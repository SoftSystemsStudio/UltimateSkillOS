import logging
import pickle

try:  # Optional dependency
    from sklearn.ensemble import RandomForestClassifier  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency guard
    RandomForestClassifier = None  # type: ignore
    _SKLEARN_IMPORT_ERROR = exc
else:  # pragma: no cover - executed when sklearn present
    _SKLEARN_IMPORT_ERROR = None

logger = logging.getLogger(__name__)

MODEL_PATH = "data/router_model.pkl"

class MLRouterModel:
    def __init__(self, model_path=MODEL_PATH):
        self.model_path = model_path
        self.model = None
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)

    def train(self, logs):
        if not logs:
            logger.debug("No feedback logs available for ML router training")
            return

        if RandomForestClassifier is None:
            logger.warning(
                "scikit-learn not installed; skipping ML router training. %s",
                _SKLEARN_IMPORT_ERROR,
            )
            return

        samples = [
            (
                [len((log.get("query") or "").strip()), len(" ".join(log.get("skills", [])))],
                log["skills"][0],
            )
            for log in logs
            if log.get("skills")
        ]

        if not samples:
            logger.debug("Insufficient data to train ML router")
            return

        X = [sample[0] for sample in samples]
        y = [sample[1] for sample in samples]

        self.model = RandomForestClassifier()
        try:
            self.model.fit(X[: len(y)], y)
        except Exception as exc:
            logger.warning("Failed to train ML router model: %s", exc)
            return

        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)

    def predict(self, queries):
        if self.model is None:
            logger.debug("ML router model not trained; cannot predict")
            return None

        if RandomForestClassifier is None:
            logger.warning("scikit-learn not installed; cannot perform predictions")
            return None

        try:
            features = [[len((q or "").strip()), 0] for q in queries]
            return self.model.predict(features)
        except Exception as exc:
            logger.warning("Failed to run ML router prediction: %s", exc)
            return None
