# skill_engine/agent.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

from skill_engine.engine import SkillEngine
from skill_engine.memory.memory_manager import get_memory_manager
from core.router import Router  # Using the existing Router implementation


class Agent:
    def __init__(self, max_steps: int = 6) -> None:
        self.engine = SkillEngine()
        # Shared, process-wide memory manager (SQLite-backed by default)
        self.memory = get_memory_manager()
        self.router = Router()
        self.max_steps = max_steps

    def run(self, task: str, verbose: bool = False) -> Dict[str, Any]:
        thoughts: List[str] = []
        actions: List[Dict[str, Any]] = []
        observations: List[str] = []

        query: str = task

        for step in range(1, self.max_steps + 1):
            thought = f"Step {step}: decide best skill for: {query}"
            if verbose:
                print("Thought:", thought)
            thoughts.append(thought)

            route_result = self.router.route(query)
            skill_name = route_result["use_skill"]
            params: Dict[str, Any] = route_result.get("params", {"text": query})

            if verbose:
                print("Action:", skill_name, "with params:", params)
            actions.append({"skill": skill_name, "params": params})

            obs = self.engine.run(skill_name, params)
            if verbose:
                print("Observation:", obs)
            observations.append(str(obs))

            structured_obs: Optional[Dict[str, Any]] = obs if isinstance(obs, dict) else None

            # ------------------------------------------------------------------
            # Memory write: store useful outcomes
            # ------------------------------------------------------------------
            if structured_obs is not None:
                if "summary" in structured_obs:
                    self.memory.add(str(structured_obs["summary"]))
                elif "answer" in structured_obs:
                    self.memory.add(str(structured_obs["answer"]))
                else:
                    text_val = params.get("text")
                    if isinstance(text_val, str):
                        self.memory.add(text_val)

            # ------------------------------------------------------------------
            # Termination: explicit summary/answer
            # ------------------------------------------------------------------
            if structured_obs is not None and ("summary" in structured_obs or "answer" in structured_obs):
                final_answer = structured_obs.get("summary") or structured_obs.get("answer")
                return {
                    "task": task,
                    "final_answer": final_answer,
                    "thoughts": thoughts,
                    "actions": actions,
                    "observations": observations,
                    "steps_taken": step,
                }

            # ------------------------------------------------------------------
            # Termination: memory_search skill
            # ------------------------------------------------------------------
            if skill_name == "memory_search" and structured_obs is not None and "matches" in structured_obs:
                matches = structured_obs.get("matches") or []
                # Normalize the query we are trying to answer
                query_for_search = params.get("query") or params.get("text") or query
                query_clean = str(query_for_search).strip()

                answer_text: Optional[str] = None

                if matches:
                    # Prefer a match that is:
                    # - not identical to the current query
                    # - not obviously a serialized debug dict
                    for m in matches:
                        if not isinstance(m, dict):
                            continue
                        txt = m.get("text")
                        if not isinstance(txt, str):
                            continue

                        clean = txt.strip()
                        # Skip if it's literally the same as the query
                        if clean == query_clean:
                            continue
                        # Skip old artifacts like stringified dicts
                        if clean.startswith("{") and "summary" in clean:
                            continue

                        answer_text = clean
                        break

                    # Fallback: if filtering removed everything, default to the top match's text
                    if answer_text is None:
                        top = matches[0]
                        if isinstance(top, dict) and isinstance(top.get("text"), str):
                            answer_text = top["text"]  # type: ignore[index]

                if answer_text:
                    self.memory.add(answer_text)
                    return {
                        "task": task,
                        "final_answer": answer_text,
                        "thoughts": thoughts,
                        "actions": actions,
                        "observations": observations,
                        "steps_taken": step,
                    }

                # No usable matches found: return a clear response and stop.
                no_match_answer = "I could not find anything in memory that answers that."
                self.memory.add(no_match_answer)

                return {
                    "task": task,
                    "final_answer": no_match_answer,
                    "thoughts": thoughts,
                    "actions": actions,
                    "observations": observations,
                    "steps_taken": step,
                }

            # ------------------------------------------------------------------
            # Default: propagate observation into next query
            # ------------------------------------------------------------------
            query = str(obs)

        # Fallback: we hit max_steps without a clear answer.
        return {
            "task": task,
            "final_answer": query,
            "thoughts": thoughts,
            "actions": actions,
            "observations": observations,
            "steps_taken": self.max_steps,
        }
