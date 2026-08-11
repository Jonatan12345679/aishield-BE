# AIShield Backend API

Backend API untuk **AIShield**, sebuah sistem berbasis FastAPI yang menyediakan fitur **Privacy Detection** menggunakan model object detection berbasis **ONNX**.

Backend menerima gambar melalui API, menjalankan inferensi menggunakan model ONNX, mendeteksi objek yang termasuk kategori privasi, kemudian dapat melakukan **automatic blurring** pada area yang terdeteksi.

## ✨ Fitur

* 🔍 Privacy/Object Detection menggunakan model ONNX
* 🖼️ Upload gambar melalui REST API
* 🔒 Automatic blurring pada objek sensitif
* 📦 Model inference menggunakan ONNX Runtime
* ⚡ FastAPI REST API
* 🗄️ PostgreSQL untuk database
* 🐳 Docker & Docker Compose
* 📖 Swagger/OpenAPI documentation
* 🔄 Hot reload untuk development menggunakan Docker
* 🧩 Struktur backend terpisah antara API, service, model, dan konfigurasi

### Objek Privacy

Model saat ini digunakan untuk mendeteksi beberapa objek yang dianggap sensitif, seperti:

| Class ID | Object     |
| -------: | ---------- |
|        0 | Plat Nomor |
|        1 | QR Code    |
|        2 | QR Code    |
|        3 | QR Code    |
|        8 | KTP        |

> Class ID mengikuti konfigurasi model YOLO yang telah diekspor ke ONNX.

---

# 🛠️ Tech Stack

## Backend

* **Python 3.12**
* **FastAPI**
* **Uvicorn**
* **Pydantic**
* **Pydantic Settings**

## Machine Learning

* **ONNX Runtime**
* **OpenCV**
* **NumPy**

Model yang digunakan adalah model object detection yang telah diekspor ke format:

```text
ONNX (.onnx)
```

Backend **tidak membutuhkan Ultralytics untuk melakukan inference**.

Inference dilakukan langsung menggunakan:

```python
onnxruntime
```

sehingga dependency production lebih ringan.

## Database

* **PostgreSQL 16**
* **SQLAlchemy**
* **psycopg2-binary**

## Image Processing

* **OpenCV**
* **NumPy**
* **Pillow**

OpenCV digunakan untuk:

* membaca gambar
* resize
* preprocessing
* crop bounding box
* Gaussian blur
* encoding gambar kembali menjadi JPEG

## Container

* **Docker**
* **Docker Compose**

---

# 📦 Package yang Digunakan

Berikut dependency utama yang digunakan oleh backend:

```text
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.14.2
click==8.4.2
colorama==0.4.6
fastapi==0.141.1
greenlet==3.5.4
h11==0.16.0
idna==3.18
joblib==1.5.3
narwhals==2.24.0
numpy==2.5.1
pandas==3.0.5
psycopg2-binary==2.9.12
pydantic==2.13.4
pydantic-core==2.46.4
pydantic-settings==2.14.2
python-dateutil==2.9.0.post0
python-dotenv==1.2.2
scikit-learn==1.9.0
scipy==1.18.0
six==1.17.0
sqlalchemy==2.0.51
starlette==1.3.1
threadpoolctl==3.6.0
typing-extensions==4.16.0
typing-inspection==0.4.2
tzdata==2026.3
uvicorn==0.52.0

onnxruntime==1.28.0
opencv-python-headless==4.10.0.84
pillow==11.0.0
python-multipart==0.0.20
```

> `python-multipart` diperlukan oleh FastAPI untuk menerima file upload menggunakan `UploadFile` dan `File`.

---

# 📁 Struktur Project

```text
aishield-BE/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── detection.py
│   │
│   ├── services/
│   │   ├── model_loader.py
│   │   └── privacy_detector.py
│   │
│   ├── schemas/
│   │
│   ├── models/
│   │
│   └── db/
│
├── ml/
│   └── privacy-detection-model/
│       └── weights/
│           └── best.onnx
│
├── tests/
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
├── .env.example
└── README.md
```

---

# 🧠 Model Privacy Detection

Model berada di:

```text
ml/privacy-detection-model/weights/best.onnx
```

Model menerima input dengan ukuran:

```text
1 × 3 × 640 × 640
```

dan menghasilkan output:

```text
1 × 300 × 6
```

Format setiap detection:

```text
[x1, y1, x2, y2, confidence, class_id]
```

Contoh:

```json
{
  "bbox": [
    41.07,
    168.47,
    623.02,
    622.79
  ],
  "confidence": 0.566,
  "class_id": 8
}
```

Backend kemudian mengubah koordinat hasil model dari ukuran `640 × 640` ke ukuran asli gambar.

---

# ⚙️ Environment Variables

Buat file:

```text
.env
```

Contoh:

```env
DATABASE_URL=postgresql://aishield:aishield123@localhost:5432/aishield_db

MODEL_PRIVACY_DETECTION_PATH=./ml/privacy-detection-model/weights/best.onnx

DEBUG=True
```

Untuk Docker, path model menggunakan path di dalam container:

```env
MODEL_PRIVACY_DETECTION_PATH=/app/ml/privacy-detection-model/weights/best.onnx
```

---

# 🐍 Menjalankan Tanpa Docker

## 1. Clone Repository

```bash
git clone <url-repository>
cd aishield-BE
```

## 2. Buat Virtual Environment

Windows:

```bash
python -m venv venv
```

Aktifkan:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Jalankan PostgreSQL

Pastikan PostgreSQL sudah berjalan dan database:

```text
aishield_db
```

tersedia.

Contoh:

```sql
CREATE USER aishield WITH PASSWORD 'aishield123';

CREATE DATABASE aishield_db OWNER aishield;
```

## 5. Pastikan Model Ada

Pastikan file berikut tersedia:

```text
ml/privacy-detection-model/weights/best.onnx
```

## 6. Jalankan FastAPI

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API tersedia di:

```text
http://localhost:8000
```

---

# 🐳 Menjalankan Dengan Docker

Docker merupakan metode yang direkomendasikan untuk development maupun deployment.

## 1. Pastikan Docker tersedia

```bash
docker --version
docker compose version
```

## 2. Build dan Jalankan

```bash
docker compose up --build
```

atau menjalankan di background:

```bash
docker compose up -d --build
```

Docker Compose akan menjalankan:

```text
PostgreSQL
    ↓
AIShield FastAPI
```

---

# 🔄 Development dengan Hot Reload

Backend menggunakan:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

dan source code di-mount ke container.

Contoh:

```yaml
volumes:
  - ./app:/app/app
  - ./ml:/app/ml
```

Dengan konfigurasi tersebut, perubahan pada file Python di:

```text
app/
```

akan langsung terdeteksi oleh Uvicorn.

Perubahan model di:

```text
ml/
```

juga tidak membutuhkan rebuild image karena folder tersebut di-mount sebagai volume.

### Catatan

Perubahan pada:

```text
requirements.txt
Dockerfile
```

tetap membutuhkan rebuild:

```bash
docker compose up --build
```

Sedangkan perubahan biasa pada:

```text
app/
ml/
```

tidak perlu rebuild image.

---

# 🔌 API Endpoint

## Health Check

```http
GET /
```

Response:

```json
{
  "status": "online",
  "system": "AIShield Engine",
  "version": "1.0.0"
}
```

---

# 🔍 Privacy Detection

Endpoint:

```http
POST /api/v1/detect
```

Request menggunakan:

```text
multipart/form-data
```

dengan field:

```text
file
```

Contoh menggunakan cURL:

```bash
curl -X POST "http://localhost:8000/api/v1/detect" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg"
```

Contoh response:

```json
{
  "count": 1,
  "detections": [
    {
      "bbox": [
        41.0748291015625,
        168.47264099121094,
        623.0267944335938,
        622.7951049804688
      ],
      "confidence": 0.56645268201828,
      "class_id": 8
    }
  ]
}
```

---

# 🖼️ Privacy Blurring

Backend juga menyediakan proses untuk melakukan blur pada area yang terdeteksi.

Alurnya:

```text
Upload Image
      │
      ▼
Decode Image
      │
      ▼
Resize 640 × 640
      │
      ▼
ONNX Inference
      │
      ▼
Detection
      │
      ▼
Filter Confidence
      │
      ▼
Convert BBox
to Original Image
      │
      ▼
Gaussian Blur
      │
      ▼
Encode JPEG
      │
      ▼
Return Image
```

Area yang termasuk kategori privacy akan diproses menggunakan:

```python
cv2.GaussianBlur()
```

Contoh:

```python
blurred = cv2.GaussianBlur(
    roi,
    (51, 51),
    30
)
```

---

# 🔐 Privacy Class Filtering

Backend dapat menentukan class mana yang harus diblur.

Contoh:

```python
PRIVACY_CLASSES = {
    0,  # plat_nomor
    1,  # QR_CODE
    2,  # qr_code
    3,  # qrcode
    8   # ktp
}
```

Class yang tidak termasuk dalam daftar tersebut tidak akan diblur.

Hal ini memungkinkan model memiliki banyak class tetapi hanya sebagian class yang dianggap sebagai informasi sensitif.

---

# 📖 API Documentation

Setelah server berjalan, dokumentasi Swagger dapat diakses melalui:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

Swagger dapat digunakan untuk langsung melakukan testing upload gambar tanpa menggunakan Postman.

---

# 🗄️ PostgreSQL

Database menggunakan:

```text
PostgreSQL 16
```

Konfigurasi Docker:

```text
Host     : postgres
Port     : 5432
Database : aishield_db
Username : aishield
Password : aishield123
```

Ketika backend berjalan di Docker Compose, backend harus menggunakan hostname:

```text
postgres
```

bukan:

```text
localhost
```

Contoh:

```env
DATABASE_URL=postgresql://aishield:aishield123@postgres:5432/aishield_db
```

---

# 🛑 Menghentikan Docker

Untuk menghentikan container:

```bash
docker compose down
```

Untuk menghapus container sekaligus volume database:

```bash
docker compose down -v
```

> `-v` akan menghapus data PostgreSQL yang tersimpan pada Docker volume.

---

# 🔧 Troubleshooting

## Model tidak ditemukan

Jika muncul:

```text
NO_SUCHFILE : Load model ... best.onnx failed
```

cek:

```bash
docker exec -it aishield-api bash
```

kemudian:

```bash
find /app/ml -name "*.onnx"
```

Model seharusnya berada di:

```text
/app/ml/privacy-detection-model/weights/best.onnx
```

Pastikan `docker-compose.yml` memiliki:

```yaml
volumes:
  - ./ml:/app/ml
```

---

## `python-multipart` tidak ditemukan

Jika muncul:

```text
Form data requires "python-multipart" to be installed
```

pastikan terdapat:

```text
python-multipart==0.0.20
```

di `requirements.txt`.

Kemudian rebuild:

```bash
docker compose up --build
```

---

## Perubahan Python tidak terlihat

Pastikan backend menggunakan:

```bash
--reload
```

dan:

```yaml
volumes:
  - ./app:/app/app
```

Kemudian lihat log:

```bash
docker compose logs -f backend
```

---

## Dependency berubah

Jika `requirements.txt` berubah, jalankan:

```bash
docker compose up --build
```

Karena dependency di-install ketika Docker image dibuat.

---

# 🚀 Production

Untuk production, konfigurasi development sebaiknya disesuaikan.

Contohnya:

* nonaktifkan `--reload`
* gunakan environment variable production
* jangan expose PostgreSQL secara publik
* gunakan reverse proxy seperti Nginx
* gunakan HTTPS
* gunakan secret yang aman
* gunakan Docker image yang lebih minimal
* gunakan resource limit untuk container
* gunakan model ONNX langsung dengan ONNX Runtime

Development:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Production:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# 📌 Architecture

Secara sederhana, AIShield Backend menggunakan arsitektur:

```text
                 ┌──────────────┐
                 │   Client     │
                 │ Web / Mobile │
                 └──────┬───────┘
                        │
                        │ HTTP
                        ▼
              ┌──────────────────┐
              │     FastAPI      │
              │      Router      │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Privacy Detector │
              │     Service      │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   ONNX Runtime   │
              │   best.onnx      │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   Detection      │
              │ Bounding Boxes   │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Image Blurring  │
              │     OpenCV       │
              └────────┬─────────┘
                       │
                       ▼
                 Processed Image
```

---

# 👨‍💻 Development

Untuk menjalankan project dalam mode development:

```bash
docker compose up
```

Kemudian buka:

```text
http://localhost:8000/docs
```

Setelah melakukan perubahan pada:

```text
app/
```

Uvicorn akan melakukan reload secara otomatis.

---

# 📄 License

Project ini dikembangkan untuk kebutuhan **AIShield**.

---

# 👥 Contributors

AIShield Development Team
