from django.db import models
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField
import uuid


User = get_user_model()


class CareerQuiz(models.Model):
    """Stores career quiz responses and recommendations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='career_quiz')
    
    # Quiz responses stored as JSON
    responses = models.JSONField(default=dict, help_text="Quiz question-answer pairs")
    
    # Recommended career path based on quiz
    recommended_career = models.CharField(max_length=100, blank=True)
    recommended_industry = models.CharField(max_length=100, blank=True)
    
    # Preferences extracted from quiz
    work_environment_preference = models.CharField(max_length=50, blank=True)  # e.g., "office", "remote", "outdoor"
    time_commitment = models.CharField(max_length=50, blank=True)  # e.g., "full_time", "part_time"
    
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Career Quiz"
        verbose_name_plural = "Career Quizzes"
    
    def __str__(self):
        return f"Career Quiz: {self.user.full_name}"


class Resume(models.Model):
    """Structured resume for job seekers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resume')
    
    # Professional summary
    summary = models.TextField(blank=True)
    
    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    
    # Resume PDF URL (Cloudinary)
    resume_pdf_url = models.URLField(blank=True, help_text="Cloudinary URL of resume PDF")
    
    # AI Analysis Results (stored as JSON)
    section_status_data = models.JSONField(default=dict, blank=True, help_text="AI's section completeness assessment")
    ai_suggestions = models.JSONField(default=list, blank=True, help_text="AI's suggestions")
    
    # Completeness tracking
    completeness_percentage = models.IntegerField(default=0, help_text="0-100")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Resume"
        verbose_name_plural = "Resumes"
    
    def __str__(self):
        return f"Resume: {self.user.full_name}"


class WorkExperience(models.Model):
    """Job history entries"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='work_experiences')
    
    job_title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if current position")
    is_current = models.BooleanField(default=False)
    
    description = models.TextField(blank=True, help_text="Job responsibilities and achievements")
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Work Experience"
        verbose_name_plural = "Work Experiences"
    
    def __str__(self):
        return f"{self.job_title} at {self.company_name}"


class Education(models.Model):
    """Academic credentials"""
    
    DEGREE_CHOICES = [
        ('high_school', 'High School Diploma'),
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor\'s Degree'),
        ('master', 'Master\'s Degree'),
        ('doctorate', 'Doctorate'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='education_entries')
    
    institution_name = models.CharField(max_length=200)
    degree = models.CharField(max_length=50, choices=DEGREE_CHOICES)
    field_of_study = models.CharField(max_length=200, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Education"
        verbose_name_plural = "Education Entries"
    
    def __str__(self):
        return f"{self.degree} in {self.field_of_study} from {self.institution_name}"


class Skill(models.Model):
    """User skills with proficiency levels"""
    
    PROFICIENCY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skills')
    
    skill_name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_CHOICES, default='intermediate')
    
    class Meta:
        unique_together = ['resume', 'skill_name']
        ordering = ['skill_name']
    
    def __str__(self):
        return f"{self.skill_name} ({self.proficiency})"


class Document(models.Model):
    """Manages uploaded files (resumes, certificates, court documents)"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('resume_pdf', 'Resume PDF'),
        ('certificate', 'Certificate'),
        ('court_document', 'Court Document'),
        ('identification', 'Identification Document'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = CloudinaryField('document', folder='documents/')
    
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # For agency-uploaded documents
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='uploaded_documents'
    )
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'document_type']),
        ]
    
    def __str__(self):
        return f"{self.document_type}: {self.filename}"
