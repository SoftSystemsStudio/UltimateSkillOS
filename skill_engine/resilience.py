import threading
import time
import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: Optional[float] = None
    half_open: bool = False


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    half_open_trial_requests: int = 1


class CircuitOpen(Exception):
    pass


class CircuitBreaker:
    """A simple in-memory circuit breaker.

    Behavior:
    - Track consecutive failures.
    - When failures >= threshold, open circuit for `recovery_timeout_seconds`.
    - During open period, calls raise `CircuitOpen` immediately.
    - After timeout, transition to half-open: allow a limited number
      of trial requests (`half_open_trial_requests`). If trial succeeds,
      reset; if it fails, reopen the circuit.
    """

    def __init__(self, key: str, cfg: Optional[CircuitBreakerConfig] = None):
        self.key = key
        self.cfg = cfg or CircuitBreakerConfig()
        self._state = CircuitState()
        self._lock = threading.Lock()
        self._half_open_trials = 0

    def _now(self) -> float:
        return time.time()

    def is_open(self) -> bool:
        with self._lock:
            if self._state.opened_at is None:
                return False
            # If past recovery timeout, move to half-open
            elapsed = self._now() - self._state.opened_at
            if elapsed >= self.cfg.recovery_timeout_seconds:
                self._state.half_open = True
                self._half_open_trials = 0
                self._state.opened_at = None
                return False
            return True

    def before_call(self) -> None:
        if self.is_open():
            raise CircuitOpen(f"Circuit for {self.key} is open")
        # If half-open, allow up to configured trial requests.
        with self._lock:
            if self._state.half_open:
                if self._half_open_trials >= self.cfg.half_open_trial_requests:
                    # No more trials allowed until a result resets state
                    raise CircuitOpen(f"Circuit for {self.key} is half-open and trial limit reached")
                self._half_open_trials += 1

    def on_success(self) -> None:
        with self._lock:
            # reset state on success
            self._state = CircuitState()
            self._half_open_trials = 0

    def on_failure(self) -> None:
        with self._lock:
            self._state.failures += 1
            # open circuit if threshold reached
            if self._state.failures >= self.cfg.failure_threshold:
                self._state.opened_at = self._now()
                self._state.half_open = False
                self._half_open_trials = 0

    def get_state(self) -> dict:
        with self._lock:
            return {
                "key": self.key,
                "failures": self._state.failures,
                "opened_at": self._state.opened_at,
                "half_open": self._state.half_open,
                "half_open_trials": self._half_open_trials,
                "cfg": {
                    "failure_threshold": self.cfg.failure_threshold,
                    "recovery_timeout_seconds": self.cfg.recovery_timeout_seconds,
                    "half_open_trial_requests": self.cfg.half_open_trial_requests,
                },
            }


class CircuitBreakerRegistry:
    """Registry for named circuit breakers (in-memory).

    Use `get_or_create(key, cfg)` to retrieve a breaker for a given skill/key.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._store: Dict[str, CircuitBreaker] = {}

    def get_or_create(self, key: str, cfg: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        with self._lock:
            if key not in self._store:
                self._store[key] = CircuitBreaker(key, cfg)
            return self._store[key]

    def get_state(self, key: str) -> dict | None:
        with self._lock:
            cb = self._store.get(key)
            if not cb:
                return None
            return cb.get_state()


def create_registry(redis_url: str | None = None, prefix: str = "skillos:circuit:"):
    """Factory: create a CircuitBreakerRegistry.

    If `redis_url` is provided and the `redis` package is available, return
    a Redis-backed registry. Otherwise return an in-memory registry.
    This avoids creating global singletons or performing network IO at import time.
    """

    if not redis_url:
        return CircuitBreakerRegistry()

    try:
        import redis

        class RedisCircuitBreaker:
            """Circuit breaker implementation backed by Redis keys.

            Keys per circuit (prefix + key):
              - failures: integer count
              - opened_at: float timestamp or empty
              - half_open_trials: integer
            """

            def __init__(self, key: str, cfg: Optional[CircuitBreakerConfig], client: redis.Redis, prefix: str = "skillos:circuit:"):
                self.key = key
                self.cfg = cfg or CircuitBreakerConfig()
                self.client = client
                self.prefix = prefix

            def _k(self, suffix: str) -> str:
                return f"{self.prefix}{self.key}:{suffix}"

            def _now(self) -> float:
                return time.time()

            def is_open(self) -> bool:
                opened = self.client.get(self._k("opened_at"))
                if not opened:
                    return False
                try:
                    opened_at = float(opened)
                except Exception:
                    return False
                elapsed = self._now() - opened_at
                if elapsed >= self.cfg.recovery_timeout_seconds:
                    # move to half-open by clearing opened_at and resetting trials
                    pipe = self.client.pipeline()
                    pipe.delete(self._k("opened_at"))
                    pipe.set(self._k("half_open_trials"), 0)
                    pipe.execute()
                    return False
                return True

            def get_state(self) -> dict:
                try:
                    failures = int(self.client.get(self._k("failures") ) or 0)
                except Exception:
                    failures = 0
                try:
                    opened = self.client.get(self._k("opened_at"))
                    opened_at = float(opened) if opened else None
                except Exception:
                    opened_at = None
                try:
                    half_trials = int(self.client.get(self._k("half_open_trials")) or 0)
                except Exception:
                    half_trials = 0
                return {
                    "key": self.key,
                    "failures": failures,
                    "opened_at": opened_at,
                    "half_open": bool(half_trials > 0 and opened_at is None and failures >= self.cfg.failure_threshold),
                    "half_open_trials": half_trials,
                    "cfg": {
                        "failure_threshold": self.cfg.failure_threshold,
                        "recovery_timeout_seconds": self.cfg.recovery_timeout_seconds,
                        "half_open_trial_requests": self.cfg.half_open_trial_requests,
                    },
                }

            def before_call(self) -> None:
                if self.is_open():
                    raise CircuitOpen(f"Circuit for {self.key} is open (redis)")
                trials = self.client.get(self._k("half_open_trials"))
                if trials is None:
                    return
                try:
                    trials_i = int(trials)
                except Exception:
                    trials_i = 0
                if trials_i >= self.cfg.half_open_trial_requests:
                    raise CircuitOpen(f"Circuit for {self.key} is half-open and trial limit reached (redis)")
                # increment trial optimistically
                try:
                    self.client.incr(self._k("half_open_trials"))
                except Exception:
                    pass

            def on_success(self) -> None:
                pipe = self.client.pipeline()
                pipe.delete(self._k("failures"))
                pipe.delete(self._k("opened_at"))
                pipe.delete(self._k("half_open_trials"))
                try:
                    pipe.execute()
                except Exception:
                    pass

            def on_failure(self) -> None:
                # increment failures
                try:
                    failures = self.client.incr(self._k("failures"))
                except Exception:
                    failures = None
                if failures is not None and failures >= self.cfg.failure_threshold:
                    try:
                        self.client.set(self._k("opened_at"), str(self._now()))
                        self.client.set(self._k("half_open_trials"), 0)
                    except Exception:
                        pass


        class RedisCircuitBreakerRegistry:
            def __init__(self, url: str, prefix: str = "skillos:circuit:"):
                parts = url
                self.client = redis.from_url(parts)
                self.prefix = prefix

            def get_or_create(self, key: str, cfg: Optional[CircuitBreakerConfig] = None) -> RedisCircuitBreaker:
                return RedisCircuitBreaker(key, cfg, client=self.client, prefix=self.prefix)

            def get_state(self, key: str) -> dict | None:
                try:
                    cb = RedisCircuitBreaker(key, None, client=self.client, prefix=self.prefix)
                    return cb.get_state()
                except Exception:
                    return None

        try:
            return RedisCircuitBreakerRegistry(redis_url)
        except Exception:
            return CircuitBreakerRegistry()
    except Exception:
        # redis not available; keep in-memory registry
        return CircuitBreakerRegistry()
