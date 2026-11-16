
from pathlib import Path
import joblib
from datetime import datetime, timezone


class ModelRegistry:
    """Save, load and list LedgerLens forecasting models."""

    def __init__(self, registry_dir="/kaggle/working/ledgerlens_models"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def save_model(self, model, model_name, metadata=None):
        if not model_name or Path(model_name).name != model_name:
            raise ValueError("model_name must be a simple filename.")

        artifact = {
            "model": model,
            "metadata": metadata or {},
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name
        }

        path = self.registry_dir / f"{model_name}.joblib"
        joblib.dump(artifact, path)

        return path

    def load_model(self, model_name):
        if not model_name or Path(model_name).name != model_name:
            raise ValueError("model_name must be a simple filename.")

        path = self.registry_dir / f"{model_name}.joblib"

        if not path.exists():
            raise FileNotFoundError(f"Model not found: {path}")

        artifact = joblib.load(path)

        return artifact

    def list_models(self):
        return sorted(
            path.stem
            for path in self.registry_dir.glob("*.joblib")
        )
