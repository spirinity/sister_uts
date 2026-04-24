import time
import httpx
import uuid
import os
from datetime import datetime, timezone

AGGREGATOR_URL = os.getenv("AGGREGATOR_URL", "http://localhost:8080/publish")

def run_publisher():
    print(f"Memulai Publisher... Target: {AGGREGATOR_URL}")
    print("Menunggu Aggregator siap...")
    time.sleep(5)  # Beri waktu sebentar agar aggregator di Docker Compose siap menerima request
    
    try:
        # Buat 1 event unik
        event_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        
        payload = {
            "topic": "sensor-data",
            "event_id": event_id,
            "timestamp": now_iso,
            "source": "simulated-publisher",
            "payload": {"temperature": 25.5}
        }
        
        # Simulasi At-Least-Once Delivery (Pengiriman Ganda)
        # Kita sengaja mengirim event yang SAMA sebanyak 2 kali berturut-turut
        print(f"Mengirim event {event_id} (Asli)")
        r1 = httpx.post(AGGREGATOR_URL, json=payload, timeout=5.0)
        print(f"-> Response: {r1.status_code}")
        
        print(f"Mengirim event {event_id} (Duplikat untuk tes Idempotency)")
        r2 = httpx.post(AGGREGATOR_URL, json=payload, timeout=5.0)
        print(f"-> Response: {r2.status_code}")
        print("-" * 40)
        print("Selesai! Publisher berhasil mengirim 1 event asli dan 1 duplikat.")
        
    except Exception as e:
        print(f"Gagal menghubungi aggregator: {e}")

if __name__ == "__main__":
    run_publisher()
