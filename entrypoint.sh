#!/bin/sh
set -e
alembic upgrade head
python -c "from rembg import new_session; new_session('u2net')" 2>/dev/null || true
exec gunicorn -w 1 --worker-class gthread --threads 4 -b 0.0.0.0:5000 "app:create_app('production')"
