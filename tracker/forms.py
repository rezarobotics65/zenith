"""
ModelForms backing the in-page editing added to the tracker (Dashboard, KPI &
Timetable, Activity Log). Django admin still works and still has the richest
tooling (bulk actions, autocomplete) — these forms exist so day-to-day
updates don't require a trip to /admin/.
"""
from django import forms

from .models import (
    ActivityLog,
    CareerObjective,
    Certification,
    Course,
    KPI,
    MonthlyCommitment,
    MonthlyPlan,
    Pillar,
    Resume,
    Skill,
    SkillDomain,
)

TEXTAREA_SMALL = forms.Textarea(attrs={'rows': 3})


class CareerObjectiveForm(forms.ModelForm):
    class Meta:
        model = CareerObjective
        fields = [
            'current_title', 'target_title', 'current_salary', 'target_salary',
            'currency', 'start_date', 'target_date', 'notes',
        ]
        widgets = {'notes': TEXTAREA_SMALL}


class SkillDomainForm(forms.ModelForm):
    class Meta:
        model = SkillDomain
        fields = ['code', 'name', 'description', 'priority', 'order']
        widgets = {'description': TEXTAREA_SMALL}


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['domain', 'name', 'current_level', 'target_level', 'baseline_level', 'why_it_matters', 'order']
        widgets = {'why_it_matters': TEXTAREA_SMALL}


class CertificationForm(forms.ModelForm):
    class Meta:
        model = Certification
        fields = [
            'name', 'provider', 'status', 'priority', 'planned_hours',
            'cost_amount', 'cost_currency', 'target_date', 'earned_date',
            'credential_id', 'credential_url', 'domains', 'notes',
            'show_on_portfolio', 'order',
        ]
        widgets = {
            'notes': TEXTAREA_SMALL,
            'domains': forms.CheckboxSelectMultiple,
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'name', 'provider', 'tier', 'status', 'domain', 'certification',
            'planned_hours', 'url', 'is_free', 'start_month', 'target_month',
            'completed_date', 'application_commitment', 'application_done',
            'notes', 'order',
        ]
        widgets = {
            'notes': TEXTAREA_SMALL,
            'application_commitment': TEXTAREA_SMALL,
            'start_month': forms.DateInput(attrs={'type': 'date'}),
            'target_month': forms.DateInput(attrs={'type': 'date'}),
            'completed_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PillarForm(forms.ModelForm):
    class Meta:
        model = Pillar
        fields = ['code', 'name', 'description', 'weight', 'order']
        widgets = {'description': TEXTAREA_SMALL}


class KPIForm(forms.ModelForm):
    class Meta:
        model = KPI
        fields = [
            'pillar', 'code', 'title', 'target', 'verified_by', 'period',
            'period_year', 'period_month', 'status', 'target_value',
            'current_value', 'due_date', 'notes', 'order',
        ]
        widgets = {'notes': TEXTAREA_SMALL}


class MonthlyPlanForm(forms.ModelForm):
    class Meta:
        model = MonthlyPlan
        fields = ['year', 'month', 'theme', 'target_hours', 'status', 'review_notes', 'reviewed_on']
        widgets = {
            'review_notes': TEXTAREA_SMALL,
            'reviewed_on': forms.DateInput(attrs={'type': 'date'}),
        }


class MonthlyCommitmentForm(forms.ModelForm):
    class Meta:
        model = MonthlyCommitment
        fields = ['plan', 'pillar', 'commitment', 'done_when', 'is_complete', 'completed_date', 'order']
        widgets = {
            'commitment': TEXTAREA_SMALL,
            'completed_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ActivityLogForm(forms.ModelForm):
    class Meta:
        model = ActivityLog
        fields = [
            'date', 'activity_type', 'title', 'description', 'hours',
            'course', 'certification', 'kpi', 'skill_domain', 'is_milestone',
        ]
        widgets = {
            'description': TEXTAREA_SMALL,
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class KPIQuickUpdateForm(forms.ModelForm):
    """Minimal form for the Status + Current value cells on the KPI &
    Timetable table — the full KPIForm requires every field, which doesn't
    fit an inline row edit."""
    class Meta:
        model = KPI
        fields = ['status', 'current_value']


class CourseQuickUpdateForm(forms.ModelForm):
    """Minimal form for the Status cell on the KPI & Timetable Courses
    table. Progress itself isn't inline-editable — it's computed from
    logged hours (or forced to 100 by COMPLETE status), not a raw field."""
    class Meta:
        model = Course
        fields = ['status']


class ResumeForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file', 'is_default']
