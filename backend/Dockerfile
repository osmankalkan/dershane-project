FROM python:3.12-slim

WORKDIR /app

# Sistem bağımlılıklarını kur (psycopg2 ve derleme için gerekli olanlar)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Uploads dizinini oluştur
RUN mkdir -p uploads/raw

# FastAPI portu
EXPOSE 8000

# Uygulamayı başlat
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
