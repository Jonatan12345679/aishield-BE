from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.schemas.explain import ExplainResponse
from app.services.explain_engine import explain_event as xai_explain
from sqlalchemy import desc
from pydantic import BaseModel
import csv
import io
from datetime import datetime
from fastapi.responses import StreamingResponse

from app.db.database import get_db
from app.models.event import AttackType, NetworkEvent, RiskLevel, BlockedIP
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

class BlockRequest(BaseModel):
    ip: str
    reason: str | None = None

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
    blocked_sub = db.query(BlockedIP.ip).subquery()
    recent = (
        db.query(NetworkEvent)
        .filter(~NetworkEvent.src_ip.in_(blocked_sub)) 
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

    blocked_set = {r.ip for r in db.query(BlockedIP.ip).all()}

    events_out = []
    for e in events:
        resp = EventResponse.model_validate(e)
        resp.is_blocked = e.src_ip in blocked_set
        events_out.append(resp)

    return EventListResponse(
        total=total,
        page=page,
        page_size=page_size,
        events=events_out,
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

@router.get("/top-attackers")
def get_top_attackers(limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """IP dengan anomali terbanyak - leaderboard attacker buat panel respond."""
    rows = (
        db.query(
            NetworkEvent.src_ip,
            func.count(NetworkEvent.id).label("cnt"),
            func.max(NetworkEvent.timestamp).label("last_seen"),
        )
        .filter(NetworkEvent.is_anomaly.is_(True))
        .filter(NetworkEvent.attack_type != AttackType.NONE)
        .group_by(NetworkEvent.src_ip)
        .order_by(desc("cnt"))
        .limit(limit)
        .all()
    )
    blocked = {r.ip for r in db.query(BlockedIP.ip).all()}

    return {
        "attackers": [
            {
                "ip": r.src_ip,
                "count": r.cnt,
                "last_seen": r.last_seen,
                "is_blocked": r.src_ip in blocked,
            }
            for r in rows
        ]
    }   

@router.post("/blocklist", status_code=201)
def block_ip(payload: BlockRequest, db: Session = Depends(get_db)):
    exists = db.query(BlockedIP).filter(BlockedIP.ip == payload.ip).first()
    if exists:
        raise HTTPException(status_code=409, detail="IP sudah diblok")
    db.add(BlockedIP(ip=payload.ip, reason=payload.reason or "manual block"))
    db.commit()
    return {"status": "blocked", "ip": payload.ip}


@router.delete("/blocklist/{ip}")
def unblock_ip(ip: str, db: Session = Depends(get_db)):
    row = db.query(BlockedIP).filter(BlockedIP.ip == ip).first()
    if not row:
        raise HTTPException(status_code=404, detail="IP tidak ada di blocklist")
    db.delete(row)
    db.commit()
    return {"status": "unblocked", "ip": ip}

@router.get("/report")
def export_report(
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """
    Export anomali terbaru sebagai CSV - laporan insiden buat audit.
    Sengaja pakai limit (bukan range tanggal) biar ga ribet soal timezone.
    """
    events = (
        db.query(NetworkEvent)
        .filter(NetworkEvent.is_anomaly.is_(True))
        .order_by(NetworkEvent.timestamp.desc())
        .limit(limit)
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "timestamp", "src_ip", "dst_ip", "dst_port", "protocol",
            "attack_type", "risk_level", "anomaly_score", "is_simulated",
        ]
    )
    for e in events:
        writer.writerow(
            [
                e.timestamp.isoformat(),
                e.src_ip,
                e.dst_ip,
                e.dst_port,
                getattr(e.protocol, "value", e.protocol),
                getattr(e.attack_type, "value", e.attack_type),
                getattr(e.risk_level, "value", e.risk_level),
                e.anomaly_score,
                e.is_simulated,
            ]
        )

    buffer.seek(0)
    filename = f"aishield_incident_report_{datetime.now():%Y%m%d_%H%M%S}.csv"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )    