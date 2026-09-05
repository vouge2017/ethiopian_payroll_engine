FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

FROM python:3.11-slim AS runtime

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser && \
    apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .
RUN mkdir -p /app/uploads && chown -R appuser:appgroup /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_APP=wsgi:app \
    GUNICORN_TMPDIR=/tmp/gunicorn \
    WORKER_TMP_DIR=/tmp/gunicorn-workers

# Create the gunicorn tmp dirs owned by appuser BEFORE gunicorn starts.
# Gunicorn's default fallback for the control socket is /nonexistent,
# which triggers "Permission denied: '/nonexistent'" at boot when running
# as a non-root user (appuser). Pre-creating the dirs silences the noise.
USER root
RUN mkdir -p /tmp/gunicorn /tmp/gunicorn-workers && \
    chown -R appuser:appgroup /tmp/gunicorn /tmp/gunicorn-workers && \
    chmod 700 /tmp/gunicorn /tmp/gunicorn-workers
USER appuser

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-5000}/healthz')" || exit 1

CMD ["sh", "-c", "echo '[startup] Running database migrations...' && flask db upgrade 2>&1 | tail -20; status=${PIPESTATUS[0]}; if [ $status -ne 0 ]; then echo '[startup] FATAL: migrations failed with exit code $status'; exit $status; fi; echo '[startup] Migrations OK, starting gunicorn...'; exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --timeout 120 --worker-tmp-dir /tmp/gunicorn-workers --tmp-dir /tmp/gunicorn wsgi:app"]
