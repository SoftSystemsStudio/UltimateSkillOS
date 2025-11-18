# Circuit Breaker

UltimateSkillOS supports a per-skill circuit-breaker to protect downstream skills from cascading failures. Defaults are provided in `config.AppConfig.agent.circuit_breaker` and can be overridden via environment variables or TOML/YAML config.

Key settings (in `agent.circuit_breaker`):

- `failure_threshold` (int): consecutive failures to open the circuit (default: 5)
- `recovery_timeout_seconds` (int): how long circuit stays open before allowing half-open trials (default: 30)
- `half_open_trial_requests` (int): number of trial requests allowed in half-open state (default: 1)

Redis persistence

For multi-process deployments you can persist circuit state to Redis. Set the environment variable `SKILLOS_CIRCUIT_REDIS_URL` to enable the Redis-backed registry. Example:

```
export SKILLOS_CIRCUIT_REDIS_URL=redis://localhost:6379/0
```

Ensure the `redis` Python package is installed (an optional dependency is listed in `requirements.txt`). If Redis is not available, the system falls back to an in-memory registry.

CLI: Inspect circuit state

Use the CLI to inspect a skill's circuit state:

```
python -m skill_engine.cli inspect-circuit <skill_name>
```

If Redis is enabled, you will see persisted state; otherwise you will see in-memory state for the running process.
