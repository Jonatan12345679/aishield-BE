import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackType(str, enum.Enum):
    NONE = "none"  # traffic normal
    PORT_SCAN = "port_scan"
    BRUTE_FORCE = "brute_force"
    DDOS = "ddos"
    DATA_EXFILTRATION = "data_exfiltration"
    UNKNOWN_ANOMALY = "unknown_anomaly"  # anomali terdeteksi tapi tidak match rule manapun


class NetworkEvent(Base):

    __tablename__ = "network_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Identitas koneksi 
    src_ip: Mapped[str] = mapped_column(String(45), index=True)  # 45 = cukup utk IPv6
    dst_ip: Mapped[str] = mapped_column(String(45), index=True)
    src_port: Mapped[int] = mapped_column(Integer, nullable=True)
    dst_port: Mapped[int] = mapped_column(Integer, index=True)
    protocol: Mapped[str] = mapped_column(String(10))  # TCP / UDP / ICMP

    # Fitur numerik (input ke model ML) 
    bytes_sent: Mapped[float] = mapped_column(Float, default=0.0)
    bytes_received: Mapped[float] = mapped_column(Float, default=0.0)
    packet_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    connection_rate: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # jumlah koneksi/menit dari src_ip yang sama

    # Hasil deteksi ML 
    anomaly_score: Mapped[float] = mapped_column(
        Float, nullable=True
    )  # skor mentah dari IsolationForest.decision_function()
    is_anomaly: Mapped[bool] = mapped_column(default=False, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False),
        default=RiskLevel.LOW,
        index=True,
    )
    attack_type: Mapped[AttackType] = mapped_column(
        Enum(AttackType, native_enum=False),
        default=AttackType.NONE,
        index=True,
    )

    #  Metadata tambahan 
    is_simulated: Mapped[bool] = mapped_column(
        default=False
    )  # True kalau berasal dari SimulationPanel (demo trigger)

    __table_args__ = (
        # Index gabungan buat query dashboard: "anomali terbaru urut waktu"
        Index("ix_events_anomaly_timestamp", "is_anomaly", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<NetworkEvent {self.src_ip}->{self.dst_ip}:{self.dst_port} "
            f"risk={self.risk_level} attack={self.attack_type}>"
        )