from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.utils.text import slugify
import uuid


User = get_user_model()


class Category(models.Model):
    """Dynamic categories for jobs and training programs"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class GeneralUser(models.Model):
    """Profile for self-enrolled general job seekers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='general_profile')
    phone_number = models.CharField(max_length=20)  # Required
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Payment tracking
    has_paid = models.BooleanField(default=False)
    
    # Resume completeness
    resume_completeness = models.IntegerField(default=0, help_text="Resume completion percentage (0-100)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"General User: {self.user.full_name}"


class ReferredUser(models.Model):
    """Profile for agency-referred court users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referred_profile')
    phone_number = models.CharField(max_length=20)  # Required
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Court information - All required for court-referred users
    court_name = models.CharField(max_length=200)
    case_id = models.CharField(max_length=200)
    
    # Payment tracking
    has_paid = models.BooleanField(default=False)
    
    # Resume completeness
    resume_completeness = models.IntegerField(default=0, help_text="Resume completion percentage (0-100)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Referred User: {self.user.full_name} - {self.case_id}"


class Employer(models.Model):
    """Profile for employer accounts"""
    
    INDUSTRY_CHOICES = [
        ('healthcare', 'Healthcare'),
        ('technology', 'Technology'),
        ('construction', 'Construction'),
        ('retail', 'Retail'),
        ('hospitality', 'Hospitality'),
        ('manufacturing', 'Manufacturing'),
        ('education', 'Education'),
        ('finance', 'Finance'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('banned', 'Banned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    
    company_name = models.CharField(max_length=200)  # Required
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, default='other')
    office_location = models.CharField(max_length=200)  # Required
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Employer: {self.company_name}"



class TrainingProvider(models.Model):
    """Profile for training provider accounts"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('banned', 'Banned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trainer_profile')
    
    specialization = models.CharField(max_length=200)  # Required
    experience = models.CharField(max_length=200, help_text="Years of experience or description")  # Required
    skills = ArrayField(models.CharField(max_length=50))  # Required - must provide at least one skill
    bio = models.TextField()  # Required
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Performance metrics (calculated fields)
    total_learners = models.IntegerField(default=0)
    average_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Trainer: {self.user.full_name} - {self.specialization}"



class Agency(models.Model):
    """Profile for rehabilitation agency accounts"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('banned', 'Banned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agency_profile')
    
    agency_id = models.CharField(max_length=100, unique=True)  # Required
    agency_name = models.CharField(max_length=200)  # Required
    representative_name = models.CharField(max_length=200, default='')  # Optional
    address = models.CharField(max_length=300)  # Required
    
    # Verification documents (stored as Cloudinary URLs or file paths)
    verification_documents = models.JSONField(default=list, blank=True, help_text="URLs to court authorization and registration docs")
    
    # Primary verification document from Cloudinary
    document_public_id = models.CharField(max_length=255, blank=True, default='', help_text="Cloudinary public_id for the verification document")
    document_url = models.URLField(blank=True, default='', help_text="Direct URL to the verification document")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Agency: {self.agency_name}"


# Import all other models to make them available when importing from users.models
from .job_models import Job, JobApplication, Interview
from .training_models import TrainingProgram, Enrollment, Certificate
from .compliance_models import CaseAssignment, ComplianceTimeline, ProgressReport, AuditLog
from .profile_models import CareerQuiz, Resume, WorkExperience, Education, Skill, Document
from .payment_models import Payment, TransactionLog
from .additional_models import SavedJob, ContactMessage, EmployerTrainingLinkage
from .notification_models import Notification


__all__ = [
    'Category',
    'GeneralUser', 'ReferredUser', 'Employer', 'TrainingProvider', 'Agency',
    'Job', 'JobApplication', 'Interview',
    'TrainingProgram', 'Enrollment', 'Certificate',
    'CaseAssignment', 'ComplianceTimeline', 'ProgressReport', 'AuditLog',
    'CareerQuiz', 'Resume', 'WorkExperience', 'Education', 'Skill', 'Document',
    'Payment', 'TransactionLog',
    'SavedJob', 'ContactMessage', 'EmployerTrainingLinkage',
    'Notification',
]