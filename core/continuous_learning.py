import os
import pickle
from core.ml_router import MLRouterModel
from core.feedback_logger import FeedbackLogger
from core.optimizer import ParameterOptimizer

class ContinuousLearner:
    def __init__(self, model_path="data/router_model.pkl"):
        self.model = MLRouterModel(model_path)
        self.logger = FeedbackLogger()
        self.version = 1

    def update(self):
        logs = self.logger.get_logs()
        self.model.train(logs)
        self.version += 1
        with open("data/model_version.txt", "w") as f:
            f.write(f"Router_v{self.version}")
        # Optionally, call optimizer after model update
        optimizer = ParameterOptimizer()
        optimizer.optimize(logs)

    def get_model(self):
        return self.model.model

    def get_version(self):
        return self.version
