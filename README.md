# Pub-Sub Log Aggregator (UTS Sistem Terdistribusi)

Layanan Pub-Sub log aggregator dengan **Idempotent Consumer** dan **Deduplication Store**. Didesain untuk memenuhi kriteria UTS dengan performa tinggi menggunakan FastAPI dan antrean `asyncio`.

## Prasyarat
- [Docker](https://www.docker.com/) & Docker Compose terinstal.

## Cara Menjalankan Aplikasi (Docker Compose)
Aplikasi ini sudah dipisahkan menjadi dua buah *service*: `aggregator` (server utama) dan `publisher` (simulasi pengirim data duplikat secara terus-menerus).

1. Buka terminal di direktori proyek ini.
2. Jalankan perintah berikut untuk mem-build dan menyalakan container:
   ```bash
   docker-compose up --build -d
   ```
3. Cek log dari aggregator dan publisher:
   ```bash
   docker-compose logs -f
   ```
   *Anda akan melihat publisher terus mengirim data ganda, dan aggregator membuang duplikat tersebut.*
4. Untuk menghentikan container:
   ```bash
   docker-compose down
   ```

## Endpoint API
Setelah aplikasi menyala, server dapat diakses di `http://localhost:8080`. Dokumentasi interaktif (Swagger UI) tersedia di: **`http://localhost:8080/docs`**.

1. **`POST /publish`**: Mengirim log (mendukung single/batch).
2. **`GET /events`**: Menampilkan riwayat log yang berhasil diproses secara persisten.
3. **`GET /stats`**: Menampilkan statistik *real-time* (received, processed, duplicate_dropped).

## Asumsi Desain
1. **At-Least-Once Delivery**: Diasumsikan Publisher bisa saja mengirim ulang pesan yang sama (karena *network timeout* dsb).
2. **Local-Only Deduplication**: Sistem didesain berjalan lokal (single node) sehingga `SQLite` sudah sangat cukup untuk menangani fitur *persistance* dan mencegah *re-processing* setelah server mati/restart.
3. **Total Ordering**: Dalam konteks aggregator ini, urutan pasti (*Total Ordering*) tidak begitu diutamakan, yang lebih dipentingkan adalah *Idempotency* (tidak memproses log yang sama dua kali) agar statistik konsisten.

## Menjalankan Unit Test (Opsional)
Jika Anda memiliki Python di lokal (tanpa Docker), Anda bisa menjalankan *Unit Testing* otomatis dengan `pytest`:
```bash
pip install -r requirements.txt
pytest
```
