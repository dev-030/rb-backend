from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid


User = get_user_model()


class Job(models.Model):
    """Job posting created by employers"""
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('temporary', 'Temporary'),
    ]
    
    JOB_STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('draft', 'Draft'),
    ]
    
    
    # Removed CATEGORY_CHOICES - now using Category model
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey('users.Employer', on_delete=models.CASCADE, related_name='jobs')
    
    title = models.CharField(max_length=200)
    category = models.ForeignKey(
        'users.Category',
        on_delete=models.SET_NULL,
        null=True,
        related_name='jobs',
        help_text="Job category - will be set to null if category is deleted"
    )
    description = models.TextField()
    requirements = models.TextField()
    
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    location = models.CharField(max_length=200)
    is_remote = models.BooleanField(default=False)
    
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    skills_required = models.JSONField(default=list, blank=True)  # List of skill strings
    number_of_openings = models.IntegerField(null=True, blank=True, help_text="Number of positions available")
    
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=JOB_STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['employer', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.employer.company_name}"


class JobApplication(models.Model):
    """Job application submitted by job seekers"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('offer_received', 'Offer Received'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    cover_letter = models.TextField(blank=True)
    
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Employer notes
    employer_notes = models.TextField(blank=True)
    
    # Hired Details
    hired_date = models.DateField(null=True, blank=True)
    hired_time = models.TimeField(null=True, blank=True)
    hired_location = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job', 'applicant']  # Prevent duplicate applications
        indexes = [
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['job', 'status']),
        ]
    
    def __str__(self):
        return f"{self.applicant.full_name} -> {self.job.title}"


class Interview(models.Model):
    """Interview scheduled between employer and applicant"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name='interviews')
    
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    duration_minutes = models.IntegerField(default=30)
    
    meeting_link = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
    
    def __str__(self):
        return f"Interview: {self.application.applicant.full_name} for {self.application.job.title}"
