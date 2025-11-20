import json
import os
from datetime import datetime, timezone

LOG_PATH = "data/feedback_log.json"

class FeedbackLogger:
    def __init__(self, log_path=LOG_PATH):
        self.log_path = log_path
        if not os.path.exists(os.path.dirname(log_path)):
            os.makedirs(os.path.dirname(log_path))
        if not os.path.exists(log_path):
            with open(log_path, "w") as f:
                json.dump([], f)

    def log(self, query, skills, outcome, metrics=None, metadata=None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "skills": skills,
            "outcome": outcome,
            "metrics": metrics or {},
            "metadata": metadata or {},
        }
        with open(self.log_path, "r+") as f:
            data = json.load(f)
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()

    def get_logs(self):
        with open(self.log_path) as f:
            return json.load(f)

    def log_skill_gap(self, gap_description):
        # Append to skill_gaps.json
        skill_gaps_path = "skills/skill_gaps.json"
        with open(skill_gaps_path, "r+") as f:
            gaps = json.load(f)
            gaps.append({"timestamp": datetime.now(timezone.utc).isoformat(), "gap": gap_description})
            f.seek(0)
            json.dump(gaps, f, indent=2)
            f.truncate()
