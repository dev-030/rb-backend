from django.db import models
from django.contrib.auth import get_user_model
import uuid


User = get_user_model()


class SavedJob(models.Model):
    """Jobs saved/bookmarked by users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='saved_by_users')
    
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'job']
        ordering = ['-saved_at']
        indexes = [
            models.Index(fields=['user', '-saved_at']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} saved {self.job.title}"


class ContactMessage(models.Model):
    """Contact us form submissions"""
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='contact_messages')
    
    # For non-logged-in users
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    subject = models.CharField(max_length=300, blank=True)
    message = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    admin_response = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        sender = self.user.full_name if self.user else self.name
        return f"Contact from {sender}: {self.subject}"


class EmployerTrainingLinkage(models.Model):
    """Links employers with training providers for potential hiring"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey('Employer', on_delete=models.CASCADE, related_name='training_linkages')
    training_provider = models.ForeignKey('TrainingProvider', on_delete=models.CASCADE, related_name='employer_linkages')
    training_program = models.ForeignKey('TrainingProgram', on_delete=models.CASCADE, related_name='employer_linkages')
    
    roles_hiring = models.CharField(max_length=300, help_text="Comma-separated roles")
    salary_range = models.CharField(max_length=100, blank=True)
    active_listings = models.IntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employer.company_name} <-> {self.training_provider.user.full_name}"
