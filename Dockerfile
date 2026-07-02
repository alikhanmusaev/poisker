FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh scheduler_entrypoint.sh \
    && groupadd --system appuser \
    && useradd --system --gid appuser --home /app appuser \
    && chown -R appuser:appuser /app

ENV FLASK_APP=wsgi.py
EXPOSE 8000

USER appuser

ENTRYPOINT ["./entrypoint.sh"]
