# CLAUDE.md

Project context for AI coding assistants. Read `BUILD_BRIEF.md` for the full specification.

## What this is

A personal career tracker and public portfolio for Reza Yousefi, tracking progress towards the role of AI Solutions Delivery Manager. Two faces: a public portfolio at `/`, and a private tracker under `/tracker/` for courses, KPIs and activity logging.

## Stack — do not change these

- Python 3.12+, Django 5.x, PostgreSQL (psycopg 3)
- Django templates, server-rendered HTML only
- Hand-written CSS in `static/css/`, using CSS custom properties
- Vanilla JavaScript only, and only for charts
- Chart.js 4.x from cdnjs — the single permitted external dependency in the browser

**Never introduce:** React, Vue, HTMX, Alpine, npm, Node, any build step, Tailwind, Bootstrap, or Django REST Framework. If a task seems to need one of these, the task is wrong — stop and ask.

## Editing model

All content is created and edited through **Django admin**. Do not build custom create, update or delete forms. The portfolio and tracker pages are read-only views. Invest effort in admin configuration (`list_editable`, inlines, autocomplete) rather than custom forms.

## Access control — the rule that matters most

| Path | Access |
| :---- | :---- |
| `/`, `/case-study/<slug>/` | Public |
| `/tracker/*` | `@staff_member_required` — not `login_required` |
| `/admin/*` | Django admin |

The public portfolio must contain **no links to and no evidence of** the tracker or admin. A recruiter should not know the tracker exists. Salary figures never appear in a public template.

Any change touching URLs, views or templates must keep the access-control tests passing.

## Conventions

- Business logic and all progress calculations live in `tracker/services.py` — never in views, never in templates.
- Choice fields use `models.TextChoices`.
- Every model has `created_at`, `updated_at`, `__str__` and `Meta.ordering`.
- Pass data to charts with `{{ data|json_script:"id" }}` and parse it in JS. Never build JS objects inside template tags.
- Every chart has a plain-table fallback for when JavaScript is unavailable.
- Pillar weights come from the `Pillar.weight` database field. Never hardcode them.
- The timetable must render any date range present in the data, not a fixed one.

## Commands

python manage.py migrate

python manage.py seed_roadmap        # skills, certs, courses, KPIs, monthly plans

python manage.py seed_portfolio      # profile, experience, education, languages

python manage.py seed_roadmap --flush

pytest

Both seed commands are idempotent — they use `update_or_create` on natural keys. Running them twice must never duplicate data.

## Design

Navy `#15355E`, teal accent `#1F7A6C`, off-white `#FBFAF8`. System font stack. Flat surfaces, 1px hairlines, no shadows or gradients. Dark mode via `prefers-color-scheme`. Mobile-first, WCAG AA.

"AI Inside" is a restrained signal, not decoration — exactly five touches, listed in Section 8 of the brief. Do not add more.

## Before marking work complete

Run `pytest`. Access-control tests are non-negotiable — if they fail, the feature is not done.
