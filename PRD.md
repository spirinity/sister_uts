Product Requirements Document (PRD)
Project Name: Pub-Sub Log Aggregator (UTS Sistem Terdistribusi)
Platform: Backend API (Local / Containerized)
Tech Stack: Python 3.11, FastAPI, asyncio, SQLite, Pytest, Docker

1. Project Overview
Tujuan Proyek: Membangun sebuah layanan backend yang mengimplementasikan pola arsitektur Publish-Subscribe untuk memproses event/log. Sistem harus memiliki consumer yang bersifat idempotent (mampu menerima pesan yang sama berkali-kali tanpa memprosesnya ganda) dan dilengkapi dengan mekanisme deduplikasi yang tahan terhadap kegagalan sistem (crash/restart).

2. System Architecture
Sistem akan beroperasi sepenuhnya di dalam memori lokal (satu container), tanpa menggunakan message broker eksternal seperti Kafka atau RabbitMQ.

Publisher: Klien eksternal (atau script simulator) yang menembak endpoint REST API.

Pub-Sub Channel: Menggunakan asyncio.Queue sebagai buffer antrean di dalam memori.

Consumer/Subscriber: Sebuah background task di FastAPI yang terus-menerus menarik (pull) data dari antrean.

Deduplication Store: Database relasional berbasis file (SQLite) untuk menyimpan histori event_id secara persisten guna mencegah duplikasi.

3. Functional Requirements (Kebutuhan Fungsional)
Sistem harus memiliki tiga buah REST API endpoints utama:

A. Endpoint Publish (POST /publish)
Fungsi: Menerima data event masuk.

Payload Schema: Harus memvalidasi struktur JSON minimal berisi: topic (string), event_id (string-unik), timestamp (ISO8601), source (string), dan payload (objek).

Perilaku: Data yang valid dimasukkan ke dalam antrean internal (asyncio.Queue) dan API segera mengembalikan respons sukses HTTP 202 (Accepted) atau HTTP 200 (OK).

B. Endpoint Events (GET /events?topic=...)
Fungsi: Menampilkan daftar log/event yang unik (sudah lolos tahap deduplikasi).

Filter: Mendukung parameter query opsional topic untuk menyaring hasil.

C. Endpoint Stats (GET /stats)
Fungsi: Menyajikan metrik kesehatan sistem secara real-time.

Response Payload: Menampilkan minimal atribut received (total masuk), unique_processed (total lolos), duplicate_dropped (total ditolak), topics (daftar topik aktif), dan uptime (lama sistem menyala).

4. Core Logic & Constraints (Logika Utama)
Idempotency: Consumer harus mengecek database sebelum memproses event. Jika kombinasi topic dan event_id sudah ada di database, sistem akan mengabaikan event tersebut dan mencatatnya sebagai duplicate_dropped.

Durability (Tahan Restart): Penyimpanan status duplikasi (Deduplication Store) harus ditulis ke disk (menggunakan SQLite data.db atau JSON file). Memori internal saja tidak cukup.

Logging: Sistem harus mencetak peringatan ke terminal/console jika terdeteksi duplikasi pesan.

Isolasi Jaringan: Keseluruhan layanan harus dibungkus dalam satu Dockerfile dan tidak boleh melakukan koneksi keluar untuk database atau antrean (semua embedded).

5. Non-Functional Requirements & Performance
Skalabilitas Uji: Sistem tidak boleh crash atau melambat signifikan saat diserang dengan beban uji >= 5.000 event yang memiliki tingkat duplikasi >= 20%.

Base Image Docker: Wajib menggunakan image yang ringan dan aman (misalnya python:3.11-slim), serta menjalankan aplikasi menggunakan non-root user.

6. Testing & Acceptance Criteria (Kriteria Kelulusan)
Pengujian otomatis (Unit Tests) menggunakan pytest wajib menutupi skenario berikut:

Duplicate Rejection AC: Mengirim event_id yang sama dua kali. Ekspektasi: unique_processed bertambah 1, duplicate_dropped bertambah 1.

Schema Validation AC: Mengirim JSON tanpa field timestamp. Ekspektasi: API menolak dengan HTTP 422 (Unprocessable Entity) / HTTP 400 (Bad Request).

Persistence AC: Sistem dihentikan secara paksa (simulated restart). Ekspektasi: Event duplikat yang dikirim pasca-restart tetap ditolak.

Stats Consistency AC: Jumlah data yang dikembalikan oleh GET /events harus sama persis dengan angka unique_processed di GET /stats.