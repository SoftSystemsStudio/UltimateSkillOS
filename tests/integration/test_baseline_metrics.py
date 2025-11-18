import pytest
from core.self_eval_harness import run_meta_learning_simulation, aggregate

def test_baseline_metrics():
    """
    Test baseline performance metrics for the agent.
    """
    # Run the simulation
    runs = run_meta_learning_simulation()
    metrics = aggregate(runs)

    # Assertions for baseline metrics
    assert metrics["time_to_threshold"] < 50, "Time to threshold is too high."
    assert metrics["sample_efficiency"] > 10, "Sample efficiency is too low."

    print("Baseline metrics:", metrics)