from sklearn.ensemble import RandomForestClassifier
import pickle
import os

MODEL_PATH = "data/router_model.pkl"

class MLRouterModel:
    def __init__(self, model_path=MODEL_PATH):
        self.model_path = model_path
        self.model = None
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)

    def train(self, logs):
        # logs: list of dicts with 'query' and 'skills'
        X = [log["query"] for log in logs]
        y = [log["skills"][0] for log in logs]  # Simplified: first skill
        self.model = RandomForestClassifier()
        self.model.fit(X, y)
        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)

    def predict(self, queries):
        if self.model:
            return self.model.predict(queries)
        return None
