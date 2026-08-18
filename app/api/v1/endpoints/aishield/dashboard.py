from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.schemas.explain import ExplainResponse
from app.services.explain_engine import explain_event as xai_explain

from app.db.database import get_db
from app.models.event import AttackType, NetworkEvent, RiskLevel
from app.schemas.event import (
    AttackTypeDistribution,
    DashboardSummary,
    EventListResponse,
    EventResponse,
    ModelMetrics,
    RiskDistribution,
    RiskScoreResponse,
)
from app.services.ml_engine import ml_engine

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# bobot "kerusakan" tiap risk level, dipakai buat itung risk score
RISK_WEIGHTS = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 8,
    RiskLevel.HIGH: 20,
    RiskLevel.CRITICAL: 40,
}

RISK_SCORE_WINDOW = 100  # ambil N event terbaru buat itung skor, bukan semua histori


def _score_to_level(score: int) -> str:
    if score >= 80:
        return "safe"
    elif score >= 60:
        return "watch"
    elif score >= 35:
        return "elevated"
    return "critical"


@router.get("/risk-score", response_model=RiskScoreResponse)
def get_risk_score(db: Session = Depends(get_db)):
    """
    Skor risiko "sekarang", bukan rata-rata sepanjang masa kayak /summary.
    Sengaja cuma liat N event paling baru, biar begitu ada serangan masuk
    (via simulation atau traffic asli nanti), skor langsung kerasa turun -
    ga ketutupan sama 10rb histori normal.
    """
    recent = (
        db.query(NetworkEvent)
        .order_by(NetworkEvent.timestamp.desc())
        .limit(RISK_SCORE_WINDOW)
        .all()
    )

    if not recent:
        return RiskScoreResponse(score=100, level="safe", sample_size=0, critical_count=0, high_count=0)

    total_weight = sum(RISK_WEIGHTS[e.risk_level] for e in recent)
    avg_weight = total_weight / len(recent)
    score = max(0, min(100, round(100 - avg_weight)))

    return RiskScoreResponse(
        score=score,
        level=_score_to_level(score),
        sample_size=len(recent),
        critical_count=sum(1 for e in recent if e.risk_level == RiskLevel.CRITICAL),
        high_count=sum(1 for e in recent if e.risk_level == RiskLevel.HIGH),
    )


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)):
    """
    Angka-angka ringkasan buat StatCards & RiskGauge.
    Query-nya sengaja pakai agregasi SQL (count/group by) bukan ambil
    semua row terus dihitung di Python - biar tetep cepet walau datanya
    puluhan ribu baris.
    """
    total_events = db.query(NetworkEvent).count()
    total_anomalies = db.query(NetworkEvent).filter(NetworkEvent.is_anomaly.is_(True)).count()

    anomaly_rate = round((total_anomalies / total_events) * 100, 2) if total_events > 0 else 0.0

    # hitung jumlah tiap risk level sekaligus, satu query aja
    risk_counts = dict(
        db.query(NetworkEvent.risk_level, func.count(NetworkEvent.id))
        .group_by(NetworkEvent.risk_level)
        .all()
    )
    risk_distribution = RiskDistribution(
        low=risk_counts.get(RiskLevel.LOW, 0),
        medium=risk_counts.get(RiskLevel.MEDIUM, 0),
        high=risk_counts.get(RiskLevel.HIGH, 0),
        critical=risk_counts.get(RiskLevel.CRITICAL, 0),
    )

    attack_counts = dict(
        db.query(NetworkEvent.attack_type, func.count(NetworkEvent.id))
        .filter(NetworkEvent.attack_type != AttackType.NONE)
        .group_by(NetworkEvent.attack_type)
        .all()
    )
    attack_distribution = AttackTypeDistribution(
        port_scan=attack_counts.get(AttackType.PORT_SCAN, 0),
        brute_force=attack_counts.get(AttackType.BRUTE_FORCE, 0),
        ddos=attack_counts.get(AttackType.DDOS, 0),
        data_exfiltration=attack_counts.get(AttackType.DATA_EXFILTRATION, 0),
        unknown_anomaly=attack_counts.get(AttackType.UNKNOWN_ANOMALY, 0),
    )

    latest_event = (
        db.query(NetworkEvent.timestamp).order_by(NetworkEvent.timestamp.desc()).first()
    )

    return DashboardSummary(
        total_events=total_events,
        total_anomalies=total_anomalies,
        anomaly_rate=anomaly_rate,
        risk_distribution=risk_distribution,
        attack_type_distribution=attack_distribution,
        latest_event_at=latest_event[0] if latest_event else None,
    )


@router.get("/events", response_model=EventListResponse)
def list_events(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    anomaly_only: bool = Query(False, description="Filter cuma yang anomali aja"),
    risk_level: RiskLevel | None = Query(None),
):
    """
    List event buat LogStream, urut dari yang paling baru.
    Dukung filter anomaly_only & risk_level, plus pagination biar FE
    ga perlu narik ribuan baris sekaligus.
    """
    query = db.query(NetworkEvent)

    if anomaly_only:
        query = query.filter(NetworkEvent.is_anomaly.is_(True))
    if risk_level:
        query = query.filter(NetworkEvent.risk_level == risk_level)

    total = query.count()

    events = (
        query.order_by(NetworkEvent.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return EventListResponse(
        total=total,
        page=page,
        page_size=page_size,
        events=[EventResponse.model_validate(e) for e in events],
    )


@router.get("/model-metrics", response_model=ModelMetrics)
def get_model_metrics():
    """
    Hasil evaluasi training (precision/recall/F1 dari train.py), buat
    ditampilin sbg bukti performa model - bukan cuma klaim doang.
    """
    metrics = ml_engine.get_metrics()
    return ModelMetrics(
        n_estimators=metrics.get("n_estimators", 0),
        contamination=metrics.get("contamination", 0),
        train_rows=metrics.get("train_rows", 0),
        test_rows=metrics.get("test_rows", 0),
        binary_metrics=metrics.get("binary_metrics", {}),
        per_attack_type_recall=metrics.get("per_attack_type_recall", {}),
    )

@router.get("/events/{event_id}/explain", response_model=ExplainResponse)
def explain_event_endpoint(event_id: str, db: Session = Depends(get_db)):
    event = db.query(NetworkEvent).filter(NetworkEvent.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    return xai_explain(event)   