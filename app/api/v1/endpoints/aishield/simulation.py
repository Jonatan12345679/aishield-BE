import asyncio
import random
import time
from enum import Enum

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.endpoints.aishield.websocket import manager
from app.db.database import get_db
from app.models.event import NetworkEvent
from app.services import event_simulator
from app.services.ml_engine import ml_engine
from app.services.risk_calculator import process_event

router = APIRouter(prefix="/simulation", tags=["Simulation"])


class SimulationType(str, Enum):
    NORMAL = "normal"
    PORT_SCAN = "port_scan"
    BRUTE_FORCE = "brute_force"
    DDOS = "ddos"
    DATA_EXFILTRATION = "data_exfiltration"


class SimulationRequest(BaseModel):
    attack_type: SimulationType
    count: int | None = None  # kosongin aja biar auto (30-50), override cuma buat testing


class SimulationResponse(BaseModel):
    attack_type: str
    total_generated: int
    anomalies_detected: int
    duration_sec: float


# tiap batch di-commit terus dikasih jeda dikit, biar keliatan "ngalir"
# di LogStream bukan muncul serentak sekaligus
BATCH_SIZE = 5
BATCH_DELAY_SEC = 0.4


def _generate_raw_event(attack_type: SimulationType, ddos_target: tuple[str, int]) -> dict:
    if attack_type == SimulationType.NORMAL:
        return event_simulator.generate_normal_event()
    elif attack_type == SimulationType.PORT_SCAN:
        return event_simulator.generate_port_scan_event()
    elif attack_type == SimulationType.BRUTE_FORCE:
        return event_simulator.generate_brute_force_event()
    elif attack_type == SimulationType.DDOS:
        return event_simulator.generate_ddos_event(*ddos_target)
    elif attack_type == SimulationType.DATA_EXFILTRATION:
        return event_simulator.generate_data_exfiltration_event()
    raise ValueError(f"Attack type ga dikenal: {attack_type}")


@router.post("/trigger", response_model=SimulationResponse)
async def trigger_simulation(payload: SimulationRequest, db: Session = Depends(get_db)):
    """
    Generate event simulasi, lewatin ke ml_engine + risk_calculator kayak
    event beneran, terus disimpen ke DB dengan is_simulated=True.
 
    Sengaja generate per-batch kecil + delay dikit (bukan bulk insert
    sekaligus), biar pas dashboard nge-poll tiap 5 detik.Tiap batch juga di-broadcast
    lewat WebSocket, jadi client yang connect ga perlu nunggu polling sama
    sekali buat tau ada event baru.
    """
    count = payload.count or random.randint(30, 50)
 
    # DDoS butuh 1 target tetap sepanjang simulasi (banyak src beda nembak
    # 1 dst yang sama), jadi ditentuin sekali di awal, bukan tiap event
    ddos_target = (
        event_simulator._random_ip(internal=True),
        random.choice(event_simulator.COMMON_PORTS),
    )
 
    start = time.time()
    anomalies_detected = 0
    generated = 0
 
    while generated < count:
        batch_count = min(BATCH_SIZE, count - generated)
        batch_events = []
 
        for _ in range(batch_count):
            raw_event = _generate_raw_event(payload.attack_type, ddos_target)
            ml_result = ml_engine.predict_one(raw_event)
            final = process_event(raw_event, ml_result)
 
            db_event = NetworkEvent(
                src_ip=raw_event["src_ip"],
                dst_ip=raw_event["dst_ip"],
                src_port=raw_event["src_port"],
                dst_port=raw_event["dst_port"],
                protocol=raw_event["protocol"],
                bytes_sent=raw_event["bytes_sent"],
                bytes_received=raw_event["bytes_received"],
                packet_count=raw_event["packet_count"],
                duration_ms=raw_event["duration_ms"],
                connection_rate=raw_event["connection_rate"],
                anomaly_score=final["anomaly_score"],
                is_anomaly=final["is_anomaly"],
                risk_level=final["risk_level"],
                attack_type=final["attack_type"],
                is_simulated=True,
            )
            batch_events.append(db_event)
            if final["is_anomaly"]:
                anomalies_detected += 1
 
        db.add_all(batch_events)
        db.commit()
        for e in batch_events:
            db.refresh(e)
        generated += batch_count
 
        # broadcast tiap event di batch ini ke semua client yang connect
        await manager.broadcast(
            {
                "type": "new_events",
                "events": [
                    {
                        "id": str(e.id),
                        "timestamp": e.timestamp,
                        "src_ip": e.src_ip,
                        "dst_ip": e.dst_ip,
                        "dst_port": e.dst_port,
                        "protocol": e.protocol,
                        "risk_level": e.risk_level.value,
                        "attack_type": e.attack_type.value,
                        "anomaly_score": e.anomaly_score,
                        "is_anomaly": e.is_anomaly,
                    }
                    for e in batch_events
                ],
            }
        )
 
        if generated < count:
            await asyncio.sleep(BATCH_DELAY_SEC)
 
    return SimulationResponse(
        attack_type=payload.attack_type.value,
        total_generated=generated,
        anomalies_detected=anomalies_detected,
        duration_sec=round(time.time() - start, 2),
    )