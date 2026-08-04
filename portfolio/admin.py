from django.contrib import admin

from .models import Achievement, CaseStudy, CoreExpertise, Education, Experience, Language, Profile, TechTool


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 1
    fields = ('text', 'metric_value', 'metric_label', 'is_headline', 'order')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'headline', 'is_published', 'open_to_work', 'updated_at')

    def has_add_permission(self, request):
        return not Profile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'proficiency', 'notes', 'order')
    list_editable = ('proficiency', 'order')
    ordering = ('order',)


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'start_date', 'end_date', 'is_current', 'is_published', 'order')
    list_filter = ('is_current', 'is_published')
    search_fields = ('title', 'company', 'summary')
    list_editable = ('is_published', 'order')
    ordering = ('order',)
    inlines = [AchievementInline]


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('qualification', 'institution', 'year_completed', 'order')
    list_editable = ('order',)
    ordering = ('order',)


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ('title', 'headline_metric', 'is_published', 'date_completed', 'order')
    list_filter = ('is_published',)
    search_fields = ('title', 'situation', 'task', 'action', 'result')
    list_editable = ('is_published', 'order')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('order',)
    autocomplete_fields = ['related_experience']


@admin.register(CoreExpertise)
class CoreExpertiseAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order')
    list_editable = ('icon', 'order')
    ordering = ('order',)


@admin.register(TechTool)
class TechToolAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_key', 'abbreviation', 'order')
    list_editable = ('icon_key', 'abbreviation', 'order')
    ordering = ('order',)
