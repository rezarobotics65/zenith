# Career Tracker & Portfolio

A personal career management system for Reza Yousefi: a public portfolio at `/`
and a private, staff-only tracker under `/tracker/`. Built per `BUILD_BRIEF.md`
— read that file for the full specification and `CLAUDE.md` for the working
conventions.

## Stack

Python 3.10+, Django 5.2, PostgreSQL (psycopg 3), server-rendered Django
templates, hand-written CSS, vanilla JS, Chart.js from a CDN. No frontend
framework, no build step, no DRF. All content is edited through Django admin.

## Local setup

```bash
python -m venv venv
venv/Scripts/activate            # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

cp .env.example .env             # then fill in SECRET_KEY, DB credentials
docker compose up -d             # starts local PostgreSQL on :5432

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_roadmap    # skills, certs, courses, KPIs, monthly plans
python manage.py seed_portfolio  # profile, experience, education, languages

python manage.py runserver
```

Then:

- Public portfolio: <http://127.0.0.1:8000/>
- Admin (content editing): <http://127.0.0.1:8000/admin/>
- Private tracker (staff only): <http://127.0.0.1:8000/tracker/>

Both seed commands are idempotent (`update_or_create` on natural keys) and
accept `--flush` to clear their app's data first:

```bash
python manage.py seed_roadmap --flush
python manage.py seed_portfolio --flush
```

## Tests

```bash
pytest
```

Requires a running PostgreSQL (`docker compose up -d`) since pytest-django
creates a real test database from `DATABASES` in settings. Access-control
tests are non-negotiable — see Section 11 of `BUILD_BRIEF.md`.

## Deployment

- `config/settings/production.py` turns on `DEBUG=False`, HTTPS redirects,
  secure cookies and HSTS — all driven by environment variables, never
  hardcoded secrets.
- Static files are served by WhiteNoise
  (`whitenoise.storage.CompressedManifestStaticFilesStorage`); run
  `python manage.py collectstatic` as part of your deploy/release step.
- `Procfile` defines a `release` step (`migrate`) and a `web` process
  (`gunicorn config.wsgi:application`) for Heroku-style platforms.
- Set `DJANGO_SETTINGS_MODULE=config.settings.production` and provide
  `SECRET_KEY`, `ALLOWED_HOSTS`, and `DB_*` via environment variables — see
  `.env.example`.
- For a step-by-step EC2 + RDS deployment with GitHub Actions CI/CD, see
  [DEPLOYMENT.md](DEPLOYMENT.md). Server-side config lives in `deploy/`
  (systemd unit, nginx config, deploy script); the workflow itself is
  `.github/workflows/deploy.yml`.

## Decisions made while building (Section 14 of BUILD_BRIEF.md)

The brief left five open questions for the author; these defaults were
applied so the build could proceed without blocking:

1. **Languages** — English and Arabic seeded as `PROFESSIONAL` per the brief;
   Persian added as `NATIVE` and Malay as `CONVERSATIONAL` (12+ years based
   in Malaysia). Adjust in admin if wrong.
2. **Visitor analytics** — omitted. Nothing in the brief's page specs asked
   for it, and it adds a model + middleware for a "nice to have."
3. **CV download** — a static uploaded file via `Profile.cv_file`, not
   generated from portfolio data. Upload a PDF at `/admin/portfolio/profile/`.
4. **Monthly review notifications** — omitted; the dashboard is the review
   surface, as the brief's own default assumption suggested.
5. **Salary visibility** — never public, exactly as specified. `CareerObjective`
   salary fields are only ever rendered in `tracker/templates/tracker/dashboard.html`,
   which sits behind `staff_member_required`.

One more worth flagging: `portfolio/views.py` imports from `tracker` in two
places — reading `SkillDomain`/`Certification` to render the portfolio's
Skills and Certifications sections, and (as of the Visitor Log feature)
writing a `CVDownloadLog` row plus calling `tracker.geoip`/
`tracker.middleware` helpers from `download_cv()`. These are the deliberate
exceptions to "portfolio must never import from tracker" (Section 4) — no
portfolio *model* depends on tracker, and tracker never imports portfolio.
`tracker.middleware.VisitorTrackingMiddleware` logs portfolio pageviews the
same way, but from settings.py, not from a portfolio import — middleware
sits above both apps rather than one importing the other.

`tracker/management/commands/seed_roadmap.py`'s ~45 monthly commitments
(Section 10.7) are synthesised from the KPIs, courses and certifications the
brief specifies for each month — the "Section 6 of the roadmap document" it
points to as the source wasn't supplied alongside the brief. Edit the wording
freely in `/admin/tracker/monthlyplan/`.
