from pathlib import Path
import json, joblib
import numpy as np
from tensorflow.keras.models import load_model

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
SEQ_LEN = 24  # must match your notebook

class LSTMOccupancyService:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.config = None
        self._load()

    def _load(self):
        model_p  = ARTIFACTS_DIR / "lstm_model_v1.h5"
        scaler_p = ARTIFACTS_DIR / "scaler_v1.pkl"
        config_p = ARTIFACTS_DIR / "config_v1.json"

        self.model  = load_model(model_p)
        self.scaler = joblib.load(scaler_p)
        self.config = json.loads(config_p.read_text())

    def predict_next(self, seq_24: list[float]) -> float:
        """
        seq_24: last 24 hourly occupancies (oldest -> newest).
        Returns the next-hour occupancy (float).
        """
        if len(seq_24) != SEQ_LEN:
            raise ValueError(f"Expected sequence of length {SEQ_LEN}, got {len(seq_24)}")

        # scaler was fit on shape (n, 1)
        x = np.array(seq_24, dtype=np.float32).reshape(-1, 1)
        x_scaled = self.scaler.transform(x)            # (24,1)

        # LSTM expects (batch, timesteps, features)
        x_scaled = x_scaled.reshape(1, SEQ_LEN, 1)     # (1,24,1)

        y_scaled = self.model.predict(x_scaled, verbose=0)  # (1,1)
        y = self.scaler.inverse_transform(y_scaled)         # (1,1)
        return float(y.ravel()[0])

    def predict_multi(self, seq_24: list[float], steps: int = 3) -> list[float]:
        """
        Naive recursive multi-step: feed each new prediction back in.
        steps: how many hours ahead (e.g., 3 -> t+1..t+3).
        """
        history = list(seq_24)
        outs = []
        for _ in range(steps):
            y_next = self.predict_next(history[-SEQ_LEN:])
            outs.append(y_next)
            history.append(y_next)
        return outs

service = LSTMOccupancyService()
