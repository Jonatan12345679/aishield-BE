"""
Synthetic Network Traffic Generator — AIShield

Menghasilkan dataset event jaringan sintetis dengan pola statistik
berbeda untuk traffic normal dan 4 jenis anomali:
    - Port Scan
    - Brute Force
    - DDoS
    - Data Exfiltration

Output: CSV di ml/aishield/dataset/synthetic_events.csv

Kolom 'label' HANYA dipakai untuk evaluasi model (precision/recall/F1)
di train.py — TIDAK dipakai sebagai input fitur ke IsolationForest,
karena model ini unsupervised.x`

Cara pakai:
    python ml/aishield/synthetic_generator.py --rows 10000
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


# Konfigurasi umum

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

COMMON_PORTS = [80, 443, 22, 3306, 5432, 21, 25, 8080, 53, 3389]
PROTOCOLS = ["TCP", "UDP", "ICMP"]
PROTOCOL_WEIGHTS = [0.75, 0.20, 0.05]

CLASS_PROPORTIONS = {
    "normal": 0.88,
    "port_scan": 0.035,
    "brute_force": 0.035,
    "ddos": 0.03,
    "data_exfiltration": 0.02,
}

BASE_TIME = datetime.now() - timedelta(days=7)


def _random_ip(internal: bool = False) -> str:
    """Generate IP acak. internal=True -> range privat (192.168.x.x)."""
    if internal:
        return f"192.168.{random.randint(0, 5)}.{random.randint(1, 254)}"
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def _random_timestamp() -> datetime:
    """
    Timestamp acak dalam 7 hari terakhir, dengan bias ke jam kerja
    (08:00-18:00) supaya pola traffic normal lebih realistis.
    """
    day_offset = random.uniform(0, 7)
    ts = BASE_TIME + timedelta(days=day_offset)

    if random.random() < 0.7:  # 70% traffic terjadi "jam kerja"
        hour = random.randint(8, 18)
    else:
        hour = random.randint(0, 23)

    return ts.replace(
        hour=hour,
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=0,
    )



# Generator per kelas
def generate_normal(n: int) -> pd.DataFrame:
    """Traffic normal: bytes wajar, port umum, connection_rate rendah."""
    rows = []
    for _ in range(n):
        rows.append(
            {
                "timestamp": _random_timestamp(),
                "src_ip": _random_ip(internal=True),
                "dst_ip": _random_ip(internal=random.random() < 0.4),
                "src_port": random.randint(1024, 65535),
                "dst_port": random.choice(COMMON_PORTS),
                "protocol": random.choices(PROTOCOLS, PROTOCOL_WEIGHTS)[0],
                "bytes_sent": max(0, np.random.normal(4000, 1500)),
                "bytes_received": max(0, np.random.normal(15000, 6000)),
                "packet_count": max(1, int(np.random.normal(40, 15))),
                "duration_ms": max(10, np.random.normal(800, 400)),
                "connection_rate": max(0.1, np.random.normal(2, 1)),
                "label": "normal",
            }
        )
    return pd.DataFrame(rows)


def generate_port_scan(n: int) -> pd.DataFrame:
    """
    Port Scan: 1 src_ip menembak banyak dst_port berbeda dalam waktu
    singkat. connection_rate sangat tinggi, bytes kecil, duration pendek.
    """
    rows = []
    for _ in range(n):
        attacker_ip = _random_ip()
        rows.append(
            {
                "timestamp": _random_timestamp(),
                "src_ip": attacker_ip,
                "dst_ip": _random_ip(internal=True),
                "src_port": random.randint(1024, 65535),
                "dst_port": random.randint(1, 65535),  # port acak/berurutan (scanning)
                "protocol": "TCP",
                "bytes_sent": max(0, np.random.normal(60, 20)),
                "bytes_received": max(0, np.random.normal(40, 15)),
                "packet_count": max(1, int(np.random.normal(3, 1))),
                "duration_ms": max(1, np.random.normal(15, 8)),
                "connection_rate": max(20, np.random.normal(80, 25)),
                "label": "port_scan",
            }
        )
    return pd.DataFrame(rows)


def generate_brute_force(n: int) -> pd.DataFrame:
    """
    Brute Force: 1 src_ip menembak port yang SAMA (SSH/DB/RDP) berulang
    kali dengan interval pendek. connection_rate tinggi, dst_port tetap.
    """
    target_ports = [22, 3306, 3389, 21]
    rows = []
    for _ in range(n):
        attacker_ip = _random_ip()
        target_port = random.choice(target_ports)
        rows.append(
            {
                "timestamp": _random_timestamp(),
                "src_ip": attacker_ip,
                "dst_ip": _random_ip(internal=True),
                "src_port": random.randint(1024, 65535),
                "dst_port": target_port,
                "protocol": "TCP",
                "bytes_sent": max(0, np.random.normal(200, 50)),
                "bytes_received": max(0, np.random.normal(150, 40)),
                "packet_count": max(1, int(np.random.normal(6, 2))),
                "duration_ms": max(5, np.random.normal(50, 20)),
                "connection_rate": max(15, np.random.normal(60, 20)),
                "label": "brute_force",
            }
        )
    return pd.DataFrame(rows)


def generate_ddos(n: int) -> pd.DataFrame:
    """
    DDoS: BANYAK src_ip berbeda menembak 1 dst_ip/port yang sama secara
    bersamaan. packet_count & connection_rate meledak, duration pendek.
    """
    rows = []
    # simulasikan beberapa "gelombang" serangan ke target yang sama
    n_targets = max(1, n // 200)
    targets = [(_random_ip(internal=True), random.choice(COMMON_PORTS)) for _ in range(n_targets)]

    for _ in range(n):
        target_ip, target_port = random.choice(targets)
        rows.append(
            {
                "timestamp": _random_timestamp(),
                "src_ip": _random_ip(),  # spoofed / botnet, selalu beda-beda
                "dst_ip": target_ip,
                "src_port": random.randint(1024, 65535),
                "dst_port": target_port,
                "protocol": random.choices(["TCP", "UDP"], [0.5, 0.5])[0],
                "bytes_sent": max(0, np.random.normal(100, 40)),
                "bytes_received": max(0, np.random.normal(10, 5)),
                "packet_count": max(1, int(np.random.normal(150, 50))),
                "duration_ms": max(1, np.random.normal(20, 10)),
                "connection_rate": max(50, np.random.normal(200, 60)),
                "label": "ddos",
            }
        )
    return pd.DataFrame(rows)


def generate_data_exfiltration(n: int) -> pd.DataFrame:
    """
    Data Exfiltration: bytes_sent (outbound) jauh di atas normal,
    duration panjang, sering terjadi di luar jam kerja, dst_ip eksternal.
    """
    rows = []
    for _ in range(n):
        ts = _random_timestamp()
        # bias ke luar jam kerja (malam / dini hari)
        if random.random() < 0.6:
            ts = ts.replace(hour=random.choice([0, 1, 2, 3, 22, 23]))

        rows.append(
            {
                "timestamp": ts,
                "src_ip": _random_ip(internal=True),
                "dst_ip": _random_ip(internal=False),  # keluar ke IP eksternal
                "src_port": random.randint(1024, 65535),
                "dst_port": random.choice([443, 21, 22, 8080]),
                "protocol": "TCP",
                "bytes_sent": max(0, np.random.normal(500_000, 150_000)),  # outbound BESAR
                "bytes_received": max(0, np.random.normal(2000, 800)),
                "packet_count": max(1, int(np.random.normal(400, 100))),
                "duration_ms": max(100, np.random.normal(60_000, 20_000)),  # koneksi lama
                "connection_rate": max(0.1, np.random.normal(1, 0.5)),  # TIDAK banyak koneksi, cuma 1 besar
                "label": "data_exfiltration",
            }
        )
    return pd.DataFrame(rows)


# Orkestrasi
GENERATORS = {
    "normal": generate_normal,
    "port_scan": generate_port_scan,
    "brute_force": generate_brute_force,
    "ddos": generate_ddos,
    "data_exfiltration": generate_data_exfiltration,
}


def generate_dataset(total_rows: int) -> pd.DataFrame:
    frames = []
    for label, proportion in CLASS_PROPORTIONS.items():
        n = max(1, int(total_rows * proportion))
        frames.append(GENERATORS[label](n))

    df = pd.concat(frames, ignore_index=True)
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)  # shuffle

    # bulatkan kolom numerik biar rapi
    numeric_cols = [
        "bytes_sent",
        "bytes_received",
        "duration_ms",
        "connection_rate",
    ]
    df[numeric_cols] = df[numeric_cols].round(2)

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic AIShield dataset")
    parser.add_argument(
        "--rows", type=int, default=10_000, help="Total jumlah baris (default: 10000)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path output CSV (default: ml/aishield/dataset/synthetic_events.csv)",
    )
    args = parser.parse_args()

    output_path = (
        Path(args.output)
        if args.output
        else Path(__file__).parent / "dataset" / "synthetic_events.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.rows} baris dataset sintetis...")
    df = generate_dataset(args.rows)

    df.to_csv(output_path, index=False)

    print(f"Selesai. Disimpan ke: {output_path}")
    print("\nDistribusi label:")
    print(df["label"].value_counts())
    print(f"\nTotal baris: {len(df)}")


if __name__ == "__main__":
    main()