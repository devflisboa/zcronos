FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/static/uploads/veiculos && chown -R appuser:appuser /app/static/uploads

USER appuser

EXPOSE 5000

CMD ["gunicorn", "-w", "1", "--worker-class", "gthread", "--threads", "4", "-b", "0.0.0.0:5000", "app:create_app('production')"]
