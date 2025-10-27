# --- STAGE 1 : BUILDER (Installation des dépendances) ---
FROM python:3.11-slim AS builder

WORKDIR /tmp/build

# 1. Installation des dépendances de compilation (pour psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Copie et installation des packages Python
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

# --- STAGE 2 : FINAL (Production) ---
FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# 1. Installation des librairies d'exécution (minimales)
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Copie des dépendances Python depuis le stage 'builder'
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 3. Copie du code source (Nouveaux noms de fichiers inclus : data_repository et inventory_service)
COPY app.py .
COPY data_repository.py .
COPY inventory_service.py .
COPY products_loader.py .
COPY style.css .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.folderWatchBlacklist", "."]
