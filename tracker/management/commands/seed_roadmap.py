"""
Idempotent seed command for tracker app data: career objective, skill domains
and skills, certifications, courses, pillars, KPIs and monthly plans.

Keyed on natural keys via update_or_create so re-running never duplicates
(BUILD_BRIEF.md Section 10). ActivityLog is deliberately never touched here —
it holds real logged work, not seed data.

Source: BUILD_BRIEF.md Section 10. Section 10.7 asks for monthly commitments
drawn from "Section 6 of the roadmap document" — that external document was
not supplied alongside the brief, so the ~45 commitments below are synthesised
from the KPIs, courses and certifications the brief does specify for each
month. Edit freely in Django admin.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from tracker.models import (
    CareerObjective,
    Certification,
    Course,
    KPI,
    MonthlyCommitment,
    MonthlyPlan,
    Pillar,
    Skill,
    SkillDomain,
)


def d(year, month, day=1):
    return date(year, month, day)


class Command(BaseCommand):
    help = 'Seed career objective, skills, certifications, courses, pillars, KPIs and monthly plans.'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Clear tracker roadmap data before seeding.')

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing tracker roadmap data...')
            MonthlyCommitment.objects.all().delete()
            MonthlyPlan.objects.all().delete()
            KPI.objects.all().delete()
            Pillar.objects.all().delete()
            Course.objects.all().delete()
            Certification.objects.all().delete()
            Skill.objects.all().delete()
            SkillDomain.objects.all().delete()
            CareerObjective.objects.all().delete()

        with transaction.atomic():
            self.seed_career_objective()
            domains = self.seed_skill_domains_and_skills()
            certifications = self.seed_certifications(domains)
            self.seed_courses(domains, certifications)
            pillars = self.seed_pillars()
            self.seed_kpis(pillars)
            self.seed_monthly_plans(pillars)

        self.stdout.write(self.style.SUCCESS('seed_roadmap complete.'))

    # ------------------------------------------------------------------
    def seed_career_objective(self):
        CareerObjective.objects.update_or_create(pk=1, defaults=dict(
            current_title='Technical Project & Business Development Manager',
            target_title='AI Solutions Delivery Manager',
            current_salary=13000,
            target_salary=20000,
            currency='RM',
            start_date=d(2026, 8, 1),
            target_date=d(2027, 9, 30),
        ))
        self.stdout.write('Career objective seeded.')

    # ------------------------------------------------------------------
    def seed_skill_domains_and_skills(self):
        domain_defs = [
            ('A', 'AI & Generative AI Solution Fluency', 'HIGHEST', 1, [
                ('LLM architecture, capabilities and limits', 3, 4),
                ('Prompt engineering and orchestration', 2, 4),
                ('RAG architecture and grounding', 2, 4),
                ('Agentic AI and multi-agent workflows', 2, 4),
                ('Model evaluation and hallucination control', 2, 4),
                ('Fine-tuning vs RAG vs prompting decision', 2, 4),
                ('MLOps lifecycle — deployment, drift, retraining', 3, 4),
                ('Computer vision and classical ML', 4, 4),
                ('AI solution architecture patterns', 3, 4),
            ]),
            ('B', 'Cloud & Enterprise Integration', 'HIGH', 2, [
                ('AWS core architecture — compute, storage, network', 3, 4),
                ('Cloud security and identity architecture', 2, 4),
                ('AI workload cost modelling and FinOps', 1, 4),
                ('Enterprise and API integration', 4, 4),
                ('Data architecture and pipelines', 3, 4),
                ('Multi-cloud and hybrid deployment', 3, 3),
            ]),
            ('C', 'Delivery & Programme Governance', 'MEDIUM', 3, [
                ('Programme planning, scheduling, critical path', 4, 4),
                ('Risk and issue management', 4, 4),
                ('Budget and financial control', 4, 4),
                ('Vendor and procurement management', 4, 4),
                ('Agile, Scrum and hybrid delivery models', 2, 4),
                ('Estimating AI projects under uncertainty', 2, 4),
                ('SLA design and service transition', 4, 4),
            ]),
            ('D', 'AI Governance, Risk & Compliance', 'HIGH', 4, [
                ('Responsible AI — bias, fairness, transparency', 2, 4),
                ('AI regulation landscape — EU AI Act and successors', 1, 3),
                ('ISO/IEC 42001 AI management systems', 1, 3),
                ('Data privacy — PDPA, PDPL, GDPR-equivalent', 4, 4),
                ('Model risk, audit and assurance', 2, 3),
            ]),
            ('E', 'Commercial & Client Engagement', 'MEDIUM', 5, [
                ('Pre-sales solutioning and proposals', 4, 4),
                ('Business case and ROI modelling', 2, 4),
                ('Pricing and commercial structuring', 2, 3),
                ('Contract, SOW and scope management', 3, 4),
                ('Client relationship and account growth', 3, 4),
            ]),
            ('F', 'Leadership & Influence', 'HIGHEST', 6, [
                ('Executive presence and board-level communication', 2, 4),
                ('Influencing without authority', 2, 4),
                ('Team leadership, delegation and coaching', 3, 4),
                ('Difficult conversations and conflict resolution', 2, 4),
                ('Negotiation — client, vendor and internal', 2, 4),
                ('Hiring and building capability', 1, 3),
                ('Storytelling with data', 2, 4),
            ]),
        ]

        domains = {}
        for code, name, priority, order, skills in domain_defs:
            domain, _ = SkillDomain.objects.update_or_create(
                code=code,
                defaults=dict(name=name, priority=priority, order=order),
            )
            domains[code] = domain
            for i, (skill_name, current, target) in enumerate(skills, start=1):
                Skill.objects.update_or_create(
                    domain=domain, name=skill_name,
                    defaults=dict(current_level=current, target_level=target, baseline_level=current, order=i),
                )
        self.stdout.write(f'{len(domain_defs)} skill domains seeded.')
        return domains

    # ------------------------------------------------------------------
    def seed_certifications(self, domains):
        planned_defs = [
            dict(name='AWS Certified AI Practitioner (AIF-C01)', provider='Amazon Web Services',
                 status='PLANNED', priority=1, planned_hours=25, cost_amount=100, cost_currency='USD',
                 target_date=d(2026, 9, 30), domain_codes=['A', 'D'], order=1),
            dict(name='Google Project Management Certificate', provider='Coursera / Google',
                 status='PLANNED', priority=2, planned_hours=45, cost_amount=0, cost_currency='USD',
                 target_date=d(2026, 10, 25), domain_codes=['C'], order=2),
            dict(name='AWS Certified Solutions Architect – Associate (SAA-C03)', provider='Amazon Web Services',
                 status='PLANNED', priority=3, planned_hours=50, cost_amount=150, cost_currency='USD',
                 target_date=d(2026, 11, 30), domain_codes=['B'], order=3),
            dict(name='PMP', provider='Project Management Institute',
                 status='PLANNED', priority=4, planned_hours=45, cost_amount=545, cost_currency='USD',
                 target_date=d(2027, 2, 28), domain_codes=['C', 'E'], order=4),
        ]
        earned_defs = [
            dict(name='Microsoft Azure AI Essentials Professional Certificate', provider='Microsoft / LinkedIn Learning', order=5),
            dict(name='AWS Technical Essentials', provider='Amazon Web Services', order=6),
            dict(name='AWS Systems Operations (SysOps)', provider='Amazon Web Services', order=7),
            dict(name='Machine Learning for Business Intelligence', provider='iTrain', order=8),
            dict(name='Master Computer Vision OpenCV4 with Deep Learning', provider='Udemy', order=9),
        ]

        certifications = {}
        for defn in planned_defs:
            domain_codes = defn.pop('domain_codes')
            cert, _ = Certification.objects.update_or_create(
                name=defn.pop('name'), defaults=dict(show_on_portfolio=True, **defn),
            )
            cert.domains.set([domains[c] for c in domain_codes])
            certifications[cert.name] = cert

        for defn in earned_defs:
            cert, _ = Certification.objects.update_or_create(
                name=defn.pop('name'),
                defaults=dict(
                    provider=defn['provider'], status='EARNED', priority=defn['order'],
                    planned_hours=0, show_on_portfolio=True, order=defn['order'],
                ),
            )
            certifications[cert.name] = cert

        self.stdout.write(f'{len(planned_defs) + len(earned_defs)} certifications seeded.')
        return certifications

    # ------------------------------------------------------------------
    def seed_courses(self, domains, certifications):
        technical = [
            dict(name='Generative and Agentic AI', provider='Oxford Saïd Business School / Coursera',
                 domain='A', planned_hours=15, start_month=d(2026, 8), target_month=d(2026, 9), order=1),
            dict(name='AI workload cost and FinOps fundamentals', provider='AWS Skill Builder',
                 domain='B', planned_hours=8, start_month=d(2026, 11), target_month=d(2026, 11), order=2),
            dict(name='Agile and Scrum foundations', provider='Coursera / LinkedIn Learning',
                 domain='C', planned_hours=10, start_month=d(2026, 12), target_month=d(2026, 12), order=3),
            dict(name='IBM RAG and Agentic AI Professional Certificate', provider='IBM / Coursera',
                 domain='A', planned_hours=30, status='NOT_STARTED', start_month=None,
                 target_month=d(2027, 12, 31), order=4),
            dict(name='Microsoft Azure AI Essentials: Workloads and Machine Learning on Azure',
                 provider='LinkedIn Learning', domain='A', planned_hours=0, status='COMPLETE',
                 start_month=None, target_month=None, order=5),
        ]

        leadership = [
            dict(name='Executive Presence and Communicating with Executives', planned_hours=3,
                 start_month=d(2026, 8), target_month=d(2026, 8),
                 application_commitment='Apply one executive-communication technique with the Group CEO', order=1),
            dict(name='Influencing Without Authority', planned_hours=3,
                 start_month=d(2026, 9), target_month=d(2026, 9),
                 application_commitment='Apply an influence technique with a vendor or client stakeholder', order=2),
            dict(name='Financial Acumen for Non-Financial Managers', planned_hours=6, domain='E',
                 start_month=d(2026, 9), target_month=d(2026, 10),
                 application_commitment='Build a business case for one live initiative', order=3),
            dict(name='Storytelling with Data', planned_hours=3,
                 start_month=d(2026, 10), target_month=d(2026, 10),
                 application_commitment='Rebuild one existing project report using data-storytelling structure', order=4),
            dict(name='Having Difficult Conversations', planned_hours=2,
                 start_month=d(2026, 10), target_month=d(2026, 10),
                 application_commitment='Hold one overdue difficult conversation', order=5),
            dict(name='Coaching and Developing Employees', planned_hours=3,
                 start_month=d(2026, 11), target_month=d(2026, 11),
                 application_commitment='Hold one structured coaching conversation with a team member', order=6),
            dict(name='Negotiation Skills', planned_hours=4,
                 start_month=d(2026, 11), target_month=d(2026, 12),
                 application_commitment='Apply the framework in one vendor or client negotiation', order=7),
            dict(name='Leading High-Performing and Distributed Teams', planned_hours=3,
                 start_month=d(2026, 12), target_month=d(2026, 12),
                 application_commitment='Run one team retrospective using the course structure', order=8),
            dict(name='Strategic Thinking', planned_hours=3,
                 start_month=d(2026, 12), target_month=d(2026, 12),
                 application_commitment='Draft a one-page technology strategy for the HoloMe portfolio', order=9),
            dict(name="Leveraging the Power of Social Intelligence in the Age of AI", planned_hours=0,
                 status='COMPLETE', start_month=None, target_month=None, order=10),
            dict(name='Advanced Agile: The Team\'s Mindset', planned_hours=0, domain='C',
                 status='COMPLETE', start_month=None, target_month=None, order=11),
        ]

        count = 0
        for defn in technical:
            domain_code = defn.pop('domain')
            status = defn.pop('status', 'NOT_STARTED')
            Course.objects.update_or_create(
                name=defn.pop('name'),
                defaults=dict(
                    tier='TECHNICAL', provider=defn.pop('provider'), status=status,
                    domain=domains.get(domain_code), is_free=True, **defn,
                ),
            )
            count += 1

        for defn in leadership:
            domain_code = defn.pop('domain', 'F')
            status = defn.pop('status', 'NOT_STARTED')
            Course.objects.update_or_create(
                name=defn.pop('name'),
                defaults=dict(
                    tier='LEADERSHIP', provider='LinkedIn Learning', status=status,
                    domain=domains.get(domain_code), is_free=True, **defn,
                ),
            )
            count += 1

        # Certification-tier courses, linked to their certification via FK.
        for cert_name, hours in [
            ('AWS Certified AI Practitioner (AIF-C01)', 25),
            ('Google Project Management Certificate', 45),
            ('AWS Certified Solutions Architect – Associate (SAA-C03)', 50),
            ('PMP', 45),
        ]:
            c = certifications.get(cert_name)
            if not c:
                continue
            Course.objects.update_or_create(
                name=f'{cert_name} — exam prep',
                defaults=dict(
                    tier='CERTIFICATION', provider=c.provider, status='NOT_STARTED',
                    domain=c.domains.first(), certification=c, planned_hours=hours,
                    is_free=(c.cost_amount == 0), target_month=c.target_date.replace(day=1) if c.target_date else None,
                    order=c.order,
                ),
            )
            count += 1

        self.stdout.write(f'{count} courses seeded.')

    # ------------------------------------------------------------------
    def seed_pillars(self):
        defs = [
            ('A', 'Capability', 30, 'Certifications earned, courses completed, skill levels raised', 1),
            ('B', 'Applied evidence', 35, 'Techniques used at work, outcomes produced, case studies written', 2),
            ('C', 'Visibility', 20, 'Profile, network, recruiter reach, professional presence', 3),
            ('D', 'Career outcome', 15, 'Title, offers, compensation', 4),
        ]
        pillars = {}
        for code, name, weight, description, order in defs:
            pillar, _ = Pillar.objects.update_or_create(
                code=code, defaults=dict(name=name, weight=weight, description=description, order=order),
            )
            pillars[code] = pillar
        self.stdout.write('4 pillars seeded.')
        return pillars

    # ------------------------------------------------------------------
    def seed_kpis(self, pillars):
        # code, title, target, verified_by, due_date, target_value
        defs = [
            ('A1', 'AWS Certified AI Practitioner', 'Pass by 30 Sep 2026', 'Certificate issued', d(2026, 9, 30), None),
            ('A2', 'AWS Solutions Architect – Associate', 'Pass by 30 Nov 2026', 'Certificate issued', d(2026, 11, 30), None),
            ('A3', 'Google PM Certificate – 35 contact hours', 'Complete by 25 Oct 2026', 'Certificate issued', d(2026, 10, 25), None),
            ('A4', 'PMP', 'Pass by 28 Feb 2027', 'Certificate issued', d(2027, 2, 28), None),
            ('A5', 'Oxford Generative and Agentic AI', 'Complete by 30 Sep 2026', 'Certificate issued', d(2026, 9, 30), None),
            ('A6', 'Leadership courses completed', '9 by 31 Dec 2026', 'Completion records', d(2026, 12, 31), 9),
            ('A7', 'Domain A average skill level', '2.6 → 3.5+ by Dec 2026', 'Self-assessment', d(2026, 12, 31), None),
            ('A8', 'Domain F average skill level', '2.0 → 3.2+ by Dec 2026', 'Self-assessment', d(2026, 12, 31), None),
            ('B1', 'Leadership techniques applied and documented', '9 – one per course', 'Written reflection', None, 9),
            ('B2', 'Quantified case studies written (STAR)', '4 by 31 Dec 2026', 'Evidence pack', d(2026, 12, 31), 4),
            ('B3', 'AI governance artefact produced at work', '1 – responsible-AI checklist', 'Document in use', None, None),
            ('B4', 'AI project cost model built', '1 – inference/run-cost model', 'Spreadsheet in use', None, None),
            ('B5', 'New commercial value closed or milestone owned', '1 minimum with an RM figure', 'Documented', None, None),
            ('B6', 'Executive-level presentation delivered', '3', 'Logged with feedback', None, 3),
            ('C1', 'LinkedIn profile rebuilt to AI Delivery narrative', 'By 31 Aug 2026', 'Published', d(2026, 8, 31), None),
            ('C2', 'LinkedIn posts published', '18', 'Post count', None, 18),
            ('C3', 'Relevant new connections', '+300', 'Connection count', None, 300),
            ('C4', 'Recruiter or hiring-manager conversations', '8', 'Tracker', None, 8),
            ('C5', 'Informational interviews in target role', '5', 'Tracker', None, 5),
            ('C6', 'Public professional presence – talk or article', '1', 'Link or recording', None, None),
            ('D1', 'CV consolidated to single target title', 'By 15 Aug 2026', 'One master CV', d(2026, 8, 15), None),
            ('D2', 'Internal title change requested', 'By 31 Jan 2027', 'Conversation held', d(2027, 1, 31), None),
            ('D3', 'Target company list built', '15 companies by 31 Dec 2026', 'Written list', d(2026, 12, 31), 15),
            ('D4', 'Formal offers received at target band', '2+ by 31 Jul 2027', 'Written offers', d(2027, 7, 31), 2),
            ('D5', 'Base salary', 'RM 20,000+ by 30 Sep 2027', 'Signed contract', d(2027, 9, 30), 20000),
        ]
        for i, (code, title, target, verified_by, due_date, target_value) in enumerate(defs, start=1):
            pillar = pillars[code[0]]
            KPI.objects.update_or_create(
                code=code,
                defaults=dict(
                    pillar=pillar, title=title, target=target, verified_by=verified_by,
                    period='YEARLY', period_year=2026, status='NOT_STARTED',
                    target_value=target_value, current_value=0 if target_value is not None else None,
                    due_date=due_date, order=i,
                ),
            )
        self.stdout.write(f'{len(defs)} KPIs seeded.')

    # ------------------------------------------------------------------
    def seed_monthly_plans(self, pillars):
        plan_defs = [
            (2026, 8, 'Foundations', 38),
            (2026, 9, 'First certification', 40),
            (2026, 10, 'Delivery credential', 40),
            (2026, 11, 'Second certification', 40),
            (2026, 12, 'Consolidate and position', 36),
            (2027, 1, 'PMP push', 32),
            (2027, 2, 'Qualified', 16),
        ]

        # (year, month) -> list of (pillar_code, commitment, done_when)
        commitment_defs = {
            (2026, 8): [
                ('A', 'Start AWS Certified AI Practitioner exam prep', 'Study plan active, first module complete'),
                ('A', 'Start Oxford Generative and Agentic AI course', 'Enrolled and first two units complete'),
                ('C', 'Rebuild LinkedIn profile to AI Delivery narrative', 'Profile published (KPI C1)'),
                ('D', 'Consolidate CV to single target title', 'One master CV finalised (KPI D1)'),
                ('A', 'Complete Executive Presence and Communicating with Executives', 'Course marked complete'),
                ('B', 'Apply one executive-communication technique with the Group CEO', 'Technique used and reflected on'),
                ('C', 'Publish first LinkedIn posts', '2 posts published'),
            ],
            (2026, 9): [
                ('A', 'Sit and pass AWS Certified AI Practitioner exam', 'Certificate issued (KPI A1)'),
                ('A', 'Complete Oxford Generative and Agentic AI course', 'Certificate issued (KPI A5)'),
                ('A', 'Complete Influencing Without Authority course', 'Course marked complete'),
                ('B', 'Apply an influence technique with a vendor or client stakeholder', 'Technique used and documented'),
                ('C', 'Continue LinkedIn posting cadence', '4 posts published cumulative'),
                ('C', 'Start recruiter and hiring-manager conversations', '2 conversations logged'),
            ],
            (2026, 10): [
                ('A', 'Complete Google Project Management Certificate', 'Certificate issued (KPI A3)'),
                ('A', 'Complete Financial Acumen for Non-Financial Managers course', 'Course marked complete'),
                ('B', 'Build a business case for one live initiative', 'Business case documented'),
                ('A', 'Complete Storytelling with Data course', 'Course marked complete'),
                ('B', 'Rebuild one project report using data-storytelling structure', 'Report rebuilt and shared'),
                ('A', 'Complete Having Difficult Conversations course', 'Course marked complete'),
                ('B', 'Hold one overdue difficult conversation', 'Conversation held and reflected on'),
                ('C', 'Run informational interviews in target role', '2 interviews logged'),
            ],
            (2026, 11): [
                ('A', 'Sit and pass AWS Solutions Architect – Associate exam', 'Certificate issued (KPI A2)'),
                ('B', 'Complete AI workload cost and FinOps fundamentals course', 'Course marked complete'),
                ('B', 'Build an AI project cost model', 'Spreadsheet in use (KPI B4)'),
                ('A', 'Complete Coaching and Developing Employees course', 'Course marked complete'),
                ('B', 'Hold one structured coaching conversation with a team member', 'Conversation held and documented'),
                ('A', 'Start Negotiation Skills course', 'Course in progress'),
                ('B', 'Deliver first executive-level presentation', '1 of 3 delivered with feedback logged'),
            ],
            (2026, 12): [
                ('A', 'Complete Negotiation Skills course', 'Course marked complete'),
                ('B', 'Apply negotiation framework in one vendor or client negotiation', 'Negotiation logged'),
                ('A', 'Complete Leading High-Performing and Distributed Teams course', 'Course marked complete'),
                ('B', 'Run one team retrospective using the course structure', 'Retrospective held'),
                ('A', 'Complete Strategic Thinking course', 'Course marked complete'),
                ('B', 'Draft a one-page technology strategy for the HoloMe portfolio', 'Draft circulated'),
                ('B', 'Finish quantified STAR case studies', '4 case studies complete (KPI B2)'),
                ('C', 'Publish a public professional talk or article', 'Link or recording captured (KPI C6)'),
            ],
            (2027, 1): [
                ('A', 'Enter PMP exam prep intensive', 'Study plan active, mock exam scored'),
                ('D', 'Request internal title change conversation', 'Conversation held (KPI D2)'),
                ('B', 'Close new commercial value or own a milestone with an RM figure', 'Value documented (KPI B5)'),
                ('C', 'Continue recruiter and hiring-manager conversations', '6 conversations logged cumulative'),
            ],
            (2027, 2): [
                ('A', 'Sit and pass PMP exam', 'Certificate issued (KPI A4)'),
                ('B', 'Deliver remaining executive-level presentations', '3 of 3 delivered with feedback logged'),
                ('C', 'Reach 18 LinkedIn posts published', 'Post count at target (KPI C2)'),
                ('D', 'Review formal offers pipeline against target band', 'Pipeline reviewed'),
            ],
        }

        plan_count = 0
        commitment_count = 0
        for year, month, theme, target_hours in plan_defs:
            plan, _ = MonthlyPlan.objects.update_or_create(
                year=year, month=month,
                defaults=dict(theme=theme, target_hours=target_hours, status='PLANNED'),
            )
            plan_count += 1
            for i, (pillar_code, commitment, done_when) in enumerate(commitment_defs.get((year, month), []), start=1):
                MonthlyCommitment.objects.update_or_create(
                    plan=plan, order=i,
                    defaults=dict(pillar=pillars[pillar_code], commitment=commitment, done_when=done_when),
                )
                commitment_count += 1

        self.stdout.write(f'{plan_count} monthly plans and {commitment_count} commitments seeded.')
