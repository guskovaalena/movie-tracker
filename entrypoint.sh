#!/bin/sh
set -e

if [ "$1" = "dev" ]; then
    shift
    exec "$@"
fi

while ! nc -z db 5432; do
  sleep 0.5
done

export FLASK_APP=run.py

if [ ! -d "migrations" ]; then
    flask db init
fi

flask db migrate -m "auto migration" 2>/dev/null || echo "No new migrations"

flask db upgrade

exec "$@"