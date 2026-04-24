FROM python:3.11-slim

WORKDIR /app

# Membuat non-root user demi keamanan (best practice)
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app

# Switch ke user tersebut
USER appuser

# Install dependencies terlebih dahulu agar masuk ke layer cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code ke dalam container
COPY src/ ./src/

# Buka port 8080
EXPOSE 8080

# Jalankan server
CMD ["python", "-m", "src.main"]
