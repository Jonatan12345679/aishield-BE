"""Explainable AI (XAI) engine.

Menjelaskan KENAPA Isolation Forest men-flag event sebagai anomali:
ukur seberapa jauh tiap fitur menyimpang dari baseline traffic normal
(mean & std yang tersimpan di StandardScaler saat training).

Metode: z-score per fitur -> kontribusi = |z| / Σ|z|.

PENTING: fitur turunan (bytes_ratio, burst_score, dll) dihitung ulang
dengan engineer_features() dari train.py - fungsi YANG SAMA dengan
training & inference - jadi penjelasan pasti konsisten dengan model.
"""

import pandas as pd

import app.services.ml_engine as ml_mod
from app.services.ml_engine import ml_engine

FEATURE_META = {
    "bytes_sent": {"label": "BYTES SENT", "unit": "B"},
    "bytes_received": {"label": "BYTES RECV", "unit": "B"},
    "packet_count": {"label": "PACKETS", "unit": "pkt"},
    "duration_ms": {"label": "DURATION", "unit": "ms"},
    "connection_rate": {"label": "CONN RATE", "unit": "conn/s"},
    "bytes_ratio": {"label": "BYTES RATIO", "unit": ""},
    "is_common_port": {"label": "COMMON PORT", "unit": ""},
    "bytes_per_packet": {"label": "BYTES/PKT", "unit": "B/pkt"},
    "burst_score": {"label": "BURST SCORE", "unit": ""},
}


def _raw_dict_from_event(event) -> dict:
    """Rekonstruksi dict event mentah (format event_simulator) dari row DB."""
    return {
        "src_ip": event.src_ip,
        "dst_ip": event.dst_ip,
        "src_port": event.src_port,
        "dst_port": event.dst_port,
        "protocol": getattr(event.protocol, "value", event.protocol),
        "bytes_sent": event.bytes_sent,
        "bytes_received": event.bytes_received,
        "packet_count": event.packet_count,
        "duration_ms": event.duration_ms,
        "connection_rate": event.connection_rate,
    }


def explain_event(event) -> dict:
    """Bikin penjelasan per-fitur untuk satu NetworkEvent."""
    ml_engine._ensure_loaded()  # pastikan scaler + feature_columns termuat

    scaler = ml_engine.scaler
    columns = ml_engine.feature_columns

    # hitung ulang fitur turunan dengan rumus IDENTIK training/inference
    raw = _raw_dict_from_event(event)
    df = ml_mod.engineer_features(pd.DataFrame([raw]))
    row = df.iloc[0]

    # z-score tiap fitur terhadap baseline normal
    means = getattr(scaler, "mean_", None)
    stds = getattr(scaler, "scale_", None)
    if means is None or stds is None:
        raise RuntimeError("scaler.pkl bukan StandardScaler (mean_/scale_ tidak ada)")

    z_scores, raw_values, total_z = {}, {}, 0.0
    for i, col in enumerate(columns):
        value = float(row[col])
        std = float(stds[i]) or 1.0  # hindari division by zero
        z = (value - float(means[i])) / std
        z_scores[col] = z
        raw_values[col] = value
        total_z += abs(z)

    # 3) kontribusi relatif
    contributors = []
    for i, col in enumerate(columns):
        z = z_scores[col]
        baseline = float(means[i])
        ratio = (raw_values[col] / baseline) if baseline else None
        meta = FEATURE_META.get(col, {"label": col.upper(), "unit": ""})
        contributors.append(
            {
                "feature": col,
                "label": meta["label"],
                "unit": meta["unit"],
                "value": round(raw_values[col], 2),
                "baseline": round(baseline, 2),
                "z_score": round(z, 2),
                "direction": "above" if z >= 0 else "below",
                "contribution": round((abs(z) / total_z * 100) if total_z else 0.0, 1),
                "ratio": round(ratio, 1) if ratio is not None else None,
            }
        )

    contributors.sort(key=lambda c: c["contribution"], reverse=True)

    return {
        "event_id": str(event.id),
        "attack_type": getattr(event.attack_type, "value", event.attack_type),
        "risk_level": getattr(event.risk_level, "value", event.risk_level),
        "anomaly_score": float(event.anomaly_score),
        "is_anomaly": bool(event.is_anomaly),
        "contributors": contributors[:4],  # top 4 biar UI rapi
    }