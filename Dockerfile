FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect admin/static into STATIC_ROOT (WhiteNoise serves them). No DB needed.
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# 3 gunicorn workers; long timeout so a slow AI menu-import (vision model on
# CPU) doesn't get killed mid-request. The prod compose sets the same.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "300"]
