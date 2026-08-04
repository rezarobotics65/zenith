"""
Idempotent seed command for portfolio app data: profile, languages,
experience, education and case-study stubs (BUILD_BRIEF.md Section 10.8).

Languages: the brief asks to seed English and Arabic as PROFESSIONAL, and to
"add Malay and Persian if applicable". Both are added here — Persian as
NATIVE (reflecting the author's background) and Malay as CONVERSATIONAL
(working-level, acquired during 12+ years based in Malaysia). Adjust freely
in Django admin if that's wrong.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from portfolio.models import Achievement, CaseStudy, Education, Experience, Language, Profile


def d(year, month, day=1):
    return date(year, month, day)


class Command(BaseCommand):
    help = 'Seed profile, languages, experience, education and case-study stubs.'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Clear portfolio data before seeding.')

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing portfolio data...')
            CaseStudy.objects.all().delete()
            Achievement.objects.all().delete()
            Experience.objects.all().delete()
            Education.objects.all().delete()
            Language.objects.all().delete()
            Profile.objects.all().delete()

        with transaction.atomic():
            self.seed_profile()
            self.seed_languages()
            experiences = self.seed_experience()
            self.seed_education()
            self.seed_case_studies(experiences)

        self.stdout.write(self.style.SUCCESS('seed_portfolio complete.'))

    # ------------------------------------------------------------------
    def seed_profile(self):
        introduction = (
            "AI delivery leader with 12+ years taking AI solutions from design to live enterprise "
            "deployment, currently delivering AI Digital Human (HoloMe) programmes across Southeast "
            "Asia and the Middle East.\n\n"
            "Combines applied computer vision and machine learning engineering with senior delivery "
            "leadership across cross-functional, cross-regional teams — translating emerging AI "
            "capability into programmes that ship, scale and hold up under enterprise governance."
        )
        Profile.objects.update_or_create(pk=1, defaults=dict(
            full_name='Reza Yousefi',
            headline='AI Solutions Delivery Manager',
            tagline='AI delivery leader turning enterprise AI solutions into live, governed deployments across Southeast Asia and the Middle East.',
            introduction=introduction,
            location='Kuala Lumpur, Malaysia',
            email='reza.robotics65@gmail.com',
            phone='+60 12-703 7145',
            linkedin_url='https://linkedin.com/in/reza-yousefi86',
            years_experience=12,
            open_to_work=True,
            is_published=True,
        ))
        self.stdout.write('Profile seeded.')

    # ------------------------------------------------------------------
    def seed_languages(self):
        defs = [
            ('English', 'PROFESSIONAL', '', 1),
            ('Arabic', 'PROFESSIONAL', '', 2),
            ('Persian', 'NATIVE', '', 3),
            ('Malay', 'CONVERSATIONAL', 'Working-level, acquired in Malaysia', 4),
        ]
        for name, proficiency, notes, order in defs:
            Language.objects.update_or_create(
                name=name, defaults=dict(proficiency=proficiency, notes=notes, order=order),
            )
        self.stdout.write(f'{len(defs)} languages seeded.')

    # ------------------------------------------------------------------
    def seed_experience(self):
        defs = [
            dict(
                company='Byond Asia', title='Technical Project & Business Development Manager',
                location='Selangor, Malaysia', start_date=d(2025, 11), end_date=None, is_current=True,
                order=1,
                summary=(
                    'Leading delivery of AI Digital Human (HoloMe) programmes across Southeast Asia and '
                    'the Middle East, pairing technical delivery ownership with business development for '
                    'new AI solution engagements.'
                ),
                achievements=[
                    dict(text='RM 1.2M enterprise engagement closed', metric_value='RM 1.2M',
                         metric_label='enterprise engagement closed', is_headline=False),
                    dict(text='AI Digital Human (HoloMe) programme delivery spanning multiple regional markets',
                         metric_value='', metric_label='', is_headline=False),
                    dict(text='12+ years of AI and computer vision engineering experience across delivery and technical roles',
                         metric_value='12+ years', metric_label='AI & computer vision engineering', is_headline=True),
                    dict(text='3 AI/ML-focused certifications earned: Microsoft Azure AI Essentials, Machine Learning for Business Intelligence, and Computer Vision with Deep Learning',
                         metric_value='3', metric_label='AI/ML certifications earned', is_headline=True),
                ],
            ),
            dict(
                company='Sena Traffic Systems (ITMAX)', title='Project Manager',
                location='Kuala Lumpur, Malaysia', start_date=d(2022, 1), end_date=d(2025, 11), is_current=False,
                order=2,
                summary='Delivered AI-managed smart traffic systems at city scale, owning programme budget, risk and stakeholder governance.',
                achievements=[
                    dict(text='600+ AI-managed intersections delivered', metric_value='600+',
                         metric_label='AI-managed intersections delivered', is_headline=True),
                    dict(text='60%+ reduction in system incidents', metric_value='60%+',
                         metric_label='reduction in system incidents', is_headline=True),
                    dict(text='95% programme budget adherence', metric_value='95%',
                         metric_label='programme budget adherence', is_headline=False),
                    dict(text='Developed a computer vision-based vehicle classification and tracking system to support real-time traffic monitoring',
                         metric_value='', metric_label='', is_headline=False),
                ],
            ),
            dict(
                company='Ace Resource Advisory Services', title='Assistant Manager, Analytics & Business Insights',
                location='Kuala Lumpur, Malaysia', start_date=d(2021, 1), end_date=d(2022, 1), is_current=False,
                order=3, summary='Led analytics and business insight initiatives supporting client advisory engagements.',
                achievements=[],
            ),
            dict(
                company="N'osairis Technology Solutions",
                title='Software Developer & IoT Solution Consultant & BI Developer',
                location='Kuala Lumpur, Malaysia', start_date=d(2018, 1), end_date=d(2021, 1), is_current=False,
                order=4, summary='Built software, IoT and business intelligence solutions across client engagements.',
                achievements=[],
            ),
            dict(
                company='Sena Traffic Systems', title='R&D Engineer',
                location='Kuala Lumpur, Malaysia', start_date=d(2017, 1), end_date=d(2018, 1), is_current=False,
                order=5, summary='Research and development on intelligent traffic systems.',
                achievements=[],
            ),
            dict(
                company='MMU Centre of Robotics & Automation', title='Research Officer',
                location='Melaka, Malaysia', start_date=d(2015, 1), end_date=d(2017, 1), is_current=False,
                order=6, summary='Applied robotics and automation research.',
                achievements=[],
            ),
            dict(
                company='Cohu (Ismeca)', title='Software Engineer Assistant',
                location='Melaka, Malaysia', start_date=d(2014, 1), end_date=d(2015, 1), is_current=False,
                order=7, summary='Software engineering support for semiconductor test equipment.',
                achievements=[],
            ),
            dict(
                company='iRadar Sdn Bhd', title='Research Assistant',
                location='Melaka, Malaysia', start_date=d(2013, 1), end_date=d(2013, 12), is_current=False,
                order=8, summary='Research assistance on radar signal processing projects.',
                achievements=[],
            ),
        ]

        experiences = {}
        for defn in defs:
            achievements = defn.pop('achievements')
            exp, _ = Experience.objects.update_or_create(
                company=defn['company'], title=defn['title'],
                defaults=dict(is_published=True, **{k: v for k, v in defn.items() if k not in ('company', 'title')}),
            )
            experiences[exp.company] = exp
            for order, achievement in enumerate(achievements, start=1):
                Achievement.objects.update_or_create(
                    experience=exp, order=order,
                    defaults=achievement,
                )
        self.stdout.write(f'{len(defs)} experience entries seeded.')
        return experiences

    # ------------------------------------------------------------------
    def seed_education(self):
        Education.objects.update_or_create(
            institution='Multimedia University', qualification='Bachelor of Electronics Engineering',
            defaults=dict(field_of_study='Robotics & Automation', location='Melaka, Malaysia',
                          year_completed=2015, order=1),
        )
        self.stdout.write('Education seeded.')

    # ------------------------------------------------------------------
    def seed_case_studies(self, experiences):
        byond = experiences.get('Byond Asia')
        sena = experiences.get('Sena Traffic Systems (ITMAX)')

        defs = [
            dict(
                title='Kuala Lumpur smart traffic — 600+ intersections, 60% incident reduction',
                slug='kl-smart-traffic', related_experience=sena, order=1,
                headline_metric='60% fewer incidents across 600+ AI-managed intersections',
                situation='Draft: describe the city-scale traffic management challenge.',
                task='Draft: describe scope owned as Project Manager.',
                action='Draft: describe the AI-managed intersection rollout and governance approach.',
                result='Draft: 600+ intersections delivered, 60%+ incident reduction, 95% budget adherence.',
            ),
            dict(
                title='JCorp / KPJ — RM 1.2M AI solution engagement',
                slug='jcorp-kpj-ai-engagement', related_experience=byond, order=2,
                headline_metric='RM 1.2M enterprise AI engagement closed',
                situation='Draft: describe the client context and opportunity.',
                task='Draft: describe the commercial and delivery objectives.',
                action='Draft: describe the solutioning and delivery approach.',
                result='Draft: RM 1.2M engagement closed and delivered.',
            ),
            dict(
                title='Project & Portfolio Management platform build',
                slug='ppm-platform-build', related_experience=None, order=3,
                headline_metric='',
                situation='Draft: describe the need for a PPM platform.',
                task='Draft: describe the build objectives.',
                action='Draft: describe the platform build approach.',
                result='Draft: outcomes and adoption.',
            ),
            dict(
                title='Cross-regional AI Digital Human (HoloMe) rollout',
                slug='holome-cross-regional-rollout', related_experience=byond, order=4,
                headline_metric='',
                situation='Draft: describe the HoloMe programme context across regions.',
                task='Draft: describe the rollout objectives.',
                action='Draft: describe the cross-regional delivery approach.',
                result='Draft: outcomes across Southeast Asia and the Middle East.',
            ),
            dict(
                title='Vehicle Classification and Tracking System',
                slug='vehicle-classification-tracking-system', related_experience=sena, order=5,
                headline_metric='',
                situation='Draft: describe the traffic-monitoring need this project addressed.',
                task='Draft: describe the scope and objectives of the CV system.',
                action=(
                    'Draft: describe the computer vision approach used for real-time vehicle '
                    'classification and tracking (model/technique, data, deployment).'
                ),
                result='Draft: add real accuracy/scale/throughput figures once available.',
            ),
        ]

        for defn in defs:
            CaseStudy.objects.update_or_create(
                slug=defn.pop('slug'),
                defaults=dict(is_published=False, date_completed=None, **defn),
            )
        self.stdout.write(f'{len(defs)} case study stubs seeded (unpublished).')
