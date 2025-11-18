import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from core.interfaces import Planner, Evaluator

class DummyPlanner(Planner):
    def plan(self, goal, context):
        return ["step1", "step2"]

class DummyEvaluator(Evaluator):
    def evaluate(self, result, context):
        return {"score": 1.0}

class TestInterfaces(unittest.TestCase):
    def test_planner(self):
        planner = DummyPlanner()
        steps = planner.plan("goal", {})
        self.assertEqual(steps, ["step1", "step2"])

    def test_evaluator(self):
        evaluator = DummyEvaluator()
        score = evaluator.evaluate("result", {})
        self.assertEqual(score["score"], 1.0)

if __name__ == "__main__":
    unittest.main()
