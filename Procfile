release: python manage.py migrate --no-input
web: gunicorn config.wsgi:application --log-file -
