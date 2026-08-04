from datetime import date

from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.urls import reverse


class CareerObjective(models.Model):
    """Singleton record describing the overall career move being tracked."""

    current_title = models.CharField(max_length=160)
    target_title = models.CharField(max_length=160)
    current_salary = models.DecimalField(max_digits=10, decimal_places=2)
    target_salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default='RM')
    start_date = models.DateField()
    target_date = models.DateField()
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Career objective'
        verbose_name_plural = 'Career objective'

    def __str__(self):
        return f'{self.current_title} → {self.target_title}'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'current_title': '',
            'target_title': '',
            'current_salary': 0,
            'target_salary': 0,
            'start_date': date.today(),
            'target_date': date.today(),
        })
        return obj

    @property
    def days_remaining(self):
        return (self.target_date - date.today()).days


class Priority(models.TextChoices):
    HIGHEST = 'HIGHEST', 'Highest'
    HIGH = 'HIGH', 'High'
    MEDIUM = 'MEDIUM', 'Medium'
    LOW = 'LOW', 'Low'


class SkillDomain(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices)
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.code} — {self.name}'

    @property
    def avg_current_level(self):
        return self.skills.aggregate(v=models.Avg('current_level'))['v'] or 0

    @property
    def avg_target_level(self):
        return self.skills.aggregate(v=models.Avg('target_level'))['v'] or 0

    @property
    def progress_pct(self):
        """How far current level has closed the gap to target, since baseline. 0-100."""
        skills = list(self.skills.all())
        if not skills:
            return 0
        total_gap = sum((s.target_level - s.baseline_level) for s in skills)
        total_closed = sum((s.current_level - s.baseline_level) for s in skills)
        if total_gap <= 0:
            return 100
        pct = (total_closed / total_gap) * 100
        return max(0, min(100, round(pct)))


class Skill(models.Model):
    domain = models.ForeignKey(SkillDomain, related_name='skills', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    current_level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    target_level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    baseline_level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    why_it_matters = models.TextField(blank=True)
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    @property
    def gap(self):
        delta = self.target_level - self.current_level
        if delta <= 0:
            return 'NONE'
        if delta == 1:
            return 'MODERATE'
        if delta == 2:
            return 'LARGE'
        return 'CRITICAL'


class Certification(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Planned'
        STUDYING = 'STUDYING', 'Studying'
        BOOKED = 'BOOKED', 'Booked'
        EARNED = 'EARNED', 'Earned'
        DEFERRED = 'DEFERRED', 'Deferred'
        ABANDONED = 'ABANDONED', 'Abandoned'

    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED)
    priority = models.PositiveSmallIntegerField(default=1)
    planned_hours = models.PositiveIntegerField(default=0)
    cost_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cost_currency = models.CharField(max_length=8, default='USD')
    target_date = models.DateField(null=True, blank=True)
    earned_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=120, blank=True)
    credential_url = models.URLField(blank=True)
    domains = models.ManyToManyField(SkillDomain, blank=True, related_name='certifications')
    notes = models.TextField(blank=True)
    show_on_portfolio = models.BooleanField(default=True)
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'priority']

    def __str__(self):
        return self.name

    @property
    def hours_logged(self):
        return self.activities.aggregate(v=Sum('hours'))['v'] or 0

    @property
    def progress_pct(self):
        if self.status == self.Status.EARNED:
            return 100
        if not self.planned_hours:
            return 0
        pct = (float(self.hours_logged) / self.planned_hours) * 100
        return max(0, min(100, round(pct)))


class Pillar(models.Model):
    code = models.CharField(max_length=1, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    weight = models.PositiveSmallIntegerField(help_text='Percent weight, all pillars must total 100')
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.code} — {self.name}'


class Course(models.Model):
    class Tier(models.TextChoices):
        CERTIFICATION = 'CERTIFICATION', 'Certification'
        TECHNICAL = 'TECHNICAL', 'Technical'
        LEADERSHIP = 'LEADERSHIP', 'Leadership'

    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not started'
        IN_PROGRESS = 'IN_PROGRESS', 'In progress'
        COMPLETE = 'COMPLETE', 'Complete'
        DROPPED = 'DROPPED', 'Dropped'

    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=120)
    tier = models.CharField(max_length=14, choices=Tier.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NOT_STARTED)
    domain = models.ForeignKey(SkillDomain, null=True, blank=True, on_delete=models.SET_NULL, related_name='courses')
    certification = models.ForeignKey(
        Certification, null=True, blank=True, on_delete=models.SET_NULL, related_name='courses',
    )
    planned_hours = models.PositiveIntegerField(default=0)
    url = models.URLField(blank=True)
    is_free = models.BooleanField(default=True, help_text='Covered by Coursera Plus / LinkedIn Learning')
    start_month = models.DateField(null=True, blank=True, help_text='Use the 1st of the month')
    target_month = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    application_commitment = models.TextField(blank=True, help_text='The "use it at work" pairing')
    application_done = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['tier', 'order']

    def __str__(self):
        return self.name

    @property
    def hours_logged(self):
        return self.activities.aggregate(v=Sum('hours'))['v'] or 0

    @property
    def progress_pct(self):
        if self.status == self.Status.COMPLETE:
            return 100
        if not self.planned_hours:
            return 0
        pct = (float(self.hours_logged) / self.planned_hours) * 100
        return max(0, min(100, round(pct)))


class KPI(models.Model):
    class Period(models.TextChoices):
        YEARLY = 'YEARLY', 'Yearly'
        MONTHLY = 'MONTHLY', 'Monthly'

    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not started'
        ON_TRACK = 'ON_TRACK', 'On track'
        AT_RISK = 'AT_RISK', 'At risk'
        BEHIND = 'BEHIND', 'Behind'
        COMPLETE = 'COMPLETE', 'Complete'

    pillar = models.ForeignKey(Pillar, related_name='kpis', on_delete=models.PROTECT)
    code = models.CharField(max_length=10, help_text='A1, B3, C2...')
    title = models.CharField(max_length=300)
    target = models.CharField(max_length=200)
    verified_by = models.CharField(max_length=200, blank=True)
    period = models.CharField(max_length=7, choices=Period.choices)
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NOT_STARTED)
    target_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['pillar__order', 'order']
        verbose_name = 'KPI'
        verbose_name_plural = 'KPIs'

    def __str__(self):
        return f'{self.code} — {self.title}'

    @property
    def rag(self):
        mapping = {
            self.Status.COMPLETE: 'GREEN',
            self.Status.ON_TRACK: 'GREEN',
            self.Status.AT_RISK: 'AMBER',
            self.Status.BEHIND: 'RED',
            self.Status.NOT_STARTED: 'RED',
        }
        return mapping.get(self.status, 'RED')

    @property
    def progress_pct(self):
        if self.target_value is not None and self.current_value is not None and self.target_value > 0:
            pct = (float(self.current_value) / float(self.target_value)) * 100
            return max(0, min(100, round(pct)))
        status_map = {
            self.Status.NOT_STARTED: 0,
            self.Status.AT_RISK: 25,
            self.Status.BEHIND: 25,
            self.Status.ON_TRACK: 60,
            self.Status.COMPLETE: 100,
        }
        return status_map.get(self.status, 0)


class MonthlyPlan(models.Model):
    class Status(models.TextChoices):
        PLANNED = 'PLANNED', 'Planned'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETE = 'COMPLETE', 'Complete'
        SLIPPED = 'SLIPPED', 'Slipped'

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    theme = models.CharField(max_length=200, help_text='"Foundations", "First certification"')
    target_hours = models.PositiveIntegerField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PLANNED)
    review_notes = models.TextField(blank=True)
    reviewed_on = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['year', 'month']
        unique_together = ('year', 'month')

    def __str__(self):
        return f'{self.year}-{self.month:02d} — {self.theme}'

    @property
    def period_date(self):
        return date(self.year, self.month, 1)

    @property
    def actual_hours(self):
        return ActivityLog.objects.filter(
            date__year=self.year, date__month=self.month,
        ).aggregate(v=Sum('hours'))['v'] or 0

    @property
    def hours_variance_pct(self):
        if not self.target_hours:
            return 0
        pct = ((float(self.actual_hours) - self.target_hours) / self.target_hours) * 100
        return round(pct)


class MonthlyCommitment(models.Model):
    plan = models.ForeignKey(MonthlyPlan, related_name='commitments', on_delete=models.CASCADE)
    pillar = models.ForeignKey(Pillar, on_delete=models.PROTECT)
    commitment = models.TextField()
    done_when = models.CharField(max_length=300)
    is_complete = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['plan__year', 'plan__month', 'order']

    def __str__(self):
        return self.commitment[:60]


class ActivityLog(models.Model):
    class ActivityType(models.TextChoices):
        STUDY = 'STUDY', 'Study'
        EXAM = 'EXAM', 'Exam'
        APPLICATION = 'APPLICATION', 'Application'
        PRACTICE = 'PRACTICE', 'Practice'
        WORK_APPLICATION = 'WORK_APPLICATION', 'Work application'
        NETWORKING = 'NETWORKING', 'Networking'
        CONTENT = 'CONTENT', 'Content'
        INTERVIEW = 'INTERVIEW', 'Interview'
        REVIEW = 'REVIEW', 'Review'
        MILESTONE = 'MILESTONE', 'Milestone'
        OTHER = 'OTHER', 'Other'

    date = models.DateField(default=date.today, db_index=True)
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities')
    certification = models.ForeignKey(
        Certification, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities',
    )
    kpi = models.ForeignKey(KPI, null=True, blank=True, on_delete=models.SET_NULL, related_name='activities')
    skill_domain = models.ForeignKey(SkillDomain, null=True, blank=True, on_delete=models.SET_NULL)
    is_milestone = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.date} — {self.title}'


class Resume(models.Model):
    """A CV/resume file, versioned. Exactly one may be marked default at a
    time — enforced in save(), not just in the form, so it holds regardless
    of whether the record was created via the tracker UI or admin."""

    file = models.FileField(
        upload_to='resumes/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])],
    )
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.filename

    @property
    def filename(self):
        return self.file.name.rsplit('/', 1)[-1] if self.file else ''

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Resume.objects.exclude(pk=self.pk).update(is_default=False)
