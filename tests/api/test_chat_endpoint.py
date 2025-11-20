"""
Integration tests for the /chat API endpoint.
"""
import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import Mock
from types import SimpleNamespace
from skill_engine.domain import AgentResult


@pytest.fixture
def client():
    """Create a test client for the FastAPI app with mocked agent."""
    # Force import of api.py file (not api/ package) by manipulating sys.path
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    api_py_path = os.path.join(root_path, 'api.py')
    
    # Import the module directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_module", api_py_path)
    api_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_module)
    
    # Mock the agent to avoid initialization issues in tests
    mock_agent = Mock()
    mock_result = AgentResult(
        plan_id="test-123",
        status="success",
        final_answer="Test response",
        steps_completed=1,
        total_time_ms=10.0
    )
    mock_agent.run.return_value = mock_result
    mock_agent.config = SimpleNamespace(
        continuous_learning_enabled=True,
        continuous_learning_background_interval_seconds=900,
        continuous_learning_trigger_on_feedback=True,
    )
    mock_agent.continuous_learner = None
    
    # Inject mock agent into app state
    api_module.app.state.agent = mock_agent
    api_module.app.state.learning_runner = None
    
    # Create test client
    return TestClient(api_module.app)


def test_health_endpoint(client):
    """Test the /health endpoint returns OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_valid_query(client):
    """Test /chat endpoint with a valid query."""
    response = client.post(
        "/chat",
        json={"query": "What is 2+2?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert isinstance(data["response"], dict)


def test_chat_endpoint_empty_query(client):
    """Test /chat endpoint with empty query."""
    response = client.post(
        "/chat",
        json={"query": ""}
    )
    # Should still return 200 with mocked agent
    assert response.status_code == 200


def test_chat_endpoint_missing_query(client):
    """Test /chat endpoint with missing query field."""
    response = client.post(
        "/chat",
        json={}
    )
    assert response.status_code == 422  # Validation error


def test_chat_endpoint_invalid_json(client):
    """Test /chat endpoint with invalid JSON."""
    response = client.post(
        "/chat",
        data="not json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_chat_endpoint_returns_structured_response(client):
    """Test that /chat returns a structured AgentResult."""
    response = client.post(
        "/chat",
        json={"query": "Hello"}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "response" in data
    resp = data["response"]
    
    if isinstance(resp, dict):
        # Should have AgentResult fields
        assert "plan_id" in resp
        assert "status" in resp
        assert resp["status"] == "success"


def test_learning_status_endpoint(client):
    agent = client.app.state.agent

    # Provide learner stats and runner snapshot
    learner_mock = Mock()
    learner_mock.stats.return_value = {"version": 5, "total_events": 42, "events_since_update": 3}
    agent.continuous_learner = learner_mock

    class DummyRunner:
        def snapshot(self):
            return {"running": False, "total_runs": 2}

    client.app.state.learning_runner = DummyRunner()

    response = client.get("/learning/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["agent_initialized"] is True
    assert payload["learning_available"] is True
    assert payload["runner"]["running"] is False
    assert payload["learner"]["version"] == 5
