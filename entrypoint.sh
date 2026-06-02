#!/bin/sh
set -e

if [ "$1" = "dev" ]; then
    shift
    echo "Development mode - skipping migrations"
    exec "$@"
fi

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "PostgreSQL started"

export FLASK_APP=run.py

if [ ! -d "migrations" ]; then
    echo "Initializing migrations folder..."
    flask db init
    echo "Creating initial migration..."
    flask db migrate -m "Initial migration"
fi

echo "Applying migrations..."
flask db upgrade

exec "$@"