from __future__ import annotations
 
import argparse
import json
from pathlib import Path
 
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
 
RANDOM_SEED = 42
 
DEFAULT_CSV_PATH = Path(__file__).parent / "dataset" / "synthetic_events.csv"
MODEL_DIR = Path(__file__).parent / "model"
 
COMMON_PORTS = {80, 443, 22, 3306, 5432, 21, 25, 8080, 53, 3389}
 
# Fitur final yang masuk ke model 
FEATURE_COLUMNS = [
    "bytes_sent",
    "bytes_received",
    "packet_count",
    "duration_ms",
    "connection_rate",
    "bytes_ratio",
    "is_common_port",
    "bytes_per_packet",
    "burst_score",
]


# Feature Engineering
 
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tambahkan fitur turunan ke dataframe.
    Fungsi ini dipanggil juga oleh ml_engine.py saat prediksi realtime,
    supaya konsisten antara training dan inference.
    """
    df = df.copy()
 
    df["bytes_ratio"] = df["bytes_sent"] / (df["bytes_received"] + 1)
    df["is_common_port"] = df["dst_port"].isin(COMMON_PORTS).astype(int)
    df["bytes_per_packet"] = df["bytes_sent"] / (df["packet_count"] + 1)
    df["burst_score"] = df["connection_rate"] / (df["duration_ms"] + 1) * 1000 # makin tinggi = makin bursty
 
    return df
 
 
# Training & Evaluasi

def train_and_evaluate(
    df: pd.DataFrame, contamination: float, n_estimators: int
) -> tuple[IsolationForest, StandardScaler, dict]:
    df = engineer_features(df)
 
    X = df[FEATURE_COLUMNS]
    y_true_label = df["label"]  # hanya untuk evaluasi
    y_true_binary = (y_true_label != "normal").astype(int)  # 1 = anomali, 0 = normal
 
    X_train, X_test, y_train_binary, y_test_binary, label_train, label_test = train_test_split(
        X,
        y_true_binary,
        y_true_label,
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=y_true_label,
    )
 
    print(f"Train set: {len(X_train)} baris | Test set: {len(X_test)} baris")
 
    #  Scaling 
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
 
    # Training unsupervised
    print("Training IsolationForest...")
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_train_scaled)
 
    # Prediksi di test set 
    # sklearn: kalau predict() -> 1 (normal) / -1 (anomali)
    raw_pred = model.predict(X_test_scaled)
    y_pred_binary = (raw_pred == -1).astype(int)  # ini diubah saja ke 0/1 biar konsisten dgn y_true
 
    anomaly_scores = model.decision_function(X_test_scaled)  #makin negatif = makin anomali
 
    # Metrik evaluasi (binary: anomaly vs normal) 
    precision = precision_score(y_test_binary, y_pred_binary, zero_division=0)
    recall = recall_score(y_test_binary, y_pred_binary, zero_division=0)
    f1 = f1_score(y_test_binary, y_pred_binary, zero_division=0)
    cm = confusion_matrix(y_test_binary, y_pred_binary).tolist()
    report = classification_report(
        y_test_binary, y_pred_binary, target_names=["normal", "anomaly"], zero_division=0, output_dict=True
    )
 
    # Breakdown recall per jenis serangan 
    # Untuk tiap jenis serangan, berapa persen yang berhasil terdeteksi sbg anomali?
    per_attack_recall = {}
    for attack_label in label_test.unique():
        if attack_label == "normal":
            continue
        mask = (label_test == attack_label).to_numpy()
        detected = y_pred_binary[mask].sum()
        total = mask.sum()
        per_attack_recall[attack_label] = {
            "detected": int(detected),
            "total": int(total),
            "recall": round(float(detected / total), 4) if total > 0 else None,
        }
 
    metrics = {
        "n_estimators": n_estimators,
        "contamination": contamination,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "feature_columns": FEATURE_COLUMNS,
        "binary_metrics": {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4),
        },
        "confusion_matrix": {
            "labels": ["normal", "anomaly"],
            "matrix": cm,  # [[TN, FP], [FN, TP]]
        },
        "classification_report": report,
        "per_attack_type_recall": per_attack_recall,
        "anomaly_score_stats": {
            "min": round(float(anomaly_scores.min()), 4),
            "max": round(float(anomaly_scores.max()), 4),
            "mean": round(float(anomaly_scores.mean()), 4),
        },
    }
 
    return model, scaler, metrics
 

# Main
 
def main() -> None:
    parser = argparse.ArgumentParser(description="Train IsolationForest untuk AIShield")
    parser.add_argument("--csv", type=str, default=None, help="Path CSV dataset")
    parser.add_argument(
        "--contamination",
        type=float,
        default=0.12,
        help="Perkiraan proporsi anomali di data (default: 0.12, sesuai desain generator)",
    )
    parser.add_argument("--n-estimators", type=int, default=200)
    args = parser.parse_args()
 
    csv_path = Path(args.csv) if args.csv else DEFAULT_CSV_PATH
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan di {csv_path}. "
            "Jalankan dulu: python ml/aishield/synthetic_generator.py"
        )
 
    print(f"Membaca dataset dari: {csv_path}")
    df = pd.read_csv(csv_path)
 
    model, scaler, metrics = train_and_evaluate(
        df, contamination=args.contamination, n_estimators=args.n_estimators
    )
 
    # ini simpan artifact 
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
 
    model_path = MODEL_DIR / "isolation_forest.pkl"
    scaler_path = MODEL_DIR / "scaler.pkl"
    metrics_path = MODEL_DIR / "metrics.json"
    feature_cols_path = MODEL_DIR / "feature_columns.json"
 
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    with open(feature_cols_path, "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)
 
    print(f"\nModel disimpan ke: {model_path}")
    print(f"Scaler disimpan ke: {scaler_path}")
    print(f"Metrics disimpan ke: {metrics_path}")
 
    print("\n=== RINGKASAN EVALUASI ===")
    print(f"Precision : {metrics['binary_metrics']['precision']}")
    print(f"Recall    : {metrics['binary_metrics']['recall']}")
    print(f"F1-Score  : {metrics['binary_metrics']['f1_score']}")
    print("\nRecall per jenis serangan:")
    for attack, stats in metrics["per_attack_type_recall"].items():
        print(f"  {attack:20s}: {stats['detected']}/{stats['total']} terdeteksi ({stats['recall']})")
 
 
if __name__ == "__main__":
    main()