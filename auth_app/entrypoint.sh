#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn auth_conf.wsgi:application --bind 0.0.0.0:8000 --workers 3
