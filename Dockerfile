FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm AS wheels
RUN apt-get update && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libmariadb3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home rental
WORKDIR /app
COPY --from=wheels /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels
COPY manage.py .
COPY rental rental
COPY templates templates
COPY vehicle_rental vehicle_rental
COPY --from=frontend /build/dist frontend/dist
RUN DJANGO_SECRET_KEY=static-build-only MYSQL_NAME=build MYSQL_USER=build MYSQL_PASSWORD=build \
    MYSQL_HOST=localhost MYSQL_PORT=3306 python manage.py collectstatic --noinput \
    && mkdir -p /app/media && chown rental:rental /app/media
USER rental
EXPOSE 8000
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=2", "vehicle_rental.wsgi:application"]
