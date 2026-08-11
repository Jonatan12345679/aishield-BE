
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.config import settings

# Tambah folder ml/ ke sys.path supaya bisa import fungsi engineer_features
# langsung dari train.py — single source of truth untuk feature engineering.
ML_DIR = Path(__file__).parent.parent.parent / "ml" / "aishield"
if str(ML_DIR) not in sys.path:
    sys.path.append(str(ML_DIR))

try:
    from train import engineer_features  # noqa: E402
except ImportError:
    engineer_features = None  # ini akan dihandle di _ensure_loaded()


class MLEngine:
    """
    wrapper/singleton untuk memuat dan mengelola state model deteksi anomali.
    Memudahkan dependency injection dan unit testing (mocking).
    """

    def __init__(self) -> None:
        self.model = None
        self.scaler = None
        self.feature_columns: list[str] = []
        self.metrics: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        """memuat artefak model, scaler, dan metadata dari disk saat aplikasi startup."""
        model_path = Path(settings.ML_MODEL_PATH)
        scaler_path = Path(settings.ML_SCALER_PATH)
        metrics_path = Path(settings.ML_METRICS_PATH)
        feature_cols_path = model_path.parent / "feature_columns.json"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model tidak ditemukan di {model_path}. "
                "Jalankan dulu: python ml/aishield/train.py"
            )

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

        if feature_cols_path.exists():
            with open(feature_cols_path) as f:
                self.feature_columns = json.load(f)

        if metrics_path.exists():
            with open(metrics_path) as f:
                self.metrics = json.load(f)

        self._loaded = True
        print(f"[ml_engine] Model berhasil dimuat dari {model_path}")

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
        if engineer_features is None:
            raise ImportError(
                "Tidak bisa import engineer_features dari ml/aishield/train.py. "
                "Pastikan file tersebut ada dan tidak error."
            )

    def predict_one(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        memproses dan memprediksi skor anomali untuk single network event.

        Args:
            event (dict): Data event mentah (membutuhkan field: bytes_sent, 
                        bytes_received, packet_count, duration_ms, 
                        connection_rate, dst_port).

        Returns:
            dict: Hasil prediksi berisi 'anomaly_score' dan status 'is_anomaly'.
        """
        self._ensure_loaded()

        df = pd.DataFrame([event])
        df = engineer_features(df)

        X = df[self.feature_columns]
        X_scaled = self.scaler.transform(X)

        raw_pred = self.model.predict(X_scaled)[0]  # 1 = normal, -1 = anomali
        score = float(self.model.decision_function(X_scaled)[0])

        return {
            "anomaly_score": round(score, 4),
            "is_anomaly": bool(raw_pred == -1),
        }

    def predict_batch(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Memprediksi sekumpulan network event secara kolektif (batch processing)."""
        self._ensure_loaded()

        if not events:
            return []

        df = pd.DataFrame(events)
        df = engineer_features(df)

        X = df[self.feature_columns]
        X_scaled = self.scaler.transform(X)

        raw_preds = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)

        return [
            {
                "anomaly_score": round(float(score), 4),
                "is_anomaly": bool(pred == -1),
            }
            for pred, score in zip(raw_preds, scores, strict=True)
        ]

    def get_metrics(self) -> dict[str, Any]:
        """Ambil metrics hasil evaluasi training (buat ditampilkan di dashboard)."""
        self._ensure_loaded()
        return self.metrics


# instance tunggal yang diimport oleh endpoint lainnya. Dipanggil sekali saat startup FastAPI.
ml_engine = MLEngine()