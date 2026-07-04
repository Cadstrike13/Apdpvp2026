FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# jpeg/zlib/libffi : libs runtime nécessaires à Pillow (conservées) ;
# le reste n'est utile qu'à la compilation et est retiré après pip install.
RUN apk add --no-cache jpeg zlib libffi \
    && apk add --no-cache --virtual .build-deps gcc musl-dev jpeg-dev zlib-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn \
    && apk del .build-deps

COPY . .

RUN mkdir -p /app/db /app/media /app/staticfiles \
    && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
