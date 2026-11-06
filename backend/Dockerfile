FROM python:3.12-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y libreoffice-calc fonts-liberation fonts-crosextra-carlito \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data/fotos \
    && chown -R app:app /data
WORKDIR /srv
COPY . .
RUN python -m pip install --no-cache-dir pip==26.2.0 \
    && pip install --no-cache-dir '.[dev]' \
    && chown -R app:app /srv
USER app

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
