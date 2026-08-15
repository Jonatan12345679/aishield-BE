from datetime import datetime
from uuid import UUID
 
from pydantic import BaseModel, ConfigDict
 
from app.models.event import AttackType, RiskLevel

class EventResponse(BaseModel):
    """Satu baris event buat ditampilin di LogStream/ThreatTimeline."""
 
    model_config = ConfigDict(from_attributes=True)  # ini fungi agar bisa langsung dari objek SQLAlchemy
 
    id: UUID
    timestamp: datetime
    src_ip: str
    dst_ip: str
    dst_port: int
    protocol: str
    bytes_sent: float
    bytes_received: float
    connection_rate: float
    anomaly_score: float | None
    is_anomaly: bool
    risk_level: RiskLevel
    attack_type: AttackType
    is_simulated: bool
 
 
class EventListResponse(BaseModel):
    """Response buat endpoint list event, dengan pagination biar ga berat kalau datanya banyak."""
 
    total: int
    page: int
    page_size: int
    events: list[EventResponse]
 
 
class RiskDistribution(BaseModel):
    """Jumlah event per risk level - dipakai buat RiskGauge/pie chart."""
 
    low: int
    medium: int
    high: int
    critical: int
 
 
class AttackTypeDistribution(BaseModel):
    """Jumlah event per jenis serangan - dipakai buat AnomalyChart."""
 
    port_scan: int
    brute_force: int
    ddos: int
    data_exfiltration: int
    unknown_anomaly: int
 
 
class DashboardSummary(BaseModel):
    """Ringkasan angka-angka utama buat StatCards di halaman dashboard."""
 
    total_events: int
    total_anomalies: int
    anomaly_rate: float  # persentase, 0-100
    risk_distribution: RiskDistribution
    attack_type_distribution: AttackTypeDistribution
    latest_event_at: datetime | None
 
 
class RiskScoreResponse(BaseModel):
    """Skor risiko terkini, dihitung dari event terbaru - dipakai RiskGauge."""
 
    score: int  
    level: str 
    sample_size: int  # berapa event terakhir yang dipakai buat hitung
    critical_count: int
    high_count: int
    """Isi metrics.json hasil training, ditampilin sbg bukti performa model ke juri."""


class ModelMetrics(BaseModel):
    n_estimators: int
    contamination: float
    train_rows: int
    test_rows: int
    binary_metrics: dict
    per_attack_type_recall: dict
