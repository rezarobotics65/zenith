# Deployment runbook — EC2 (Amazon Linux 2023) + RDS (PostgreSQL 18.1)

Everything below assumes: an EC2 instance already running Amazon Linux 2023,
an RDS PostgreSQL 18.1 instance already created, and you can SSH into the
EC2 instance with your `.pem` key. Serving over plain HTTP on the instance's
public IP for now — see Part 6 for adding a domain + HTTPS later.

Config files this refers to live in `deploy/` and `.github/workflows/deploy.yml`.

---

## Part 1 — One-time server setup

SSH in first:

```bash
ssh -i /path/to/your-key.pem ec2-user@<EC2_PUBLIC_IP>
```

**1. System packages**

```bash
sudo dnf update -y
sudo dnf install -y git python3.12 python3.12-devel python3.12-pip gcc nginx
```

Amazon Linux 2023's default `python3` is 3.9.25 — too old for Django 5.2 (requires
3.10+). Install `python3.12` explicitly as above (AL2023's repos ship it as a
separate package); use it by name in the next step rather than the bare `python3`.

**2. Clone the repo**

```bash
git clone https://github.com/rezarobotics65/zenith.git /home/ec2-user/zenith
cd /home/ec2-user/zenith
```

**3. Virtual environment + dependencies**

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**4. Production `.env`**

```bash
nano /home/ec2-user/zenith/.env
```

Paste, filling in the real values (RDS details are in the AWS Console under
RDS → Databases → your instance → "Connectivity & security"):

```
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<generate one — see below>
DEBUG=False
ALLOWED_HOSTS=<EC2_PUBLIC_IP>

DB_NAME=<your RDS database name>
DB_USER=<your RDS master username>
DB_PASSWORD=<your RDS master password>
DB_HOST=<your RDS endpoint, e.g. zenith-db.xxxxx.ap-southeast-1.rds.amazonaws.com>
DB_PORT=5432

# No domain/HTTPS yet — these MUST be False or the site will redirect-loop
# / drop cookies over plain HTTP. Flip to True once HTTPS is set up (Part 6).
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

Generate a real `SECRET_KEY` (don't reuse the one from local dev):

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**5. RDS network access**

In the AWS Console, open the RDS instance's security group and add an
inbound rule: **Type** PostgreSQL, **Port** 5432, **Source** = the EC2
instance's security group (not `0.0.0.0/0` — RDS should never be open to the
internet). I can't do this step for you — it needs the AWS Console.

**6. Migrate, seed, collect static, create an admin user**

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py seed_roadmap
python manage.py seed_portfolio
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

**7. Smoke-test Gunicorn directly** (before wiring up systemd/nginx)

```bash
venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000
# Ctrl+C once you see it start with no errors
```

**8. systemd service (keeps it running, restarts on crash/reboot)**

```bash
sudo cp deploy/zenith.service /etc/systemd/system/zenith.service
sudo systemctl daemon-reload
sudo systemctl enable --now zenith
sudo systemctl status zenith   # should say "active (running)"
```

**9. nginx (reverse proxy + serves static/media directly)**

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/zenith.conf
sudo nginx -t                  # test config syntax
sudo systemctl enable --now nginx
```

**10. Security group for the instance itself**

In the AWS Console, on the EC2 instance's security group, add an inbound
rule: **Type** HTTP, **Port** 80, **Source** 0.0.0.0/0 (and `::/0` for IPv6
if you want it). Again, Console-only — I can't do this myself.

**11. Visit it**

```
http://<EC2_PUBLIC_IP>/
```

You should see the portfolio. `http://<EC2_PUBLIC_IP>/admin/` should show
the Django admin login.

> **Elastic IP recommended:** a plain EC2 public IP changes if the instance
> ever stops/starts. Allocate an Elastic IP and associate it with the
> instance so `ALLOWED_HOSTS` (and your CI/CD secrets) don't silently break
> later. Console → EC2 → Elastic IPs → Allocate → Associate.

---

## Part 2 — CI/CD: auto-deploy on push to `main`

This repo already has `.github/workflows/deploy.yml` — it SSHes into the
server and runs `deploy/deploy.sh` (pull, install deps, migrate,
collectstatic, restart) on every push to `main`.

**1. Generate a dedicated deploy key** (on your own machine, not the server —
never reuse your personal `.pem` for CI):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f gh_deploy_key -N ""
```

This creates `gh_deploy_key` (private) and `gh_deploy_key.pub` (public) in
your current directory.

**2. Authorize the public key on the server** — SSH in with your `.pem` as
usual, then:

```bash
echo "<paste contents of gh_deploy_key.pub>" >> ~/.ssh/authorized_keys
```

**3. Let the deploy user restart the service without a password** — the
deploy script calls `sudo systemctl restart zenith`, scoped to just that:

```bash
echo "ec2-user ALL=(root) NOPASSWD: /usr/bin/systemctl restart zenith" | sudo tee /etc/sudoers.d/zenith-deploy
sudo chmod 440 /etc/sudoers.d/zenith-deploy
```

**4. Make `deploy.sh` executable**

```bash
chmod +x /home/ec2-user/zenith/deploy/deploy.sh
```

**5. Add GitHub repo secrets** — on GitHub: your repo → Settings → Secrets
and variables → Actions → New repository secret. Add three:

| Secret name | Value |
| :---- | :---- |
| `EC2_HOST` | the EC2 public IP (or Elastic IP) |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | the full contents of `gh_deploy_key` (the **private** key, not `.pub`) |

**6. Test it** — push any small change to `main`, then check the Actions
tab on GitHub for the "Deploy to EC2" run. On the server you can also watch
it happen live:

```bash
journalctl -u zenith -f
```

From then on, every push to `main` auto-deploys.

---

## Part 3 — Day-to-day operations

```bash
# Tail app logs
journalctl -u zenith -f

# Restart manually
sudo systemctl restart zenith

# Check nginx errors
sudo tail -f /var/log/nginx/error.log

# Redeploy manually without waiting for CI
cd /home/ec2-user/zenith && bash deploy/deploy.sh
```

---

## Part 4 (later) — Domain + HTTPS

Once a domain's DNS A record points at the instance's (Elastic) IP:

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Certbot rewrites `/etc/nginx/conf.d/zenith.conf` to add the HTTPS server
block and cert paths automatically. Then update `.env`:

```
ALLOWED_HOSTS=yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

and `sudo systemctl restart zenith`.
