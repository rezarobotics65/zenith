from django.http import FileResponse
from django.shortcuts import get_object_or_404, render

# Cross-app queries and writes: the Skills/Certifications sections read tracker
# data (BUILD_BRIEF.md Section 6.1), and download_cv() below logs a CVDownloadLog
# row when a visitor downloads the CV. These are the deliberate exceptions to
# "portfolio must never import from tracker" (Section 4) — no portfolio *model*
# depends on tracker, and tracker never imports portfolio.
import logging

from tracker import geoip
from tracker.middleware import get_client_ip, parse_user_agent
from tracker.models import CVDownloadLog, Certification, Resume, SkillDomain

from .forms import CVDownloadRequestForm
from .models import Achievement, CaseStudy, CoreExpertise, Education, Experience, Language, Profile, TechTool

logger = logging.getLogger(__name__)


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

    core_expertise = CoreExpertise.objects.all().order_by('order')

    tech_tools = TechTool.objects.all().order_by('order')

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
        'core_expertise': core_expertise,
        'tech_tools': tech_tools,
        'has_cv': Resume.objects.filter(is_default=True).exists(),
    }
    return render(request, 'portfolio/home.html', context)


def case_study_detail(request, slug):
    case_study = get_object_or_404(CaseStudy, slug=slug, is_published=True)
    profile = Profile.objects.filter(pk=1, is_published=True).first()
    context = {'case_study': case_study, 'profile': profile}
    return render(request, 'portfolio/case_study_detail.html', context)


def download_cv(request):
    """Gated CV download. Visitors fill in name/organization/email before the
    file is served — the form re-renders with errors on invalid input rather
    than downloading. Always serves whichever tracker.Resume is marked
    default (the tracker's CV manager), never profile.cv_file, which this
    supersedes as the source of the public download.

    The portfolio's "Download CV" links point here (with a ?src= tag
    identifying which button was clicked) instead of straight at a media
    URL, so the request actually passes through Django and can be gated/
    logged — a direct media URL is served by nginx/WhiteNoise in production
    and Django never sees it at all."""
    profile = Profile.objects.filter(pk=1, is_published=True).first()
    resume = Resume.objects.filter(is_default=True).first()
    if not resume:
        return render(request, 'portfolio/download_cv.html', {'resume_available': False, 'profile': profile})

    src = (request.POST.get('src') or request.GET.get('src') or 'unknown')[:100]

    if request.method == 'POST':
        form = CVDownloadRequestForm(request.POST)
        if form.is_valid():
            try:
                ip_address = get_client_ip(request)
                ua_info = parse_user_agent(request.META.get('HTTP_USER_AGENT', ''))
                geo = geoip.lookup(ip_address) if ip_address else geoip.EMPTY_RESULT
                CVDownloadLog.objects.create(
                    visitor_ip=ip_address or '0.0.0.0',
                    visitor_name=form.cleaned_data['name'],
                    organization=form.cleaned_data['organization'],
                    email=form.cleaned_data['email'],
                    country=geo['country'],
                    region=geo['region'],
                    city=geo['city'],
                    browser=ua_info['browser'],
                    device=ua_info['device'],
                    cv_version=resume.filename,
                    download_source=src,
                )
            except Exception:
                logger.warning('CV download tracking failed', exc_info=True)  # never blocks the actual download

            return FileResponse(resume.file.open('rb'), as_attachment=True, filename=resume.filename)
    else:
        form = CVDownloadRequestForm()

    return render(request, 'portfolio/download_cv.html', {
        'form': form, 'src': src, 'resume_available': True, 'profile': profile,
    })


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)
