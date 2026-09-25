#!/usr/bin/env bash
# ECO Mini CRM - container entrypoint
# 1) waits for PostgreSQL
# 2) applies migrations
# 3) collects static files (served by whitenoise)
# 4) ensures an initial admin account exists
# 5) execs the given command (gunicorn by default)
set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

wait_for_db() {
    echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} ..."

    for attempt in $(seq 1 60); do
        if python -c "import socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0 if s.connect_ex(('${DB_HOST}', ${DB_PORT})) == 0 else 1)"; then
            echo "[entrypoint] PostgreSQL is ready."
            return 0
        fi

        sleep 2
    done

    echo "[entrypoint] ERROR: PostgreSQL did not become available in time." >&2
    return 1
}

if [ -n "${DB_HOST:-}" ]; then
    wait_for_db
fi

echo "[entrypoint] Applying database migrations ..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files ..."
python manage.py collectstatic --noinput >/dev/null

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "[entrypoint] Ensuring admin user '${DJANGO_SUPERUSER_USERNAME}' ..."
    python manage.py ensure_admin \
        --username "${DJANGO_SUPERUSER_USERNAME}" \
        --password "${DJANGO_SUPERUSER_PASSWORD}" \
        --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}"
fi

echo "[entrypoint] Starting: $*"
exec "$@"
