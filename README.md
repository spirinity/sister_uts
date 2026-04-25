# UTS Sistem Terdistribusi & Parallel
## Pub-Sub Log Aggregator

| | |
|---|---|
| **Nama** | Mahardika Arka |
| **NIM** | 11231037 |
| **Mata Kuliah** | Sistem Terdistribusi & Parallel |

Layanan Pub-Sub log aggregator berbasis **FastAPI** dan **asyncio** dengan fitur **Idempoten Consumer** dan **Persistent Deduplication Store**. Sistem ini dirancang untuk menerima event/log dari publisher, memvalidasinya, dan memastikan event yang sama tidak pernah diproses lebih dari sekali — bahkan setelah server di-restart.

## Video Tutorial Youtube:
Link Video: https://www.youtube.com/watch?v=lUz1zi9Rfyo
---

## Arsitektur

![Arsitektur Sistem Pub-Sub Log Aggregator](docs/DIAGRAM%20SISTER.png)

> Diagram di atas menggambarkan alur lengkap dari Publisher Container → FastAPI Interface → Internal Queue (asyncio) → Consumer/Background Worker → Deduplication Store (SQLite). Event yang sudah ada di store akan di-*drop* (Dropped), sedangkan event baru akan disimpan (Insert & Keep).

## Struktur Proyek

```
UTS/
├── src/
│   ├── main.py           # Entry point FastAPI, definisi semua endpoint
│   ├── consumer.py       # Background consumer (idempotent processor)
│   ├── dedup_store.py    # Deduplication store berbasis SQLite
│   ├── queue_manager.py  # Wrapper asyncio.Queue
│   ├── stats.py          # Counter metrik in-memory
│   ├── models.py         # Schema Event (Pydantic)
│   └── publisher.py      # Simulasi publisher (At-Least-Once Delivery)
├── tests/
│   ├── conftest.py       # Fixtures & helpers pytest
│   ├── test_dedup.py     # Uji idempotency, dedup, dan persistensi
│   ├── test_events.py    # Uji GET /events, filter topic, dan konsistensi stats
│   ├── test_publish.py   # Uji POST /publish (validasi schema, batch, error)
│   └── test_stress.py    # Stress test 5.000 event dengan 20% duplikasi
├── data/                 # Volume SQLite (dibuat otomatis)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pytest.ini
```

---

## Cara Menjalankan

### Prasyarat
- [Docker](https://www.docker.com/) & Docker Compose terinstal

### 1. Jalankan Server (Docker Compose)

```bash
docker-compose up --build
```

Server API akan menyala di **http://localhost:8080**.
Dokumentasi interaktif Swagger UI tersedia di **http://localhost:8080/docs**.

> Hanya service `aggregator` yang menyala otomatis. Service `publisher` dan `test` bersifat manual.

### 2. Kirim Event Simulasi (Manual)

Buka terminal baru, lalu jalankan:
```bash
docker-compose run --rm publisher
```
Publisher akan mengirimkan **1 event asli + 1 duplikat** ke aggregator, lalu berhenti.

### 3. Jalankan Unit Test (di dalam Docker)

```bash
docker-compose run --rm test
```

### 4. Hentikan Server

```bash
docker-compose down
```

---

## Menjalankan Tanpa Docker (Lokal)

```bash
# Install dependencies
pip install -r requirements.txt

# Jalankan server
python -m src.main

# (Terminal baru) Jalankan publisher
python -m src.publisher

# (Terminal baru) Jalankan unit test
python -m pytest tests/ -v
```

---

## 🔌 Endpoint API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `POST` | `/publish` | Kirim satu atau banyak (batch) event |
| `GET`  | `/events` | Lihat daftar event unik yang sudah diproses |
| `GET`  | `/events?topic=<nama>` | Filter event berdasarkan topik |
| `GET`  | `/stats` | Lihat statistik sistem secara real-time |

### Contoh Request `POST /publish`

**Single Event:**
```json
{
  "topic": "user-events",
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2026-04-25T10:00:00Z",
  "source": "auth-service",
  "payload": { "user_id": 1, "action": "login_success" }
}
```

**Batch Events (Array):**
```json
[
  { "topic": "order-events", "event_id": "aaa-001", "timestamp": "2026-04-25T10:01:00Z", "source": "order-service", "payload": { "order_id": "ORD-001" } },
  { "topic": "order-events", "event_id": "aaa-002", "timestamp": "2026-04-25T10:01:05Z", "source": "order-service", "payload": { "order_id": "ORD-002" } }
]
```

### Contoh Response `GET /stats`

```json
{
  "received": 10,
  "unique_processed": 8,
  "duplicate_dropped": 2,
  "topics": ["order-events", "user-events"],
  "uptime_seconds": 42.3
}
```

---

## Unit Tests

Terdapat **14 test case** yang mencakup seluruh *Acceptance Criteria* dari brief UTS:

| File | Test Case | Deskripsi |
|------|-----------|-----------|
| `test_dedup.py` | TC-D1 | Duplikat ditolak: `unique_processed=1`, `duplicate_dropped=1` |
| `test_dedup.py` | TC-D2 | Batch berisi duplikat internal |
| `test_dedup.py` | TC-D3 | Persistensi: dedup tetap aktif setelah simulasi restart |
| `test_publish.py` | TC-P1 | Validasi schema: tolak event tanpa `timestamp` (HTTP 422) |
| `test_publish.py` | TC-P2 | Single event valid diterima (HTTP 202) |
| `test_publish.py` | TC-P3 | Batch event valid diterima |
| `test_events.py` | TC-E1 | `GET /events` mengembalikan semua event unik |
| `test_events.py` | TC-E2 | Filter `?topic=X` hanya mengembalikan event topic X |
| `test_events.py` | TC-E3 | Konsistensi: `len(GET /events) == stats.unique_processed` |
| `test_events.py` | TC-E4 | `GET /events` saat kosong mengembalikan list kosong |
| `test_events.py` | TC-E5 | `GET /stats` memiliki semua field yang diperlukan |
| `test_stress.py` | TC-S1 | Stress test: 5.000 event, 20% duplikasi, selesai < 120 detik |

---

## Asumsi Desain

1. **At-Least-Once Delivery**: Publisher diasumsikan dapat mengirim ulang event yang sama akibat *network timeout* atau *retry*. Consumer dirancang idempotent untuk menangani skenario ini.
2. **Local-Only Deduplication**: Sistem berjalan sebagai *single node*, sehingga SQLite sudah memadai sebagai *persistent dedup store*.
3. **Total Ordering**: Tidak diutamakan dalam konteks aggregator ini. Yang lebih krusial adalah *idempotency* untuk menjaga konsistensi statistik.
4. **Dedup Key**: Berdasarkan kombinasi `(topic, event_id)`, bukan `event_id` saja — memungkinkan event_id yang sama di topik berbeda tetap diproses secara independen.
