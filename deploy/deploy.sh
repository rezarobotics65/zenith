#!/bin/bash
# Runs on the EC2 instance — first manually during setup, then automatically
# by .github/workflows/deploy.yml on every push to main. Assumes the repo is
# already cloned to $APP_DIR and venv already exists (see DEPLOYMENT.md).
set -euo pipefail

APP_DIR="/home/ec2-user/zenith"
cd "$APP_DIR"

echo "==> Pulling latest code"
git pull origin main

echo "==> Installing dependencies"
source venv/bin/activate
pip install -r requirements.txt --quiet

export DJANGO_SETTINGS_MODULE=config.settings.production

echo "==> Running migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Restarting app"
sudo systemctl restart zenith

echo "==> Deploy complete: $(git rev-parse --short HEAD)"
