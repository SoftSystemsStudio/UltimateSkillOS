import copy

from config import AgentConfig, AppConfig
from skill_engine.agent import Agent


class DummyRouter:
    def route(self, query):
        return {"use_skill": "question_answering", "params": {"query": query, "text": query}}


class StubMemoryFacade:
    def add(self, *_args, **_kwargs):
        return None

    def recall_context(self, _task):
        return []


class StaticPlanner:
    name = "planner"
    version = "9.9.9"
    sla = None

    def __init__(self, steps):
        self._steps = steps

    def invoke(self, input_data, _context):
        return {"plan": copy.deepcopy(self._steps), "executed_steps": 0, "results": []}


class MemoryStub:
    name = "memory_search"
    sla = None

    def __init__(self, matches=None):
        self.matches = matches or []

    def invoke(self, input_data, _context):
        return {"query": input_data.payload.get("query", ""), "matches": self.matches}


class QAStub:
    name = "question_answering"
    sla = None

    def __init__(self, answer):
        self.answer = answer

    def invoke(self, input_data, _context):
        return {"final_answer": self.answer, "query": input_data.payload.get("query")}


class SummaryStub:
    name = "summarize"
    sla = None

    def __init__(self):
        self.received = []

    def invoke(self, input_data, _context):
        text = input_data.payload.get("text", "")
        self.received.append(text)
        summary = f"summary::{text}"
        return {"summary": summary, "final_answer": summary}


class ReflectionStub:
    name = "reflection"
    sla = None

    def __init__(self):
        self.received = []

    def invoke(self, input_data, _context):
        text = input_data.payload.get("text", "")
        self.received.append(text)
        return {"notes": "checked", "text_evaluated": text}


def make_agent(monkeypatch, skills):
    class FakeSkillEngine:
        def __init__(self):
            self.skills = skills

    monkeypatch.setattr("skill_engine.agent.SkillEngine", FakeSkillEngine)
    monkeypatch.setattr("skill_engine.agent.Router", lambda *args, **kwargs: DummyRouter())
    return Agent(
        config=AgentConfig(max_steps=6, enable_memory=False),
        memory_facade=StubMemoryFacade(),
        app_config=AppConfig(),
    )


def test_agent_runs_planner_steps_before_router(monkeypatch):
    planner = StaticPlanner(
        [
            {
                "description": "memory first",
                "skill": "memory_search",
                "input": {"query": "goal", "k": 1},
            },
            {
                "description": "answer",
                "skill": "question_answering",
                "input": {"query": "goal", "mode": "qa"},
            },
        ]
    )
    memory_skill = MemoryStub(matches=[{"text": "cached fact"}])
    qa_skill = QAStub(answer="definitive answer")

    agent = make_agent(
        monkeypatch,
        {
            "planner": planner,
            "memory_search": memory_skill,
            "question_answering": qa_skill,
        },
    )

    result = agent.run("Tell me the goal")

    assert result.status == "success"
    assert result.final_answer == "definitive answer"
    assert result.metadata.get("plan_used") is True
    assert len(result.step_results) == 2


def test_agent_replaces_last_result_placeholders(monkeypatch):
    summary_skill = SummaryStub()
    reflection_skill = ReflectionStub()
    qa_skill = QAStub(answer="Detailed write-up")
    planner = StaticPlanner(
        [
            {"skill": "question_answering", "input": {"query": "goal"}},
            {"skill": "summarize", "input": {"text": "<LAST_RESULT>"}},
            {"skill": "reflection", "input": {"text": "<LAST_RESULT>"}},
        ]
    )

    agent = make_agent(
        monkeypatch,
        {
            "planner": planner,
            "question_answering": qa_skill,
            "summarize": summary_skill,
            "reflection": reflection_skill,
        },
    )

    result = agent.run("Summarize the plan")

    assert result.final_answer.startswith("summary::")
    assert summary_skill.received == ["Detailed write-up"]
    # Reflection should receive the summarized output, not the raw QA answer
    assert reflection_skill.received == [result.final_answer]
    assert len(result.step_results) == 3