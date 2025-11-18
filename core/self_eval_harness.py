#!/usr/bin/env python3
"""
core/self_eval_harness.py
Toy self-evaluation harness. Runs a deterministic simulation and writes
data/self_eval_report_meta_learning.json for demonstration.
"""
import json
import random
from pathlib import Path
import statistics
from datetime import datetime
import difflib
from typing import List, Dict

ROOT = Path(__file__).parent.parent
OUT = ROOT / "data" / "self_eval_report_meta_learning.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def run_meta_learning_simulation(seeds=7, target_score=0.9):
    runs = []
    for s in range(seeds):
        random.seed(1000 + s)
        steps = 0
        score = 0.0
        samples = 0
        history = []
        while score < target_score and steps < 200:
            samples += random.randint(1,10)
            delta = random.random() * 0.05 * (1 - score)
            score += delta
            steps += 1
            history.append(min(score,1.0))
        runs.append({"steps": steps, "samples": samples, "final_score": min(score,1.0), "history": history})
    return runs

def aggregate(runs):
    return {"time_to_threshold": statistics.median([r['steps'] for r in runs]), "sample_efficiency": statistics.median([r['samples'] for r in runs])}

def evaluate_accuracy(expected: str, actual: str) -> float:
    """
    Evaluate accuracy using string similarity.

    Args:
        expected (str): The expected answer.
        actual (str): The actual answer.

    Returns:
        float: A score between 0 and 1 representing accuracy.
    """
    return difflib.SequenceMatcher(None, expected, actual).ratio()

def evaluate_completeness(expected_parts: List[str], actual: str) -> float:
    """
    Evaluate completeness by checking the presence of expected parts in the actual answer.

    Args:
        expected_parts (List[str]): List of key parts expected in the answer.
        actual (str): The actual answer.

    Returns:
        float: A score between 0 and 1 representing completeness.
    """
    matches = sum(1 for part in expected_parts if part in actual)
    return matches / len(expected_parts)

def evaluate_efficiency(steps: int, max_steps: int) -> float:
    """
    Evaluate efficiency based on the number of steps taken.

    Args:
        steps (int): The number of steps taken.
        max_steps (int): The maximum allowable steps.

    Returns:
        float: A score between 0 and 1 representing efficiency.
    """
    return max(0, 1 - (steps / max_steps))

def run_evaluation_task(expected: str, actual: str, expected_parts: List[str], steps: int, max_steps: int) -> Dict[str, float]:
    """
    Run a single evaluation task and compute metrics.

    Args:
        expected (str): The expected answer.
        actual (str): The actual answer.
        expected_parts (List[str]): Key parts expected in the answer.
        steps (int): The number of steps taken.
        max_steps (int): The maximum allowable steps.

    Returns:
        Dict[str, float]: A dictionary of evaluation metrics.
    """
    return {
        "accuracy": evaluate_accuracy(expected, actual),
        "completeness": evaluate_completeness(expected_parts, actual),
        "efficiency": evaluate_efficiency(steps, max_steps)
    }

def generate_evaluation_report(task_name: str, metrics: dict, runs: list) -> None:
    """
    Generate a detailed evaluation report.

    Args:
        task_name (str): The name of the task being evaluated.
        metrics (dict): Aggregated metrics for the task.
        runs (list): Detailed results of individual runs.
    """
    report = {
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "task": task_name,
        "metrics": metrics,
        "runs": runs
    }
    report_path = OUT.parent / f"self_eval_report_{task_name}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"Wrote evaluation report to {report_path}")

def log_failure_modes(runs: list) -> None:
    """
    Analyze runs to identify common failure modes and log them.

    Args:
        runs (list): Detailed results of individual runs.
    """
    failure_modes = {}
    for run in runs:
        for step, score in enumerate(run["history"], 1):
            if score < 0.5:
                failure_modes[f"step_{step}"] = failure_modes.get(f"step_{step}", 0) + 1

    failure_log_path = OUT.parent / "failure_modes_log.json"
    with open(failure_log_path, 'w', encoding='utf-8') as f:
        json.dump(failure_modes, f, indent=2)
    print(f"Logged failure modes to {failure_log_path}")

def main():
    runs = run_meta_learning_simulation()
    report = {"timestamp": datetime.utcnow().isoformat()+'Z', "skill": "meta_learning_demo", "metrics": aggregate(runs), "runs": runs}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print("Wrote self-eval report to", OUT)

    # Example evaluation task
    expected_answer = "The capital of France is Paris."
    actual_answer = "Paris is the capital of France."
    expected_parts = ["capital", "France", "Paris"]
    steps_taken = 3
    max_steps = 5

    metrics = run_evaluation_task(expected_answer, actual_answer, expected_parts, steps_taken, max_steps)

    report = {
        "timestamp": datetime.utcnow().isoformat()+'Z',
        "task": "example_task",
        "metrics": metrics
    }

    generate_evaluation_report("example_task", metrics, runs)
    log_failure_modes(runs)

    print("Wrote evaluation report to", OUT)

if __name__ == "__main__":
    main()
