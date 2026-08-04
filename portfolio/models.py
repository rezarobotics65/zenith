from django.db import models
from django.urls import reverse


class Profile(models.Model):
    """Singleton profile record. Always saved to pk=1."""

    full_name = models.CharField(max_length=120)
    headline = models.CharField(max_length=160, help_text='e.g. "AI Solutions Delivery Manager"')
    tagline = models.CharField(max_length=240, help_text='One-line positioning statement')
    introduction = models.TextField(help_text='2-3 paragraph introduction')
    location = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    photo = models.ImageField(upload_to='profile/', blank=True)
    cv_file = models.FileField(upload_to='cv/', blank=True)
    years_experience = models.PositiveIntegerField()
    open_to_work = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profile'

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'full_name': '',
            'headline': '',
            'tagline': '',
            'introduction': '',
            'location': '',
            'email': '',
            'phone': '',
            'years_experience': 0,
        })
        return obj


class Language(models.Model):
    class Proficiency(models.TextChoices):
        NATIVE = 'NATIVE', 'Native'
        FLUENT = 'FLUENT', 'Fluent'
        PROFESSIONAL = 'PROFESSIONAL', 'Professional'
        CONVERSATIONAL = 'CONVERSATIONAL', 'Conversational'
        BASIC = 'BASIC', 'Basic'

    name = models.CharField(max_length=60)
    proficiency = models.CharField(max_length=20, choices=Proficiency.choices)
    notes = models.CharField(max_length=160, blank=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_proficiency_display()})'


class Experience(models.Model):
    company = models.CharField(max_length=160)
    title = models.CharField(max_length=160)
    location = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    summary = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-start_date']

    def __str__(self):
        return f'{self.title} @ {self.company}'

    @property
    def duration_display(self):
        start = self.start_date.strftime('%b %Y') if self.start_date else ''
        if self.is_current or not self.end_date:
            end = 'Present'
        else:
            end = self.end_date.strftime('%b %Y')
        return f'{start} – {end}'


class Achievement(models.Model):
    experience = models.ForeignKey(Experience, related_name='achievements', on_delete=models.CASCADE)
    text = models.TextField()
    metric_value = models.CharField(max_length=40, blank=True, help_text='"60%", "RM 1.2M", "600+"')
    metric_label = models.CharField(max_length=80, blank=True, help_text='"incident reduction"')
    is_headline = models.BooleanField(default=False, help_text='Surface on portfolio hero')
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text[:60]


class Education(models.Model):
    institution = models.CharField(max_length=160)
    qualification = models.CharField(max_length=160)
    field_of_study = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=120, blank=True)
    year_completed = models.PositiveIntegerField()
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-year_completed']
        verbose_name_plural = 'Education'

    def __str__(self):
        return f'{self.qualification}, {self.institution}'


class CaseStudy(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    situation = models.TextField()
    task = models.TextField()
    action = models.TextField()
    result = models.TextField()
    headline_metric = models.CharField(max_length=80, blank=True, help_text='"60% fewer incidents"')
    cover_image = models.ImageField(upload_to='case-studies/', blank=True)
    tech_tags = models.CharField(max_length=200, blank=True, help_text='Comma-separated, e.g. "Python, OpenCV, AWS"')
    related_experience = models.ForeignKey(
        Experience, null=True, blank=True, on_delete=models.SET_NULL, related_name='case_studies',
    )
    date_completed = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-date_completed']
        verbose_name_plural = 'Case studies'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('portfolio:case_study_detail', kwargs={'slug': self.slug})

    AI_KEYWORDS = (
        'ai', 'artificial intelligence', 'machine learning', 'generative',
        'agentic', 'llm', 'computer vision', 'deep learning', 'holome', 'digital human',
    )

    @property
    def is_ai_related(self):
        """Heuristic used for the portfolio's small "AI" tag (Section 8, BUILD_BRIEF.md)."""
        text = ' '.join([self.title, self.situation, self.task, self.action, self.result]).lower()
        return any(keyword in text for keyword in self.AI_KEYWORDS)

    @property
    def tech_tag_list(self):
        return [t.strip() for t in self.tech_tags.split(',') if t.strip()]


class CoreExpertise(models.Model):
    """A short, curated list of current specialisms for the portfolio hero's
    "Core Expertise" grid — distinct from tracker.SkillDomain, which tracks
    aspirational roadmap progress rather than proven current expertise."""

    class Icon(models.TextChoices):
        AI_DELIVERY = 'AI_DELIVERY', 'AI Delivery'
        SMART_SYSTEMS = 'SMART_SYSTEMS', 'Smart Systems'
        COMPUTER_VISION = 'COMPUTER_VISION', 'Computer Vision'
        IOT_ROBOTICS = 'IOT_ROBOTICS', 'IoT & Robotics'
        DATA_ANALYTICS = 'DATA_ANALYTICS', 'Data Analytics'
        LEADERSHIP = 'LEADERSHIP', 'Leadership'
        CLOUD = 'CLOUD', 'Cloud'
        GOVERNANCE = 'GOVERNANCE', 'Governance'
        MACHINE_LEARNING = 'MACHINE_LEARNING', 'Machine Learning'
        DIGITAL_HUMAN = 'DIGITAL_HUMAN', 'Digital Human'
        RAG = 'RAG', 'RAG'
        PROJECT_MANAGEMENT = 'PROJECT_MANAGEMENT', 'Project Management'
        ENTERPRISE_AI = 'ENTERPRISE_AI', 'Enterprise AI'

    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=20, choices=Icon.choices, default=Icon.AI_DELIVERY)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Core expertise'

    def __str__(self):
        return self.name


class TechTool(models.Model):
    """An entry in the portfolio's "Tools & Technologies" grid. Shows an
    uploaded logo if present (upload the vendor's real logo file for a
    pixel-perfect brand icon — no external icon library is permitted in this
    stack, so a CDN icon font isn't an option); otherwise falls back to a
    hand-drawn stand-in icon selected from icon_key, and to the abbreviation
    text if even that has no match."""

    class IconKey(models.TextChoices):
        PYTHON = 'PYTHON', 'Python'
        FASTAPI = 'FASTAPI', 'FastAPI'
        REACT = 'REACT', 'React'
        TENSORFLOW = 'TENSORFLOW', 'TensorFlow'
        PYTORCH = 'PYTORCH', 'PyTorch'
        OPENCV = 'OPENCV', 'OpenCV'
        LANGCHAIN = 'LANGCHAIN', 'LangChain'
        OPENAI = 'OPENAI', 'OpenAI'
        CHROMADB = 'CHROMADB', 'ChromaDB'
        AWS = 'AWS', 'AWS'
        AZURE = 'AZURE', 'Azure'
        DOCKER = 'DOCKER', 'Docker'
        POSTGRESQL = 'POSTGRESQL', 'PostgreSQL'
        MONGODB = 'MONGODB', 'MongoDB'
        GIT = 'GIT', 'Git'
        LINUX = 'LINUX', 'Linux'
        GENERIC = 'GENERIC', 'Generic'

    name = models.CharField(max_length=60)
    abbreviation = models.CharField(max_length=6, help_text='Fallback label if no icon matches, e.g. "Py", "AWS"')
    icon_key = models.CharField(max_length=20, choices=IconKey.choices, default=IconKey.GENERIC)
    icon = models.ImageField(upload_to='tools/', blank=True, help_text="Optional — upload the vendor's real logo for a pixel-perfect icon")
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Tools & technologies'

    def __str__(self):
        return self.name
