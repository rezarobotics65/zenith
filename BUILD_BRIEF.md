# BUILD BRIEF — Career Tracker & Portfolio Web App

> **How to use this file.** Drop it into an empty folder, open that folder in VS Code, and give this file to Claude Code (or Codex) with the instruction: *"Build this application exactly as specified. Work through the milestones in Section 12 in order. Ask me before deviating from the stack constraints in Section 2."*

---

## 1. What this application is

A personal career management system for **Reza Yousefi**, tracking progress from Technical Project & Business Development Manager towards **AI Solutions Delivery Manager**.

It has two distinct faces:

| Face | Audience | Access |
| :---- | :---- | :---- |
| **Portfolio** | Recruiters, hiring managers, the public | Open, no login |
| **Career tracker** | Reza only | Login required, staff-only |

The portfolio must look like a polished professional website. The tracker is a private working tool.

### The three pages requested

1. **Portfolio** (`/`) — public. Introduction, skills, experience, languages, case studies.
2. **KPI & Timetable** (`/tracker/kpi/`) — private. Courses, certifications, monthly plans, KPI status.
3. **Dashboard** (`/tracker/`) — private. Career objective progress at a glance.

Plus a fourth, needed to satisfy "log all my activity":

4. **Activity Log** (`/tracker/activity/`) — private. Every study session, exam, conversation and milestone.

---

## 2. Stack constraints — do not deviate

These were chosen deliberately. Do not "improve" them.

**Use:**

- Python 3.12+
- Django 5.x
- PostgreSQL (psycopg 3)
- Django templates — server-rendered HTML only
- Plain CSS in a single stylesheet, hand-written
- Vanilla JavaScript, only where genuinely needed (charts, small toggles)
- Chart.js via CDN for charts
- `python-decouple` or `django-environ` for settings
- Pillow for image uploads

**Do NOT use:**

- React, Vue, Svelte, or any JS framework
- HTMX, Alpine.js, or similar
- npm, Node, Webpack, Vite, or any build step
- Tailwind, Bootstrap, or any CSS framework
- Django REST Framework — there is no API requirement
- Any CSS-in-JS or preprocessor

**Editing model:** All content is created and edited through **Django admin**. Do not build custom create/update forms or in-page editing. The public site and tracker pages are read-only views of the data. This is a deliberate decision to keep the build small.

---

## 3. Access control model

This is a hard requirement. Get it right before building anything else.

| URL pattern | Access |
| :---- | :---- |
| `/` | Public |
| `/case-study/<slug>/` | Public |
| `/tracker/*` | `@staff_member_required` |
| `/admin/*` | Django admin, superuser/staff |
| `/accounts/login/` | Public (the login form itself) |

### Rules

- Every view under `/tracker/` uses `django.contrib.admin.views.decorators.staff_member_required`. Do not use plain `login_required` — staff-only is the requirement.
- Unauthenticated users hitting `/tracker/*` redirect to `/accounts/login/?next=...`.
- The public portfolio must contain **no links** to the tracker or admin. A recruiter should see no evidence the tracker exists.
- Add a small, unobtrusive login link in the site footer only (or omit entirely and navigate to `/admin/` directly — your preference; default to omitting).
- `Profile.is_published` and `CaseStudy.is_published` flags control what appears publicly. Unpublished records are invisible to anonymous users.
- Use `django-axes` or Django's built-in throttling if deploying publicly. For local development, skip.

### Settings hardening

DEBUG = False in production

ALLOWED_HOSTS from env

SECRET_KEY from env, never committed

SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE = True in production

X_FRAME_OPTIONS = 'DENY'

---

## 4. Project structure

careertracker/

├── manage.py

├── requirements.txt

├── .env.example

├── .gitignore

├── config/

│   ├── settings/

│   │   ├── base.py

│   │   ├── local.py

│   │   └── production.py

│   ├── urls.py

│   └── wsgi.py

├── portfolio/                  # public-facing app

│   ├── models.py               # Profile, Language, Experience, Achievement,

│   │                           # Education, CaseStudy

│   ├── admin.py

│   ├── views.py

│   ├── urls.py

│   └── templates/portfolio/

├── tracker/                    # private app

│   ├── models.py               # SkillDomain, Skill, Certification, Course,

│   │                           # Pillar, KPI, MonthlyPlan, MonthlyCommitment,

│   │                           # ActivityLog, CareerObjective

│   ├── admin.py

│   ├── views.py

│   ├── urls.py

│   ├── services.py             # all progress calculations live here

│   ├── management/commands/

│   │   └── seed_roadmap.py

│   └── templates/tracker/

├── static/

│   ├── css/main.css

│   ├── css/portfolio.css

│   ├── js/charts.js

│   └── img/

├── templates/

│   ├── base.html

│   ├── base_public.html

│   └── registration/login.html

└── media/                      # uploaded images

Keep `portfolio` and `tracker` as separate apps. The portfolio must never import from the tracker.

---

## 5. Data model

Use `models.TextChoices` for all choice fields. Every model gets `created_at` and `updated_at` (`auto_now_add` / `auto_now`) and a sensible `__str__` and `Meta.ordering`.

### 5.1 Portfolio app

**Profile** — singleton (enforce `pk=1` in `save()`)

full_name            CharField(120)

headline             CharField(160)      # "AI Solutions Delivery Manager"

tagline              CharField(240)      # one-line positioning statement

introduction         TextField           # 2-3 paragraph intro

location             CharField(120)

email                EmailField

phone                CharField(40)

linkedin_url         URLField(blank)

github_url           URLField(blank)

photo                ImageField(upload_to='profile/', blank)

cv_file              FileField(upload_to='cv/', blank)

years_experience     PositiveIntegerField

open_to_work         BooleanField(default=True)

is_published         BooleanField(default=True)

**Language**

name                 CharField(60)       # English, Arabic, Malay, Persian

proficiency          CharField choices: NATIVE, FLUENT, PROFESSIONAL, CONVERSATIONAL, BASIC

notes                CharField(160, blank)

order                PositiveIntegerField(default=0)

**Experience**

company              CharField(160)

title                CharField(160)

location             CharField(120)

start_date           DateField

end_date             DateField(null, blank)     # null = current

is_current           BooleanField(default=False)

summary              TextField(blank)

is_published         BooleanField(default=True)

order                PositiveIntegerField(default=0)

Property `duration_display` returns e.g. "Nov 2025 – Present".

**Achievement** — bullet points under an Experience

experience           FK(Experience, related_name='achievements', on_delete=CASCADE)

text                 TextField

metric_value         CharField(40, blank)   # "60%", "RM 1.2M", "600+"

metric_label         CharField(80, blank)   # "incident reduction"

is_headline          BooleanField(default=False)   # surface on portfolio hero

order                PositiveIntegerField(default=0)

**Education**

institution          CharField(160)

qualification        CharField(160)

field_of_study       CharField(160, blank)

location             CharField(120, blank)

year_completed       PositiveIntegerField

order                PositiveIntegerField(default=0)

**CaseStudy** — STAR-format evidence, doubles as portfolio content

title                CharField(200)

slug                 SlugField(unique)

situation            TextField

task                 TextField

action               TextField

result               TextField

headline_metric      CharField(80, blank)    # "60% fewer incidents"

related_experience   FK(Experience, null, blank, on_delete=SET_NULL)

date_completed       DateField(null, blank)

is_published         BooleanField(default=False)

order                PositiveIntegerField(default=0)

### 5.2 Tracker app

**CareerObjective** — singleton

current_title        CharField(160)

target_title         CharField(160)

current_salary       DecimalField(10,2)

target_salary        DecimalField(10,2)

currency             CharField(8, default='RM')

start_date           DateField

target_date          DateField

notes                TextField(blank)

**SkillDomain**

code                 CharField(2, unique)     # A-F

name                 CharField(120)

description          TextField(blank)

priority             CharField choices: HIGHEST, HIGH, MEDIUM, LOW

order                PositiveIntegerField

Properties: `avg_current_level`, `avg_target_level`, `progress_pct` (`progress_pct` = how far current has closed the gap to target, floor 0, cap 100)

**Skill**

domain               FK(SkillDomain, related_name='skills', on_delete=CASCADE)

name                 CharField(200)

current_level        PositiveSmallIntegerField   # 1-5, validators 1..5

target_level         PositiveSmallIntegerField   # 1-5

baseline_level       PositiveSmallIntegerField   # level at plan start, for progress

why_it_matters       TextField(blank)

order                PositiveIntegerField

Property `gap` returns "NONE" / "MODERATE" / "LARGE" / "CRITICAL" computed from `target_level - current_level` (0 → NONE, 1 → MODERATE, 2 → LARGE, 3+ → CRITICAL).

**Certification**

name                 CharField(200)

provider             CharField(120)

status               CharField choices: PLANNED, STUDYING, BOOKED, EARNED, DEFERRED, ABANDONED

priority             PositiveSmallIntegerField

planned_hours        PositiveIntegerField(default=0)

cost_amount          DecimalField(8,2, null, blank)

cost_currency        CharField(8, default='USD')

target_date          DateField(null, blank)

earned_date          DateField(null, blank)

credential_id        CharField(120, blank)

credential_url       URLField(blank)

domains              M2M(SkillDomain, blank)

notes                TextField(blank)

show_on_portfolio    BooleanField(default=True)

order                PositiveIntegerField

**Course**

name                 CharField(200)

provider             CharField(120)

tier                 CharField choices: CERTIFICATION, TECHNICAL, LEADERSHIP

status               CharField choices: NOT_STARTED, IN_PROGRESS, COMPLETE, DROPPED

domain               FK(SkillDomain, null, blank, on_delete=SET_NULL)

certification        FK(Certification, null, blank, on_delete=SET_NULL, related_name='courses')

planned_hours        PositiveIntegerField(default=0)

url                  URLField(blank)

is_free              BooleanField(default=True)   # covered by Coursera Plus / LinkedIn Learning

start_month          DateField(null, blank)       # use the 1st of the month

target_month         DateField(null, blank)

completed_date       DateField(null, blank)

application_commitment  TextField(blank)          # the "use it at work" pairing

application_done     BooleanField(default=False)

notes                TextField(blank)

order                PositiveIntegerField

Property `hours_logged` — sum of related `ActivityLog.hours`. Property `progress_pct` — `hours_logged / planned_hours`, capped at 100. If status is COMPLETE, return 100.

**Pillar**

code                 CharField(1, unique)    # A, B, C, D

name                 CharField(120)

description          TextField(blank)

weight               PositiveSmallIntegerField   # percent, must total 100

order                PositiveIntegerField

**KPI**

pillar               FK(Pillar, related_name='kpis', on_delete=PROTECT)

code                 CharField(10)           # A1, B3, C2...

title                CharField(300)

target               CharField(200)

verified_by          CharField(200, blank)

period               CharField choices: YEARLY, MONTHLY

period_year          PositiveIntegerField

period_month         PositiveSmallIntegerField(null, blank)   # 1-12, monthly only

status               CharField choices: NOT_STARTED, ON_TRACK, AT_RISK, BEHIND, COMPLETE

target_value         DecimalField(10,2, null, blank)

current_value        DecimalField(10,2, null, blank)

due_date             DateField(null, blank)

notes               TextField(blank)

order                PositiveIntegerField

Property `rag` returns GREEN / AMBER / RED for the dashboard. Property `progress_pct` — if both target_value and current_value set, compute; else derive from status.

**MonthlyPlan**

year                 PositiveIntegerField

month                PositiveSmallIntegerField    # 1-12

theme                CharField(200)               # "Foundations", "First certification"

target_hours         PositiveIntegerField

status               CharField choices: PLANNED, ACTIVE, COMPLETE, SLIPPED

review_notes         TextField(blank)

reviewed_on          DateField(null, blank)

unique_together      (year, month)

Property `actual_hours` — sum of `ActivityLog.hours` in that month. Property `hours_variance_pct`.

**MonthlyCommitment**

plan                 FK(MonthlyPlan, related_name='commitments', on_delete=CASCADE)

pillar               FK(Pillar, on_delete=PROTECT)

commitment           TextField

done_when            CharField(300)

is_complete          BooleanField(default=False)

completed_date       DateField(null, blank)

order                PositiveIntegerField

**ActivityLog** — the universal log

date                 DateField(default=today, db_index=True)

activity_type        CharField choices: STUDY, EXAM, APPLICATION, PRACTICE,

                                        WORK_APPLICATION, NETWORKING, CONTENT,

                                        INTERVIEW, REVIEW, MILESTONE, OTHER

title                CharField(240)

description          TextField(blank)

hours                DecimalField(5,2, default=0)

course                FK(Course, null, blank, on_delete=SET_NULL, related_name='activities')

certification        FK(Certification, null, blank, on_delete=SET_NULL, related_name='activities')

kpi                  FK(KPI, null, blank, on_delete=SET_NULL, related_name='activities')

skill_domain         FK(SkillDomain, null, blank, on_delete=SET_NULL)

is_milestone         BooleanField(default=False)

`Meta.ordering = ['-date', '-created_at']`

---

## 6. Pages and views

All tracker views are **function-based or `TemplateView`** — keep it simple. Put every calculation in `tracker/services.py`, not in templates or views.

### 6.1 Portfolio — `/` (public)

Single long-scroll page with anchor navigation. Sections in order:

1. **Hero** — name, headline, tagline, location, "Open to opportunities" badge, photo, primary CTA (download CV), secondary CTA (LinkedIn).
2. **AI Inside band** — see Section 8. A visual strip immediately below the hero that makes the AI specialisation unmissable: 3–4 headline metrics pulled from `Achievement.is_headline=True` (e.g. "600+ AI-managed intersections", "60% incident reduction", "RM 1.2M closed", "12+ years").
3. **Introduction** — `Profile.introduction`.
4. **Skills** — grouped by `SkillDomain`. Render each skill as a labelled bar showing `current_level` out of 5. Domains ordered by `order`. Include a compact domain summary chart (Chart.js radar).
5. **Certifications** — cards for `Certification` where `show_on_portfolio=True`. Earned ones show a badge and credential link; in-progress ones show status honestly (this is a strength, not a weakness — it signals active development).
6. **Experience** — vertical timeline. Company, title, dates, summary, achievement bullets. Highlight `metric_value` visually.
7. **Case studies** — cards for published `CaseStudy`, linking to detail pages.
8. **Education**
9. **Languages** — `Language` list with proficiency shown as a labelled level, not a percentage bar (percentages for language fluency are meaningless and recruiters dislike them).
10. **Contact** — email, phone, LinkedIn. No contact form (avoids spam and CSRF surface).

**Case study detail** — `/case-study/<slug>/` renders the STAR sections with the headline metric prominent.

### 6.2 Dashboard — `/tracker/` (private)

Answers one question: *am I on track for AI Solutions Delivery Manager?*

- **Objective header** — current title → target title, current salary → target salary, days remaining to `target_date`, overall progress percentage.
- **Metric row (4 cards)** — certifications earned / total; hours logged / hours planned to date; KPIs complete / total; current month RAG status.
- **Certification tracker** — horizontal progress per certification with target date and status pill.
- **Skill domain radar** — Chart.js radar, current vs target across the six domains.
- **Pillar health** — for each Pillar, a weighted RAG summary of its KPIs.
- **Monthly hours chart** — Chart.js bar, actual vs target hours per month.
- **Next up** — the next three incomplete `MonthlyCommitment` records by date.
- **Recent activity** — last 10 `ActivityLog` entries.

**Overall progress calculation** (put in `services.py`, document the formula in a docstring):

overall = (0.30 * certification_progress)

        + (0.35 * kpi_pillar_b_progress)

        + (0.20 * kpi_pillar_c_progress)

        + (0.15 * kpi_pillar_d_progress)

Weights come from the `Pillar.weight` field — read them from the DB, do not hardcode.

### 6.3 KPI & Timetable — `/tracker/kpi/` (private)

- **Timetable view** — a month-by-month grid (Aug 2026 – Feb 2027 initially, but must render any range present in the data). Rows are courses and certifications; columns are months; cells shaded when the item is active in that month, with a distinct marker for target/exam months. Build this as a plain HTML table with CSS classes — no JS library.
- **Course list** — grouped by `tier`, showing provider, planned hours, hours logged, progress bar, status pill, and the application commitment for leadership courses.
- **Yearly KPIs** — table grouped by pillar, with code, title, target, status pill and progress.
- **Monthly plans** — accordion-free stacked sections (one per `MonthlyPlan`), each listing its commitments with completion state, plus target vs actual hours.
- Every section has an "Edit in admin" link (staff-only page, so this is safe) pointing at the relevant changelist.

Add simple GET filters: `?year=`, `?status=`, `?tier=`. Plain Django querystring handling, no JS.

### 6.4 Activity Log — `/tracker/activity/` (private)

- Reverse-chronological list, paginated at 50.
- Filters: date range, `activity_type`, related course, related certification.
- Summary strip: total hours this week, this month, this year; current streak in days.
- A small Chart.js line chart of weekly hours over the last 12 weeks.
- Logging new entries happens in Django admin — link prominently to `/admin/tracker/activitylog/add/`.

---

## 7. Django admin configuration

Admin is the only editing surface, so invest here — this is where daily use happens.

Requirements for every registered model:

- `list_display` with the fields you'd want in a table
- `list_filter` and `search_fields` where the model has more than ~10 rows
- `list_editable` for `status`, `order` and boolean flags — this is what makes bulk updating fast
- `ordering`
- `date_hierarchy` on `ActivityLog.date`

Specifics:

- `Achievement` as a `TabularInline` on `Experience`
- `MonthlyCommitment` as a `TabularInline` on `MonthlyPlan`
- `Skill` as a `TabularInline` on `SkillDomain`
- `Course` as a `TabularInline` on `Certification`
- `Profile` and `CareerObjective`: override `has_add_permission` to return False once one instance exists
- `ActivityLog`: `autocomplete_fields = ['course', 'certification', 'kpi']`, and default the date to today
- Admin actions: "Mark selected as complete" on `Course`, `KPI` and `MonthlyCommitment`
- Set `admin.site.site_header`, `site_title`, `index_title` to something meaningful

---

## 8. Design direction

Professional and quietly confident. The portfolio is read by recruiters in under a minute — clarity beats decoration.

### Visual language

- **Palette:** deep navy `#15355E` primary, teal `#1F7A6C` accent, warm off-white `#FBFAF8` page background, white cards, `#5F5E5A` secondary text. One accent colour only.
- **Type:** system font stack (`-apple-system, "Segoe UI", Roboto, sans-serif`). Headings 500 weight, body 400. Body 16px, line-height 1.7.
- **Layout:** max content width 1080px, generous whitespace, 8px spacing scale.
- **Borders:** 1px hairlines, 8px radius on controls, 12px on cards. No drop shadows, no gradients.
- **Dark mode:** implement with CSS custom properties and `prefers-color-scheme`. Define every colour as a variable.
- **Responsive:** mobile-first, single breakpoint at 768px and another at 1024px. Recruiters open links on phones.
- **Accessibility:** semantic HTML5 landmarks, WCAG AA contrast, visible focus states, alt text on images, skip-to-content link. Do not encode meaning in colour alone — status pills carry text labels too.

### "AI Inside" treatment

The requirement was to make the AI specialisation unmistakable when the information is visualised. Interpret it as **signal, not decoration**:

- A slim band directly under the hero with a monospace-ish "AI INSIDE" label and 3–4 hard metrics beside it. Understated, bordered, teal accent — not a badge or sticker.
- Skills belonging to Domain A (AI & Generative AI) render with the teal accent; all other domains use neutral navy. This makes the AI depth visually dominant without any text saying so.
- Certification cards for AI credentials carry a small teal dot.
- The radar chart draws Domain A first and in the accent colour.
- Every case study with an AI component shows a small `AI` tag.

Keep it to those five touches. Repeating the motif further makes it look gimmicky and undermines the seniority the page is meant to convey.

### Print

Add `@media print` rules so the portfolio prints cleanly to PDF — hide nav, expand all sections, black text on white, show URLs after links.

---

## 9. Charts

Chart.js 4.x from `cdnjs.cloudflare.com`. Three charts only:

1. **Skill radar** (portfolio + dashboard) — six axes, two datasets (current, target).
2. **Monthly hours bar** (dashboard) — actual vs target per month.
3. **Weekly hours line** (activity log) — last 12 weeks.

Pass data from view to template as JSON via `json_script`:

{{ chart_data|json_script:"skill-chart-data" }}

Then read it in `static/js/charts.js` with `JSON.parse(document.getElementById('skill-chart-data').textContent)`. Never build JS objects inside Django template tags.

Charts must have a text fallback — a plain table with the same numbers, visible when JS is unavailable. Recruiters sometimes browse with JS restricted.

---

## 10. Seed data

Create `tracker/management/commands/seed_roadmap.py`. It must be **idempotent** — use `update_or_create` keyed on natural keys, so re-running never duplicates. Support `--flush` to clear tracker data first.

Also create `portfolio/management/commands/seed_portfolio.py` for CV data.

### 10.1 Career objective

current_title  = "Technical Project & Business Development Manager"

target_title   = "AI Solutions Delivery Manager"

current_salary = 13000, target_salary = 20000, currency = "RM"

start_date     = 2026-08-01, target_date = 2027-09-30

### 10.2 Skill domains and skills

Levels are `(current, target)`. Set `baseline_level = current` at seed time.

**Domain A — AI & Generative AI Solution Fluency** (priority HIGHEST, order 1)

LLM architecture, capabilities and limits          (3, 4)

Prompt engineering and orchestration               (2, 4)

RAG architecture and grounding                     (2, 4)

Agentic AI and multi-agent workflows               (2, 4)

Model evaluation and hallucination control         (2, 4)

Fine-tuning vs RAG vs prompting decision           (2, 4)

MLOps lifecycle — deployment, drift, retraining    (3, 4)

Computer vision and classical ML                   (4, 4)

AI solution architecture patterns                  (3, 4)

**Domain B — Cloud & Enterprise Integration** (priority HIGH, order 2)

AWS core architecture — compute, storage, network  (3, 4)

Cloud security and identity architecture           (2, 4)

AI workload cost modelling and FinOps              (1, 4)

Enterprise and API integration                     (4, 4)

Data architecture and pipelines                    (3, 4)

Multi-cloud and hybrid deployment                  (3, 3)

**Domain C — Delivery & Programme Governance** (priority MEDIUM, order 3)

Programme planning, scheduling, critical path      (4, 4)

Risk and issue management                          (4, 4)

Budget and financial control                       (4, 4)

Vendor and procurement management                  (4, 4)

Agile, Scrum and hybrid delivery models            (2, 4)

Estimating AI projects under uncertainty           (2, 4)

SLA design and service transition                  (4, 4)

**Domain D — AI Governance, Risk & Compliance** (priority HIGH, order 4)

Responsible AI — bias, fairness, transparency      (2, 4)

AI regulation landscape — EU AI Act and successors (1, 3)

ISO/IEC 42001 AI management systems                (1, 3)

Data privacy — PDPA, PDPL, GDPR-equivalent         (4, 4)

Model risk, audit and assurance                    (2, 3)

**Domain E — Commercial & Client Engagement** (priority MEDIUM, order 5)

Pre-sales solutioning and proposals                (4, 4)

Business case and ROI modelling                    (2, 4)

Pricing and commercial structuring                 (2, 3)

Contract, SOW and scope management                 (3, 4)

Client relationship and account growth             (3, 4)

**Domain F — Leadership & Influence** (priority HIGHEST, order 6)

Executive presence and board-level communication   (2, 4)

Influencing without authority                      (2, 4)

Team leadership, delegation and coaching           (3, 4)

Difficult conversations and conflict resolution    (2, 4)

Negotiation — client, vendor and internal          (2, 4)

Hiring and building capability                     (1, 3)

Storytelling with data                             (2, 4)

### 10.3 Certifications

1. AWS Certified AI Practitioner (AIF-C01)

   provider="Amazon Web Services", status=PLANNED, planned_hours=25,

   cost=100 USD, target_date=2026-09-30, domains=[A, D]

2. Google Project Management Certificate (35 contact hours)

   provider="Coursera / Google", status=PLANNED, planned_hours=45,

   cost=0, target_date=2026-10-25, domains=[C]

3. AWS Certified Solutions Architect — Associate (SAA-C03)

   provider="Amazon Web Services", status=PLANNED, planned_hours=50,

   cost=150 USD, target_date=2026-11-30, domains=[B]

4. PMP

   provider="Project Management Institute", status=PLANNED, planned_hours=45,

   cost=545 USD, target_date=2027-02-28, domains=[C, E]

Also seed existing credentials with `status=EARNED` and `show_on_portfolio=True`: Microsoft Azure AI Essentials Professional Certificate; AWS Technical Essentials; AWS Systems Operations (SysOps); Machine Learning for Business Intelligence (iTrain); Master Computer Vision OpenCV4 with Deep Learning (Udemy).

### 10.4 Courses

Tier CERTIFICATION — linked to the certifications above via the `certification` FK.

Tier TECHNICAL:

Generative and Agentic AI — Oxford Saïd Business School / Coursera

    15 hrs, domain A, start 2026-08-01, target 2026-09-30

AI workload cost and FinOps fundamentals — AWS Skill Builder

    8 hrs, domain B, start 2026-11-01, target 2026-11-30

Agile and Scrum foundations — Coursera / LinkedIn Learning

    10 hrs, domain C, start 2026-12-01, target 2026-12-31

IBM RAG and Agentic AI Professional Certificate — IBM / Coursera

    30 hrs, domain A, target 2027 (status NOT_STARTED, optional)

Tier LEADERSHIP — all LinkedIn Learning, domain F unless noted. Each carries an `application_commitment`:

Executive Presence and Communicating with Executives   3 hrs, Aug 2026

    → "Apply one executive-communication technique with the Group CEO"

Influencing Without Authority                          3 hrs, Sep 2026

    → "Apply an influence technique with a vendor or client stakeholder"

Financial Acumen for Non-Financial Managers            6 hrs, Sep–Oct 2026, domain E

    → "Build a business case for one live initiative"

Storytelling with Data                                 3 hrs, Oct 2026

    → "Rebuild one existing project report using data-storytelling structure"

Having Difficult Conversations                         2 hrs, Oct 2026

    → "Hold one overdue difficult conversation"

Coaching and Developing Employees                      3 hrs, Nov 2026

    → "Hold one structured coaching conversation with a team member"

Negotiation Skills                                     4 hrs, Nov–Dec 2026

    → "Apply the framework in one vendor or client negotiation"

Leading High-Performing and Distributed Teams          3 hrs, Dec 2026

    → "Run one team retrospective using the course structure"

Strategic Thinking                                     3 hrs, Dec 2026

    → "Draft a one-page technology strategy for the HoloMe portfolio"

### 10.5 Pillars

A — Capability        weight 30   "Certifications earned, courses completed, skill levels raised"

B — Applied evidence  weight 35   "Techniques used at work, outcomes produced, case studies written"

C — Visibility        weight 20   "Profile, network, recruiter reach, professional presence"

D — Career outcome    weight 15   "Title, offers, compensation"

### 10.6 Yearly KPIs (period=YEARLY, period_year=2026, covering Aug 2026 – Jul 2027)

A1  AWS Certified AI Practitioner                     Pass by 30 Sep 2026        Certificate issued

A2  AWS Solutions Architect — Associate               Pass by 30 Nov 2026        Certificate issued

A3  Google PM Certificate — 35 contact hours          Complete by 25 Oct 2026    Certificate issued

A4  PMP                                               Pass by 28 Feb 2027        Certificate issued

A5  Oxford Generative and Agentic AI                  Complete by 30 Sep 2026    Certificate issued

A6  Leadership courses completed                      9 by 31 Dec 2026           Completion records

A7  Domain A average skill level                      2.6 → 3.5+ by Dec 2026     Self-assessment

A8  Domain F average skill level                      2.0 → 3.2+ by Dec 2026     Self-assessment

B1  Leadership techniques applied and documented      9 — one per course        Written reflection

B2  Quantified case studies written (STAR)            4 by 31 Dec 2026           Evidence pack

B3  AI governance artefact produced at work           1 — responsible-AI checklist  Document in use

B4  AI project cost model built                       1 — inference/run-cost model  Spreadsheet in use

B5  New commercial value closed or milestone owned    1 minimum with an RM figure   Documented

B6  Executive-level presentation delivered            3                          Logged with feedback

C1  LinkedIn profile rebuilt to AI Delivery narrative By 31 Aug 2026             Published

C2  LinkedIn posts published                          18                         Post count

C3  Relevant new connections                          +300                       Connection count

C4  Recruiter or hiring-manager conversations         8                          Tracker

C5  Informational interviews in target role           5                          Tracker

C6  Public professional presence — talk or article    1                          Link or recording

D1  CV consolidated to single target title            By 15 Aug 2026             One master CV

D2  Internal title change requested                   By 31 Jan 2027             Conversation held

D3  Target company list built                         15 companies by 31 Dec 2026  Written list

D4  Formal offers received at target band             2+ by 31 Jul 2027          Written offers

D5  Base salary                                       RM 20,000+ by 30 Sep 2027  Signed contract

Set `target_value` where the KPI is numeric (A6=9, B1=9, B2=4, B6=3, C2=18, C3=300, C4=8, C5=5, D3=15, D4=2, D5=20000) and `current_value=0`.

### 10.7 Monthly plans

2026-08  "Foundations"                        target_hours 38

2026-09  "First certification"                target_hours 40

2026-10  "Delivery credential"                target_hours 40

2026-11  "Second certification"               target_hours 40

2026-12  "Consolidate and position"           target_hours 36

2027-01  "PMP push"                           target_hours 32

2027-02  "Qualified"                          target_hours 16

Seed the monthly commitments from Section 6 of the roadmap document — each row becomes one `MonthlyCommitment` with its pillar, commitment text and `done_when`. There are roughly 45 in total across the seven months.

### 10.8 Portfolio seed

**Profile**

full_name = "Reza Yousefi"

headline  = "AI Solutions Delivery Manager"

location  = "Kuala Lumpur, Malaysia"

email     = "reza.robotics65@gmail.com"

phone     = "+60 12-703 7145"

linkedin  = "https://linkedin.com/in/reza-yousefi86"

years_experience = 12

Write the `introduction` from the AI Solutions Delivery Manager CV summary: AI delivery leader with 12+ years taking AI solutions from design to live enterprise deployment, currently delivering AI Digital Human (HoloMe) programmes across Southeast Asia and the Middle East, combining applied computer vision and machine learning engineering with senior delivery leadership across cross-functional, cross-regional teams.

**Languages** — English (PROFESSIONAL), Arabic (PROFESSIONAL). Add Malay and Persian if applicable; leave the seed to those two plus a comment.

**Experience** — seed all eight roles from the CV:

Byond Asia — Technical Project & Business Development Manager, Selangor, Nov 2025 – present

Sena Traffic Systems (ITMAX) — Project Manager, KL, 2022 – Nov 2025

Ace Resource Advisory Services — Assistant Manager, Analytics & Business Insights, KL, 2021 – 2022

N'osairis Technology Solutions — Software Developer & IoT Solution Consultant & BI Developer, KL, 2018 – 2021

Sena Traffic Systems — R&D Engineer, KL, 2017 – 2018

MMU Centre of Robotics & Automation — Research Officer, Melaka, 2015 – 2017

Cohu (Ismeca) — Software Engineer Assistant, Melaka, 2014 – 2015

iRadar Sdn Bhd — Research Assistant, Melaka, 2013

Seed achievements from the CV bullets. Mark these four `is_headline=True`:

"600+"      "AI-managed intersections delivered"

"60%+"      "reduction in system incidents"

"RM 1.2M"   "enterprise engagement closed"

"95%"       "programme budget adherence"

**Education** — Bachelor of Electronics Engineering (Robotics & Automation), Multimedia University, Melaka, 2015.

**Case studies** — create four stubs, `is_published=False`, for the author to complete:

Kuala Lumpur smart traffic — 600+ intersections, 60% incident reduction

JCorp / KPJ — RM 1.2M AI solution engagement

Project & Portfolio Management platform build

Cross-regional AI Digital Human (HoloMe) rollout

---

## 11. Testing

Use `pytest-django`. Do not skip this — the access control rules in Section 3 must be verified.

Required tests:

- Anonymous GET `/` returns 200
- Anonymous GET each `/tracker/*` URL returns 302 to login
- Non-staff authenticated user GET `/tracker/` returns 302
- Staff user GET each tracker URL returns 200
- Unpublished `Profile`, `Experience` and `CaseStudy` records do not appear in the public page HTML
- `seed_roadmap` is idempotent — run twice, assert object counts unchanged
- `Skill.gap` returns the correct band for level deltas 0, 1, 2, 3
- `Course.progress_pct` caps at 100 and returns 100 when status is COMPLETE
- `MonthlyPlan.actual_hours` correctly sums only that month's activity
- Dashboard overall-progress calculation against a known fixture

Target: every view has at least one test; `services.py` has full coverage.

---

## 12. Build order

Work through these in sequence. Each milestone should end with a working, committed application.

**M1 — Foundation.** Django project, split settings, Postgres connection, `.env.example`, `.gitignore`, base templates, CSS custom properties and reset. Verify the server runs.

**M2 — Models and admin.** All models from Section 5, migrations, full admin configuration from Section 7. Verify every model is creatable and editable in admin.

**M3 — Access control.** Login template, `staff_member_required` on all tracker URLs, the tests from Section 11 covering access. **Do not proceed until these tests pass.**

**M4 — Seed commands.** `seed_roadmap` and `seed_portfolio`, idempotent, with the `--flush` option. Verify by running twice.

**M5 — Portfolio page.** All ten sections, responsive, dark mode, print styles, AI Inside treatment. Case study detail page.

**M6 — Dashboard.** `services.py` calculations first with tests, then the view and template, then the charts.

**M7 — KPI and timetable page.** Timetable grid, course list, KPI tables, monthly plans, GET filters.

**M8 — Activity log.** List, filters, pagination, summary strip, weekly chart.

**M9 — Polish.** Accessibility audit, Lighthouse pass, mobile check at 375px, empty states for every list, 404 and 500 templates.

**M10 — Deployment appendix.** `requirements.txt` pinned, WhiteNoise for static, `collectstatic`, Gunicorn config, `Procfile`, README with setup steps.

---

## 13. Acceptance criteria

The build is done when all of the following are true:

- [ ] A logged-out visitor sees a complete, professional portfolio at `/` and cannot reach or discover any tracker page.
- [ ] A non-staff logged-in user cannot reach any tracker page.
- [ ] Every content change can be made through Django admin without touching code.
- [ ] `python manage.py seed_roadmap && python manage.py seed_portfolio` produces a fully populated, usable application on a clean database.
- [ ] Running either seed command twice creates no duplicates.
- [ ] The dashboard shows a single overall progress figure derived from pillar weights held in the database.
- [ ] The timetable renders correctly for any date range present in the data, not just Aug 2026 – Feb 2027.
- [ ] Every study session logged in `ActivityLog` flows through to course progress, monthly actual hours, and the dashboard.
- [ ] The portfolio is legible and correctly laid out at 375px width.
- [ ] The portfolio prints to a clean single-document PDF.
- [ ] Charts have a table fallback when JavaScript is disabled.
- [ ] All tests in Section 11 pass.
- [ ] No secret values are committed to the repository.

---

## 14. Open questions for the author

Answer these before or during M1 — they are small but affect the model:

1. Should `Language` include Malay and Persian, and at what proficiency?
2. Do you want a visitor counter or basic analytics on the portfolio, so you can see recruiter interest? (Adds a small model and middleware; Plausible or GoatCounter would be simpler.)
3. Should the CV download be a static uploaded PDF, or generated from the portfolio data?
4. Do you want email notifications for monthly reviews, or is the dashboard sufficient?
5. Should salary figures appear anywhere outside the private dashboard? Default assumption: never, and they are excluded from all public templates.
