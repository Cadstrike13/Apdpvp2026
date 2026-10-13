#!/bin/sh
set -e

# Le conteneur web applique les migrations et collecte les fichiers statiques ;
# le worker Celery (ROLE=worker) démarre directement.
if [ "${ROLE:-web}" = "web" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
