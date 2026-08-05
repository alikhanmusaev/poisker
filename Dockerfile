FROM python:3.12-slim

WORKDIR /app

COPY certificates/russian_trusted_root_ca.cer /usr/local/share/ca-certificates/russian_trusted_root_ca.crt
COPY certificates/russian_trusted_sub_ca.cer /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libpq-dev gcc fonts-dejavu-core gosu \
    && update-ca-certificates \
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
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
