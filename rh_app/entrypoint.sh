#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn rh_conf.wsgi:application --bind 0.0.0.0:8001 --workers 3
