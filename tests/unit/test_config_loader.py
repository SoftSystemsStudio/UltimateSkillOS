import os

from config import load_config


def test_load_defaults():
    cfg = load_config(config_path=None)
    assert cfg is not None
    assert hasattr(cfg, "agent")


def test_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLOS_AGENT_MAX_STEPS", "12")
    cfg = load_config(config_path=None)
    assert cfg.agent.max_steps == 12
