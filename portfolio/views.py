from django.shortcuts import get_object_or_404, render

# Read-only cross-app query: the Skills and Certifications sections of the public
# portfolio (BUILD_BRIEF.md Section 6.1) surface data owned by the tracker app's
# models. This view module is the single, intentional exception to "portfolio must
# never import from tracker" (Section 4) — no portfolio *model* depends on tracker,
# and tracker never imports portfolio.
from tracker.models import Certification, SkillDomain

from .models import Achievement, CaseStudy, Education, Experience, Language, Profile


def home(request):
    profile = Profile.objects.filter(pk=1, is_published=True).first()

    headline_achievements = Achievement.objects.filter(
        is_headline=True,
        experience__is_published=True,
    ).select_related('experience').order_by('order')[:4]

    domains = SkillDomain.objects.prefetch_related('skills').order_by('order')

    certifications = Certification.objects.filter(
        show_on_portfolio=True,
    ).prefetch_related('domains').order_by('order')

    experiences = Experience.objects.filter(
        is_published=True,
    ).prefetch_related('achievements').order_by('order')

    case_studies = CaseStudy.objects.filter(is_published=True).order_by('order')

    education = Education.objects.all().order_by('order')

    languages = Language.objects.all().order_by('order')

    radar_rows = [
        {'label': d.name, 'code': d.code, 'current': round(d.avg_current_level, 1), 'target': round(d.avg_target_level, 1)}
        for d in domains
    ]
    radar_data = {
        'labels': [r['label'] for r in radar_rows],
        'domain_codes': [r['code'] for r in radar_rows],
        'current': [r['current'] for r in radar_rows],
        'target': [r['target'] for r in radar_rows],
    }

    context = {
        'profile': profile,
        'headline_achievements': headline_achievements,
        'domains': domains,
        'certifications': certifications,
        'experiences': experiences,
        'case_studies': case_studies,
        'education': education,
        'languages': languages,
        'radar_data': radar_data,
    }
    return render(request, 'portfolio/home.html', context)


def case_study_detail(request, slug):
    case_study = get_object_or_404(CaseStudy, slug=slug, is_published=True)
    context = {'case_study': case_study}
    return render(request, 'portfolio/case_study_detail.html', context)


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)
