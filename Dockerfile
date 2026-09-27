# On épingle explicitement "bookworm" (Debian 12) : les noms de paquets
# système ci-dessous (libgdk-pixbuf2.0-0, etc.) correspondent à cette version.
# Sur "trixie" (Debian 13, devenu la base par défaut de "python:3.12-slim"
# depuis fin 2025), certains paquets ont été renommés et cassent le build.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=kobostat.settings

# Dépendances système nécessaires à WeasyPrint (export PDF) et pyreadstat (.sav)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 libharfbuzz-subset0 \
    shared-mime-info fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static staticfiles

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_users && python manage.py collectstatic --noinput && gunicorn kobostat.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --threads 4 --worker-class gthread --preload --max-requests 300 --max-requests-jitter 50 --timeout 120"]
