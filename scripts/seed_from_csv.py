
import argparse
from pathlib import Path

import pandas as pd

from app.db.database import SessionLocal, init_db
from app.models.event import AttackType, NetworkEvent, RiskLevel

DEFAULT_CSV_PATH = Path(__file__).parent.parent / "ml" / "aishield" / "dataset" / "synthetic_events.csv"

# Mapping label CSV 
LABEL_TO_ATTACK_TYPE = {
    "normal": AttackType.NONE,
    "port_scan": AttackType.PORT_SCAN,
    "brute_force": AttackType.BRUTE_FORCE,
    "ddos": AttackType.DDOS,
    "data_exfiltration": AttackType.DATA_EXFILTRATION,
}

# Risk level utk sementara
LABEL_TO_TEMP_RISK = {
    "normal": RiskLevel.LOW,
    "port_scan": RiskLevel.MEDIUM,
    "brute_force": RiskLevel.HIGH,
    "ddos": RiskLevel.CRITICAL,
    "data_exfiltration": RiskLevel.CRITICAL,
}


def seed_from_csv(csv_path: Path, limit: int | None = None, batch_size: int = 500) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV tidak ditemukan di {csv_path}. "
            "Jalankan dulu: python ml/aishield/synthetic_generator.py"
        )

    print(f"Membaca CSV dari: {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    if limit:
        df = df.head(limit)

    print(f"Total baris yang akan di-insert: {len(df)}")

    init_db() 
    db = SessionLocal()

    try:
        buffer = []
        inserted = 0

        for _, row in df.iterrows():
            label = row["label"]
            event = NetworkEvent(
                timestamp=row["timestamp"],
                src_ip=row["src_ip"],
                dst_ip=row["dst_ip"],
                src_port=int(row["src_port"]),
                dst_port=int(row["dst_port"]),
                protocol=row["protocol"],
                bytes_sent=float(row["bytes_sent"]),
                bytes_received=float(row["bytes_received"]),
                packet_count=int(row["packet_count"]),
                duration_ms=float(row["duration_ms"]),
                connection_rate=float(row["connection_rate"]),
                anomaly_score=None,  # diisi nanti oleh ml_engine
                is_anomaly=(label != "normal"),
                risk_level=LABEL_TO_TEMP_RISK.get(label, RiskLevel.LOW),
                attack_type=LABEL_TO_ATTACK_TYPE.get(label, AttackType.UNKNOWN_ANOMALY),
                is_simulated=False,
            )
            buffer.append(event)

            if len(buffer) >= batch_size:
                db.bulk_save_objects(buffer)
                db.commit()
                inserted += len(buffer)
                print(f"  ...{inserted} baris ter-insert")
                buffer.clear()

        if buffer:
            db.bulk_save_objects(buffer)
            db.commit()
            inserted += len(buffer)

        print(f"\nSelesai. Total {inserted} event berhasil di-seed ke database.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database AIShield dari CSV sintetis")
    parser.add_argument(
        "--csv", type=str, default=None, help="Path ke file CSV (default: dataset hasil generator)"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Batasi jumlah baris yang di-insert (opsional)"
    )
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else DEFAULT_CSV_PATH
    seed_from_csv(csv_path, limit=args.limit)


if __name__ == "__main__":
    main()