# Резервное копирование Poisker

Инструкция для бэкапа PostgreSQL, MinIO/S3 и связанных Docker volumes перед продакшеном.

## Что бэкапить

| Компонент | Volume / источник | Приоритет |
|-----------|-------------------|-----------|
| PostgreSQL | `postgres_data` | Обязательно, ежедневно |
| Изображения (MinIO) | `minio_data` | Обязательно, ежедневно |
| Typesense | `typesense_data` | Желательно; можно пересобрать через reindex |

## PostgreSQL

### Создать дамп

```bash
docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-board}" \
  -d "${POSTGRES_DB:-chechnya_board}" \
  --format=custom \
  > "poisker-$(date +%Y%m%d-%H%M).dump"
```

Или plain SQL:

```bash
docker compose exec -T postgres pg_dump \
  -U "${POSTGRES_USER:-board}" \
  -d "${POSTGRES_DB:-chechnya_board}" \
  > "poisker-$(date +%Y%m%d-%H%M).sql"
```

### Восстановить

Остановите web/scheduler, восстановите в чистую БД:

```bash
docker compose stop web scheduler

docker compose exec -T postgres pg_restore \
  -U "${POSTGRES_USER:-board}" \
  -d "${POSTGRES_DB:-chechnya_board}" \
  --clean --if-exists \
  < poisker-YYYYMMDD-HHMM.dump
```

Для `.sql` файла:

```bash
docker compose exec -T postgres psql \
  -U "${POSTGRES_USER:-board}" \
  -d "${POSTGRES_DB:-chechnya_board}" \
  < poisker-YYYYMMDD-HHMM.sql
```

После восстановления:

```bash
docker compose up -d web scheduler
```

## MinIO / S3 (изображения)

### Синхронизация bucket на диск

Установите [MinIO Client (`mc`)](https://min.io/docs/minio/linux/reference/minio-mc.html) или используйте `aws s3`:

```bash
mc alias set poisker http://localhost:9000 "$S3_ACCESS_KEY" "$S3_SECRET_KEY"
mc mirror poisker/board-images ./backups/board-images-$(date +%Y%m%d)
```

Через AWS CLI (S3-compatible):

```bash
aws --endpoint-url http://localhost:9000 s3 sync s3://board-images ./backups/board-images-$(date +%Y%m%d)
```

### Восстановление bucket

```bash
mc mirror ./backups/board-images-YYYYMMDD poisker/board-images
```

## Docker volumes напрямую

Альтернатива — архивировать volume (сервис должен быть остановлен):

```bash
docker compose stop postgres minio typesense

docker run --rm \
  -v poisker_postgres_data:/data \
  -v "$(pwd)/backups":/backup \
  alpine tar czf /backup/postgres_data-$(date +%Y%m%d).tar.gz -C /data .

docker run --rm \
  -v poisker_minio_data:/data \
  -v "$(pwd)/backups":/backup \
  alpine tar czf /backup/minio_data-$(date +%Y%m%d).tar.gz -C /data .

docker compose up -d
```

Имена volumes могут отличаться — проверьте: `docker volume ls | grep poisker`.

## Typesense

Индекс можно пересобрать без бэкапа:

```bash
docker compose exec web flask reindex
```

Если команда `reindex` недоступна, используйте `python manage.py reindex` или восстановите volume `typesense_data`.

## Рекомендуемый график

- **База данных** — каждый день (ночью), хранить минимум 14 копий
- **Изображения** — каждый день, хранить минимум 7–14 копий
- **Typesense** — по желанию; достаточно reindex после восстановления PostgreSQL

Храните бэкапы на отдельном сервере или в object storage (не на том же диске, что и продакшен).

## Проверка бэкапа

Периодически разворачивайте дамп на тестовом стенде и проверяйте:

- количество объявлений в БД;
- доступность изображений по URL;
- работу поиска после reindex.
