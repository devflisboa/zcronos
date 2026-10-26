#!/bin/sh
set -e
alembic upgrade head
exec gunicorn -w 1 --worker-class gthread --threads 4 -b 0.0.0.0:5000 "app:create_app('production')"
