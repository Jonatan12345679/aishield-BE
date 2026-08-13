from app.db.database import SessionLocal
from app.models.event import NetworkEvent
from app.services.ml_engine import ml_engine
from app.services.risk_calculator import process_event
 
BATCH_SIZE = 500
 
 
def reprocess_all() -> None:
    db = SessionLocal()
 
    try:
        total = db.query(NetworkEvent).count()
        print(f"Total event yang mau diproses ulang: {total}")
 
        offset = 0
        processed = 0
 
        while offset < total:
            batch = (
                db.query(NetworkEvent)
                .order_by(NetworkEvent.timestamp)
                .offset(offset)
                .limit(BATCH_SIZE)
                .all()
            )
            if not batch:
                break
 
            # susun fitur mentah dari tiap row buat dilempar ke model
            raw_events = [
                {
                    "bytes_sent": e.bytes_sent,
                    "bytes_received": e.bytes_received,
                    "packet_count": e.packet_count,
                    "duration_ms": e.duration_ms,
                    "connection_rate": e.connection_rate,
                    "dst_port": e.dst_port,
                }
                for e in batch
            ]
 
            ml_results = ml_engine.predict_batch(raw_events)
 
            # update tiap row satu-satu, gabungin hasil IForest + rule backup
            for db_event, raw, ml_result in zip(batch, raw_events, ml_results, strict=True):
                final = process_event(raw, ml_result)
                db_event.anomaly_score = final["anomaly_score"]
                db_event.is_anomaly = final["is_anomaly"]
                db_event.risk_level = final["risk_level"]
                db_event.attack_type = final["attack_type"]
 
            db.commit()
            processed += len(batch)
            offset += BATCH_SIZE
            print(f"  ...{processed}/{total} event diproses ulang")
 
        print(f"\nSelesai. Total {processed} event berhasil di-reprocess.")
 
        # ringkasan cepat 
        anomaly_count = db.query(NetworkEvent).filter(NetworkEvent.is_anomaly.is_(True)).count()
        print(f"Jumlah anomali setelah reprocess: {anomaly_count}")
 
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
 
 
if __name__ == "__main__":
    reprocess_all()