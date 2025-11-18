import json
import os

PARAMS_PATH = "data/params.json"

class ParameterOptimizer:
    def __init__(self, params_path=PARAMS_PATH):
        self.params_path = params_path
        if not os.path.exists(os.path.dirname(params_path)):
            os.makedirs(os.path.dirname(params_path))
        if not os.path.exists(params_path):
            with open(params_path, "w") as f:
                json.dump({"max_steps": 6, "top_k": 3, "confidence_threshold": 0.5}, f)

    def optimize(self, logs):
        # Placeholder: grid search or evolutionary strategy
        # For now, just increment max_steps if many failures
        failures = sum(1 for log in logs if log["outcome"] == "failed")
        with open(self.params_path, "r+") as f:
            params = json.load(f)
            if failures > 10:
                params["max_steps"] += 1
            # Example: optimize top_k
            if failures < 5:
                params["top_k"] = min(params.get("top_k", 3) + 1, 10)
            f.seek(0)
            json.dump(params, f, indent=2)
            f.truncate()
        return params

    def get_params(self):
        with open(self.params_path) as f:
            return json.load(f)
