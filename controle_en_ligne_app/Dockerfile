FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt \
    # Chromium et ses dépendances système pour les scans cookies/tiers.
    && playwright install --with-deps chromium

COPY . .

RUN useradd --create-home --uid 1000 controle \
    && mkdir -p /app/db /app/media /app/staticfiles \
    && chown -R controle:controle /app /ms-playwright \
    && chmod +x /app/entrypoint.sh

USER controle

EXPOSE 8003

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "controle_conf.wsgi:application", "--bind", "0.0.0.0:8003", "--workers", "2", "--timeout", "60"]
