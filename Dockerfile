FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# iputils-ping provides the system `ping` fallback used by ping_engine.py.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        iputils-ping \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY deploy/supervisord.conf /etc/supervisor/supervisord.conf

# Persistent SQLite location (mounted as a volume by docker-compose).
RUN mkdir -p /data

EXPOSE 8501

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
