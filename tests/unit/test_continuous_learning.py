import asyncio

from core.continuous_learning import ContinuousLearningRunner


def test_runner_invokes_callback_periodically():
    calls = {"count": 0}

    def tick():
        calls["count"] += 1

    async def run_loop():
        runner = ContinuousLearningRunner(tick=tick, interval_seconds=0.05, run_immediately=False)
        runner.start()
        await asyncio.sleep(0.12)
        await runner.stop()

    asyncio.run(run_loop())

    assert calls["count"] >= 1


def test_trigger_once_executes_immediately():
    calls = {"count": 0}

    def tick():
        calls["count"] += 1

    async def run_once():
        runner = ContinuousLearningRunner(tick=tick, interval_seconds=1.0)
        await runner.trigger_once()

    asyncio.run(run_once())

    assert calls["count"] == 1
