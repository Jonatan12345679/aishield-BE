from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.models.event import AttackType, RiskLevel

COMMON_PORTS = {80, 443, 22, 3306, 5432, 21, 25, 8080, 53, 3389}
ADMIN_SERVICE_PORTS = {22, 3306, 3389, 21, 23}


def calculate_risk_level(anomaly_score: float) -> RiskLevel:
    """
    Pemetaan skor anomali ke kategori RiskLevel berdasarkan konfigurasi threshold.
    """
    if anomaly_score <= settings.RISK_THRESHOLD_HIGH:
        return RiskLevel.CRITICAL
    elif anomaly_score <= settings.RISK_THRESHOLD_MEDIUM:
        return RiskLevel.HIGH
    elif anomaly_score <= settings.RISK_THRESHOLD_LOW:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def classify_attack_type(event: dict[str, Any], is_anomaly: bool) -> AttackType:
    """
    Klasifikasi jenis serangan menggunakan kriteria rule-based.
    Hanya dijalankan jika flag is_anomaly bernilai True.
    """
    if not is_anomaly:
        return AttackType.NONE

    connection_rate = event.get("connection_rate", 0)
    bytes_sent = event.get("bytes_sent", 0)
    duration_ms = event.get("duration_ms", 0)
    packet_count = event.get("packet_count", 0)
    dst_port = event.get("dst_port", 0)

    # Data Exfiltration: Payload besar dengan durasi koneksi panjang
    if bytes_sent > 100_000 and duration_ms > 10_000:
        return AttackType.DATA_EXFILTRATION

    # DDoS: Lonjakan paket dan connection rate dalam rentang singkat
    if connection_rate > 100 and packet_count > 80:
        return AttackType.DDOS

    # Brute Force: High connection rate ke port layanan administratif
    if connection_rate > 30 and dst_port in ADMIN_SERVICE_PORTS and duration_ms < 200:
        return AttackType.BRUTE_FORCE

    # Port Scan: Connection rate tinggi dengan ukuran payload sangat kecil
    if connection_rate > 30 and bytes_sent < 500 and duration_ms < 50:
        return AttackType.PORT_SCAN

    return AttackType.UNKNOWN_ANOMALY


def should_flag_as_anomaly_backup(event: dict[str, Any]) -> bool:
    """
    Fallback rule kustom untuk menangkap pola serangan yang tidak teridentifikasi oleh model ML.
    """
    connection_rate = event.get("connection_rate", 0)
    dst_port = event.get("dst_port", 0)
    duration_ms = event.get("duration_ms", 0)

    # Indikasi brute force yang melewati ambang statistik global ML
    if connection_rate > 40 and dst_port in ADMIN_SERVICE_PORTS and duration_ms < 150:
        return True

    return False


def process_event(event: dict[str, Any], ml_result: dict[str, Any]) -> dict[str, Any]:
    """
    Menggabungkan hasil prediksi model ML dan fallback rule untuk kalkulasi tingkat risiko serta jenis serangan.
    Args:
        event (dict): Data event jaringan mentah.
        ml_result (dict): Output prediksi dari ml_engine.

    Returns:
        dict: Hasil pemrosesan akhir berisi anomaly_score, is_anomaly, risk_level, dan attack_type.
    """
    is_anomaly = ml_result["is_anomaly"] or should_flag_as_anomaly_backup(event)
    anomaly_score = ml_result["anomaly_score"]

    risk_level = calculate_risk_level(anomaly_score) if ml_result["is_anomaly"] else (
        RiskLevel.MEDIUM if is_anomaly else RiskLevel.LOW
    )
    attack_type = classify_attack_type(event, is_anomaly)

    return {
        "anomaly_score": anomaly_score,
        "is_anomaly": is_anomaly,
        "risk_level": risk_level,
        "attack_type": attack_type,
    }