FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc fonts-dejavu-core gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh scheduler_entrypoint.sh \
    && groupadd --system appuser \
    && useradd --system --gid appuser --home /app appuser \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R appuser:appuser /app

ENV DJANGO_SETTINGS_MODULE=config.settings
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
