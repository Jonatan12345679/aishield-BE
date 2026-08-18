# Aegis AI — Backend

Backend untuk Aegis AI, platform AI dengan 2 modul utama yang melayani 1 platform:

- AIShield — engine deteksi anomali jaringan pakai Isolation Forest + REST API + WebSocket realtime
- BlurAI — engine privacy detection pakai YOLO (ONNX) + auto-blur

Repo ini isinya backend FastAPI + PostgreSQL + Docker. Frontend ada di repo terpisah (`aishield-frontend`).

---

## 🖥️ Tech Stack

### Core
- Python 3.12
- FastAPI 0.141 + Uvicorn
- Pydantic v2 + Pydantic Settings
- PostgreSQL 16 + SQLAlchemy 2.0 + psycopg2-binary

### Machine Learning
- scikit-learn — Isolation Forest (AIShield)
- pandas / numpy — data processing
- ONNX Runtime — inference model YOLO (BlurAI)
- OpenCV — image preprocessing & blurring (BlurAI)
- Pillow — image handling (BlurAI)

### Infrastructure
- Docker + Docker Compose
- WebSocket untuk realtime broadcast
- Swagger / ReDoc auto-generated API docs

### Dependencies (utama)
fastapi==0.141.1
uvicorn==0.52.0
sqlalchemy==2.0.51
psycopg2-binary==2.9.12
pydantic==2.13.4
pydantic-settings==2.14.2
scikit-learn==1.9.0
pandas==3.0.5
onnxruntime==1.28.0
opencv-python-headless==4.10.0.84
pillow==11.0.0
python-multipart==0.0.20

## 📦 Struktur Project
```
aishield-backend
├─ .dockerignore
├─ app
│  ├─ api
│  │  ├─ v1
│  │  │  ├─ endpoints
│  │  │  │  ├─ aishield
│  │  │  │  │  ├─ dashboard.py
│  │  │  │  │  ├─ simulation.py
│  │  │  │  │  ├─ websocket.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ privacy_detection
│  │  │  │  │  ├─ detection.py
│  │  │  │  │  ├─ realtime.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  └─ __init__.py
│  │  │  ├─ router.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ core
│  │  ├─ config.py
│  │  └─ __init__.py
│  ├─ db
│  │  ├─ database.py
│  │  └─ __init__.py
│  ├─ main.py
│  ├─ models
│  │  ├─ event.py
│  │  └─ __init__.py
│  ├─ schemas
│  │  ├─ detection.py
│  │  ├─ event.py
│  │  ├─ explain.py
│  │  └─ __init__.py
│  ├─ services
│  │  ├─ event_simulator.py
│  │  ├─ explain_engine.py
│  │  ├─ ml_engine.py
│  │  ├─ model_loader.py
│  │  ├─ privacy_detector.py
│  │  ├─ privacy_engine.py
│  │  ├─ realtime_detector.py
│  │  ├─ risk_calculator.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ docker-compose.yml
├─ Dockerfile
├─ ml
│  ├─ aishield
│  │  ├─ dataset
│  │  │  └─ synthetic_events.csv
│  │  ├─ model
│  │  │  ├─ feature_columns.json
│  │  │  ├─ metrics.json
│  │  │  └─ scaler.pkl
│  │  ├─ synthetic_generator.py
│  │  └─ train.py
│  └─ __init__.py
├─ readme.md
├─ requirements.txt
└─ scripts
   ├─ init.sql
   ├─ reprocess_events.py
   ├─ seed_from_csv.py
   ├─ test_db_connection.py
   └─ __init__.py

```

 
---

## ✨ Modul 1: AIShield (Network Anomaly Detection)

Dashboard SOC buat monitoring anomali jaringan. Engine utamanya Isolation Forest — unsupervised ML yang flag event yang "aneh" dibanding baseline traffic normal.

### Fitur
- REST API buat dashboard stats, events, risk score, model metrics
- Event Simulator — generate synthetic traffic (normal + 4 attack types) buat demo
- ML Pipeline — scaler + Isolation Forest + risk calculator
- WebSocket broadcast — realtime push event ke semua client
- XAI Explain — z-score per fitur vs baseline, jelasin kenapa event di-flag
- Top Attackers + IP Blocklist — block/unblock attacker, exclude dari risk score
- CSV Export — laporan insiden siap audit

### Attack Types yang Didukung
| Type | Deskripsi |
|---|---|
| `normal` | traffic biasa |
| `port_scan` | scanning port target |
| `brute_force` | upaya login paksa berulang |
| `ddos` | flood dari banyak source ke 1 target |
| `data_exfiltration` | exfiltration data keluar |

### Endpoints AIShield

| Method | Path | Fungsi |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | angka ringkasan buat StatCards |
| GET | `/api/v1/dashboard/risk-score` | skor risiko realtime (window 100 event terbaru) |
| GET | `/api/v1/dashboard/events` | list event (pagination + filter) |
| GET | `/api/v1/dashboard/events/{id}/explain` | XAI penjelasan per-fitur |
| GET | `/api/v1/dashboard/top-attackers` | leaderboard IP attacker |
| POST | `/api/v1/dashboard/blocklist` | block IP |
| DELETE | `/api/v1/dashboard/blocklist/{ip}` | unblock IP |
| GET | `/api/v1/dashboard/model-metrics` | metrics.json (F1, recall, confusion matrix) |
| GET | `/api/v1/dashboard/report` | export CSV |
| POST | `/api/v1/simulation/trigger` | trigger simulasi serangan |
| WS | `/api/v1/ws/events` | WebSocket realtime |

### Model AIShield

Ada di `ml/aishield/model/`:

| File | Isi |
|---|---|
| `isolation_forest.pkl` | model yang sudah di-training |
| `scaler.pkl` | StandardScaler (mean_ & scale_ dipakai buat XAI) |
| `feature_columns.json` | urutan 9 fitur yang di-ekstrak |
| `metrics.json` | hasil evaluasi (precision, recall, F1, confusion matrix, per-attack recall) |

Feature engineering-nya single source of truth di `ml/aishield/train.py::engineer_features()` — dipanggil sama-sama oleh training, inference, dan XAI. Jadi penjelasan fitur selalu cocok dengan apa yang dilihat model.

---

## ✨ Modul 2: BlurAI (Privacy Detection)

Engine privacy protection. Terima gambar, deteksi area sensitif pakai YOLO (ONNX), otomatis blur region-nya.

### Fitur
- Privacy/Object Detection pakai model ONNX
- Upload gambar via REST API (`multipart/form-data`)
- Automatic blurring dengan Gaussian Blur OpenCV
- ONNX Runtime — inference tanpa dependency Ultralytics (lebih ringan di production)

### Object Classes (Privacy)

| Class ID | Object |
|---|---|
| 0 | Plat Nomor |
| 1 | QR Code |
| 2 | QR Code |
| 3 | QR Code |
| 8 | KTP |

> Class ID ikut konfigurasi YOLO yang di-export ke ONNX.

### Endpoints BlurAI

| Method | Path | Fungsi |
|---|---|---|
| POST | `/api/v1/privacy-detection/detect` | deteksi tanpa blur |
| POST | `/api/v1/privacy-detection/blur` | deteksi + auto-blur |

Request pakai `multipart/form-data` dengan field `file`.

Response `detect`:
```json
{
  "count": 1,
  "detections": [
    {
      "bbox": [41.07, 168.47, 623.02, 622.79],
      "confidence": 0.566,
      "class_id": 8
    }
  ]
}


## 🚀 Cara Jalankan
docker --version
docker compose version

## setup env
# Aegis AI — Backend

Backend untuk Aegis AI, platform AI dengan 2 modul utama yang melayani 1 platform:

- AIShield — engine deteksi anomali jaringan pakai Isolation Forest + REST API + WebSocket realtime
- BlurAI — engine privacy detection pakai YOLO (ONNX) + auto-blur

Repo ini isinya backend FastAPI + PostgreSQL + Docker. Frontend ada di repo terpisah (`aishield-frontend`).

---

## 🖥️ Tech Stack

### Core
- Python 3.12
- FastAPI 0.141 + Uvicorn
- Pydantic v2 + Pydantic Settings
- PostgreSQL 16 + SQLAlchemy 2.0 + psycopg2-binary

### Machine Learning
- scikit-learn — Isolation Forest (AIShield)
- pandas / numpy — data processing
- ONNX Runtime — inference model YOLO (BlurAI)
- OpenCV — image preprocessing & blurring (BlurAI)
- Pillow — image handling (BlurAI)

### Infrastructure
- Docker + Docker Compose
- WebSocket untuk realtime broadcast
- Swagger / ReDoc auto-generated API docs

### Dependencies (utama)
fastapi==0.141.1
uvicorn==0.52.0
sqlalchemy==2.0.51
psycopg2-binary==2.9.12
pydantic==2.13.4
pydantic-settings==2.14.2
scikit-learn==1.9.0
pandas==3.0.5
onnxruntime==1.28.0
opencv-python-headless==4.10.0.84
pillow==11.0.0
python-multipart==0.0.20

## 📦 Struktur Project
```
aishield-backend
├─ .dockerignore
├─ app
│  ├─ api
│  │  ├─ v1
│  │  │  ├─ endpoints
│  │  │  │  ├─ aishield
│  │  │  │  │  ├─ dashboard.py
│  │  │  │  │  ├─ simulation.py
│  │  │  │  │  ├─ websocket.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  ├─ privacy_detection
│  │  │  │  │  ├─ detection.py
│  │  │  │  │  ├─ realtime.py
│  │  │  │  │  └─ __init__.py
│  │  │  │  └─ __init__.py
│  │  │  ├─ router.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ core
│  │  ├─ config.py
│  │  └─ __init__.py
│  ├─ db
│  │  ├─ database.py
│  │  └─ __init__.py
│  ├─ main.py
│  ├─ models
│  │  ├─ event.py
│  │  └─ __init__.py
│  ├─ schemas
│  │  ├─ detection.py
│  │  ├─ event.py
│  │  ├─ explain.py
│  │  └─ __init__.py
│  ├─ services
│  │  ├─ event_simulator.py
│  │  ├─ explain_engine.py
│  │  ├─ ml_engine.py
│  │  ├─ model_loader.py
│  │  ├─ privacy_detector.py
│  │  ├─ privacy_engine.py
│  │  ├─ realtime_detector.py
│  │  ├─ risk_calculator.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ docker-compose.yml
├─ Dockerfile
├─ ml
│  ├─ aishield
│  │  ├─ dataset
│  │  │  └─ synthetic_events.csv
│  │  ├─ model
│  │  │  ├─ feature_columns.json
│  │  │  ├─ metrics.json
│  │  │  └─ scaler.pkl
│  │  ├─ synthetic_generator.py
│  │  └─ train.py
│  └─ __init__.py
├─ readme.md
├─ requirements.txt
└─ scripts
   ├─ init.sql
   ├─ reprocess_events.py
   ├─ seed_from_csv.py
   ├─ test_db_connection.py
   └─ __init__.py

```

 
---

## ✨ Modul 1: AIShield (Network Anomaly Detection)

Dashboard SOC buat monitoring anomali jaringan. Engine utamanya Isolation Forest — unsupervised ML yang flag event yang "aneh" dibanding baseline traffic normal.

### Fitur
- REST API buat dashboard stats, events, risk score, model metrics
- Event Simulator — generate synthetic traffic (normal + 4 attack types) buat demo
- ML Pipeline — scaler + Isolation Forest + risk calculator
- WebSocket broadcast — realtime push event ke semua client
- XAI Explain — z-score per fitur vs baseline, jelasin kenapa event di-flag
- Top Attackers + IP Blocklist — block/unblock attacker, exclude dari risk score
- CSV Export — laporan insiden siap audit

### Attack Types yang Didukung
| Type | Deskripsi |
|---|---|
| `normal` | traffic biasa |
| `port_scan` | scanning port target |
| `brute_force` | upaya login paksa berulang |
| `ddos` | flood dari banyak source ke 1 target |
| `data_exfiltration` | exfiltration data keluar |

### Endpoints AIShield

| Method | Path | Fungsi |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | angka ringkasan buat StatCards |
| GET | `/api/v1/dashboard/risk-score` | skor risiko realtime (window 100 event terbaru) |
| GET | `/api/v1/dashboard/events` | list event (pagination + filter) |
| GET | `/api/v1/dashboard/events/{id}/explain` | XAI penjelasan per-fitur |
| GET | `/api/v1/dashboard/top-attackers` | leaderboard IP attacker |
| POST | `/api/v1/dashboard/blocklist` | block IP |
| DELETE | `/api/v1/dashboard/blocklist/{ip}` | unblock IP |
| GET | `/api/v1/dashboard/model-metrics` | metrics.json (F1, recall, confusion matrix) |
| GET | `/api/v1/dashboard/report` | export CSV |
| POST | `/api/v1/simulation/trigger` | trigger simulasi serangan |
| WS | `/api/v1/ws/events` | WebSocket realtime |

### Model AIShield

Ada di `ml/aishield/model/`:

| File | Isi |
|---|---|
| `isolation_forest.pkl` | model yang sudah di-training |
| `scaler.pkl` | StandardScaler (mean_ & scale_ dipakai buat XAI) |
| `feature_columns.json` | urutan 9 fitur yang di-ekstrak |
| `metrics.json` | hasil evaluasi (precision, recall, F1, confusion matrix, per-attack recall) |

Feature engineering-nya single source of truth di `ml/aishield/train.py::engineer_features()` — dipanggil sama-sama oleh training, inference, dan XAI. Jadi penjelasan fitur selalu cocok dengan apa yang dilihat model.

---

## ✨ Modul 2: BlurAI (Privacy Detection)

Engine privacy protection. Terima gambar, deteksi area sensitif pakai YOLO (ONNX), otomatis blur region-nya.

### Fitur
- Privacy/Object Detection pakai model ONNX
- Upload gambar via REST API (`multipart/form-data`)
- Automatic blurring dengan Gaussian Blur OpenCV
- ONNX Runtime — inference tanpa dependency Ultralytics (lebih ringan di production)

### Object Classes (Privacy)

| Class ID | Object |
|---|---|
| 0 | Plat Nomor |
| 1 | QR Code |
| 2 | QR Code |
| 3 | QR Code |
| 8 | KTP |

> Class ID ikut konfigurasi YOLO yang di-export ke ONNX.

### Endpoints BlurAI

| Method | Path | Fungsi |
|---|---|---|
| POST | `/api/v1/privacy-detection/detect` | deteksi tanpa blur |
| POST | `/api/v1/privacy-detection/blur` | deteksi + auto-blur |

Request pakai `multipart/form-data` dengan field `file`.

Response `detect`:
```json
{
  "count": 1,
  "detections": [
    {
      "bbox": [41.07, 168.47, 623.02, 622.79],
      "confidence": 0.566,
      "class_id": 8
    }
  ]
}


## 🚀 Cara Jalankan
docker --version
docker compose version

## setup env
DATABASE_URL=postgresql+psycopg2://aishield:aishield123@postgres:5432/aishield_db
DB_ECHO=false
DB_POOL_SIZE=10

# model paths (di dalam container)
ML_MODEL_PATH=./ml/aishield/model/isolation_forest.pkl
ML_SCALER_PATH=ml/aishield/model/scaler.pkl
ML_METRICS_PATH=ml/aishield/model/metrics.json
ML_FEATURE_COLUMNS_PATH=ml/aishield/model/feature_columns.json

MODEL_PRIVACY_DETECTION_KTP_PATH=./ml/privacy-detection-model/weights/best.onnx
MODEL_PRIVACY_DETECTION_PLAT_NOMOR_PATH=./ml/privacy-detection-model/weights/best.onnx
MODEL_PRIVACY_DETECTION_QR_CODE_PATH=./ml/privacy-detection-model/weights/best.onnx
MODEL_PRIVACY_DETECTION_STRUK_PATH=./ml/privacy-detection-model/weights/best.onnx
MODEL_PRIVACY_DETECTION_STRUK_AND_KTP_PATH=./ml/privacy-detection-model/weights/best.onnx

DEBUG=true
APP_ENV=development

## build and run
docker compose up -d --build

 ## Cek
API: http://localhost:8000
Swagger: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
WebSocket: ws://localhost:8000/api/v1/ws/events

development:
``
bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Production
``
bash
uvicorn app.main:app --host 0.0.0.0 --port 8000

🤝 Tim
Aegis AI Team
