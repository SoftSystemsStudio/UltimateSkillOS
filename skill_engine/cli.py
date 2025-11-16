# skill_engine/cli.py

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, Optional

from skill_engine.agent import Agent
from skill_engine.engine import SkillEngine


def _extract_task(params: Dict[str, Any]) -> Optional[str]:
    """
    Utility to pull a task string from common keys.
    """
    for key in ("task", "input", "query"):
        if key in params and params[key]:
            return str(params[key])
    return None


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python3 -m skill_engine.cli <tool> '<json-input>'")
        print("Examples:")
        print("  python3 -m skill_engine.cli summarize '{\"text\": \"Hello world\"}'")
        print("  python3 -m skill_engine.cli agent '{\"task\": \"My dog\\'s name is Rocket.\", \"verbose\": true}'")
        sys.exit(1)

    tool = sys.argv[1]

    try:
        params: Dict[str, Any] = json.loads(sys.argv[2])
    except json.JSONDecodeError as e:
        print(f"Invalid JSON payload: {e}")
        sys.exit(1)

    # Minimal logging bootstrap; can be centralized later.
    logging.basicConfig(level=logging.INFO)

    if tool == "agent":
        task = _extract_task(params)
        if not task:
            print("Agent mode requires one of: 'task', 'input', or 'query' in the JSON payload.")
            sys.exit(1)

        max_steps = int(params.get("max_steps", 6))
        verbose = bool(params.get("verbose", False))

        agent = Agent(max_steps=max_steps)
        result: Any = agent.run(task, verbose=verbose)
    else:
        engine = SkillEngine()
        result = engine.run(tool, params)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
