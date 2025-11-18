"""
Command-line diagnostics for UltimateSkillOS.

Usage:
  python -m skill_engine.cli trace-run "some prompt"

Prints a human-auditable trace of the plan, steps, and results.
"""
from __future__ import annotations

import argparse
import json
import sys

from skill_engine.agent import Agent


def trace_run_command(args: argparse.Namespace) -> int:
    prompt = args.prompt
    agent = Agent.from_env()
    result = agent.run(prompt, verbose=True)

    # Pretty print the result
    print("\n=== AGENT TRACE ===\n")
    print(json.dumps(result.to_dict(), indent=2, default=str))
    print("\n===================\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skill_engine.cli")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("trace-run", help="Execute a prompt and print trace")
    p.add_argument("prompt", type=str, help="Prompt or task to run")

    pc = sub.add_parser("inspect-circuit", help="Inspect circuit breaker state for a skill key")
    pc.add_argument("skill", type=str, help="Skill name or key to inspect")

    parsed = parser.parse_args(argv)
    if parsed.cmd == "trace-run":
        return trace_run_command(parsed)
    if parsed.cmd == "inspect-circuit":
        key = parsed.skill
        # Construct Agent to obtain its registry (no side-effects at import time)
        try:
            agent = Agent.from_env()
        except Exception as e:
            print(f"Failed to construct Agent: {e}")
            return 2

        reg = getattr(agent, "circuit_registry", None)
        if not reg:
            print("No circuit registry available on Agent instance")
            return 1

        try:
            state = reg.get_state(key)
        except Exception as e:
            print(f"Error fetching circuit state: {e}")
            return 2

        if not state:
            print(f"No circuit state found for '{key}'")
            return 0
        print(json.dumps(state, indent=2, default=str))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
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
