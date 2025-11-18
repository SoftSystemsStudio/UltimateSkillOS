import json

from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from api.app import app
from skill_engine.domain import AgentResult


class FakeAgent:
    def run(self, task: str, max_steps: int | None = None, verbose: bool = False) -> AgentResult:
        return AgentResult(plan_id="fake-plan", status="success", final_answer=f"echo: {task}")


def test_run_endpoint_returns_agent_result(monkeypatch):
    # Inject fake agent into app.state to avoid building real Agent
    app.state.agent = FakeAgent()
    client = TestClient(app)

    payload = {"task": "say hello", "options": {"max_steps": 1, "trace": False}}
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["final_answer"] == "echo: say hello"
