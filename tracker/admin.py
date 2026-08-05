from django.contrib import admin

from .models import (
    ActivityLog,
    CareerObjective,
    Certification,
    Course,
    CVDownloadLog,
    KPI,
    MonthlyCommitment,
    MonthlyPlan,
    Pillar,
    Resume,
    Skill,
    SkillDomain,
    VisitorLog,
)


@admin.action(description='Mark selected as complete')
def mark_complete(modeladmin, request, queryset):
    if modeladmin.model is Course:
        queryset.update(status=Course.Status.COMPLETE)
    elif modeladmin.model is KPI:
        queryset.update(status=KPI.Status.COMPLETE)
    elif modeladmin.model is MonthlyCommitment:
        from django.utils import timezone
        queryset.update(is_complete=True, completed_date=timezone.localdate())


@admin.register(CareerObjective)
class CareerObjectiveAdmin(admin.ModelAdmin):
    list_display = ('current_title', 'target_title', 'current_salary', 'target_salary', 'target_date')

    def has_add_permission(self, request):
        return not CareerObjective.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ('name', 'current_level', 'target_level', 'baseline_level', 'order')


@admin.register(SkillDomain)
class SkillDomainAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'priority', 'avg_current_level', 'avg_target_level', 'progress_pct', 'order')
    list_editable = ('priority', 'order')
    search_fields = ('code', 'name')
    ordering = ('order',)
    inlines = [SkillInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'current_level', 'target_level', 'gap', 'order')
    list_filter = ('domain',)
    search_fields = ('name',)
    list_editable = ('current_level', 'target_level', 'order')
    ordering = ('domain__order', 'order')


class CourseInline(admin.TabularInline):
    model = Course
    extra = 0
    fields = ('name', 'status', 'planned_hours', 'target_month', 'order')
    fk_name = 'certification'


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'provider', 'status', 'priority', 'target_date', 'earned_date',
        'progress_pct', 'show_on_portfolio', 'order',
    )
    list_filter = ('status', 'show_on_portfolio', 'domains')
    search_fields = ('name', 'provider', 'credential_id')
    list_editable = ('status', 'priority', 'show_on_portfolio', 'order')
    ordering = ('order',)
    filter_horizontal = ('domains',)
    inlines = [CourseInline]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'provider', 'tier', 'status', 'domain', 'certification',
        'planned_hours', 'hours_logged', 'progress_pct', 'application_done', 'order',
    )
    list_filter = ('tier', 'status', 'domain', 'is_free')
    search_fields = ('name', 'provider')
    list_editable = ('status', 'application_done', 'order')
    ordering = ('tier', 'order')
    autocomplete_fields = ['certification']
    actions = [mark_complete]


@admin.register(Pillar)
class PillarAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'weight', 'order')
    list_editable = ('weight', 'order')
    ordering = ('order',)
    search_fields = ('code', 'name')


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'title', 'pillar', 'period', 'period_year', 'period_month',
        'status', 'rag', 'progress_pct', 'due_date', 'order',
    )
    list_filter = ('pillar', 'period', 'status', 'period_year')
    search_fields = ('code', 'title', 'target')
    list_editable = ('status', 'order')
    ordering = ('pillar__order', 'order')
    actions = [mark_complete]


class MonthlyCommitmentInline(admin.TabularInline):
    model = MonthlyCommitment
    extra = 1
    fields = ('pillar', 'commitment', 'done_when', 'is_complete', 'completed_date', 'order')


@admin.register(MonthlyPlan)
class MonthlyPlanAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'theme', 'target_hours', 'actual_hours', 'status', 'reviewed_on')
    list_filter = ('status', 'year')
    list_editable = ('status',)
    ordering = ('year', 'month')
    inlines = [MonthlyCommitmentInline]


@admin.register(MonthlyCommitment)
class MonthlyCommitmentAdmin(admin.ModelAdmin):
    list_display = ('short_commitment', 'plan', 'pillar', 'is_complete', 'completed_date', 'order')
    list_filter = ('pillar', 'is_complete', 'plan')
    search_fields = ('commitment', 'done_when')
    list_editable = ('is_complete', 'order')
    ordering = ('plan__year', 'plan__month', 'order')
    actions = [mark_complete]

    @admin.display(description='Commitment')
    def short_commitment(self, obj):
        return obj.commitment[:70] + ('…' if len(obj.commitment) > 70 else '')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'title', 'activity_type', 'hours', 'course', 'certification', 'kpi', 'is_milestone')
    list_filter = ('activity_type', 'is_milestone', 'skill_domain')
    search_fields = ('title', 'description')
    date_hierarchy = 'date'
    autocomplete_fields = ['course', 'certification', 'kpi']
    ordering = ('-date', '-created_at')

    def get_changeform_initial_data(self, request):
        from django.utils import timezone
        return {'date': timezone.localdate()}


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('filename', 'is_default', 'created_at')
    list_editable = ('is_default',)
    ordering = ('-created_at',)


class ReadOnlyLogAdmin(admin.ModelAdmin):
    """Base for auto-generated log tables — viewable/searchable/filterable in
    admin for spot-checks, but never manually created or edited there."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(VisitorLog)
class VisitorLogAdmin(ReadOnlyLogAdmin):
    list_display = ('visit_time', 'ip_address', 'country', 'city', 'device', 'referral_source', 'landing_page')
    list_filter = ('device', 'referral_source', 'country')
    search_fields = ('ip_address', 'country', 'region', 'city', 'landing_page')
    date_hierarchy = 'visit_time'
    ordering = ('-visit_time',)


@admin.register(CVDownloadLog)
class CVDownloadLogAdmin(ReadOnlyLogAdmin):
    list_display = ('download_time', 'visitor_name', 'organization', 'email', 'country', 'city', 'device', 'download_source')
    list_filter = ('device', 'country')
    search_fields = ('visitor_name', 'organization', 'email', 'visitor_ip', 'country', 'region', 'city', 'cv_version')
    date_hierarchy = 'download_time'
    ordering = ('-download_time',)
