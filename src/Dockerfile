FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# libpq-dev/gcc no deberían hacer falta con psycopg[binary], pero se dejan
# por si en tu máquina termina compilando algo (ej. arquitectura ARM).
# postgresql-client: pg_dump/psql/pg_restore, para migraciones y respaldos
# contra el Postgres propio.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
