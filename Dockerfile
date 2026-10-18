FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data
# Proxies whose X-Forwarded-* headers uvicorn believes: loopback and private/Docker networks
# (Traefik, the Docker gateway in front of `tailscale serve`), not tailnet clients (100.64.0.0/10).
ENV FORWARDED_ALLOW_IPS="127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN useradd --uid 1000 --create-home appuser && mkdir -p /data && chown appuser:appuser /data
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

# --proxy-headers so request.url.scheme is https behind a proxy (secure cookies); trusted proxies
# come from FORWARDED_ALLOW_IPS above.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
