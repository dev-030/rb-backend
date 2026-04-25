from django.db import models
from django.contrib.auth import get_user_model
from cloudinary.models import CloudinaryField
import uuid


User = get_user_model()


class TrainingProgram(models.Model):
    """Training courses offered by training providers"""
    
    # Removed CATEGORY_CHOICES - now using Category model
    
    DURATION_UNIT_CHOICES = [
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('months', 'Months'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey('users.TrainingProvider', on_delete=models.CASCADE, related_name='programs')
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        'users.Category',
        on_delete=models.SET_NULL,
        null=True,
        related_name='training_programs',
        help_text="Training category - will be set to null if category is deleted"
    )
    
    external_link = models.URLField(help_text="Link to course platform or website")
    duration = models.IntegerField(help_text="Duration value (e.g., 3, 120, 6)")
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT_CHOICES, help_text="Unit of duration")
    
    deadline = models.DateField(null=True, blank=True, help_text="Enrollment or completion deadline")
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.provider.user.full_name}"


class Enrollment(models.Model):
    """Tracks user enrollment in training programs"""
    
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name='enrollments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    progress_percentage = models.IntegerField(default=0, help_text="0-100")
    financial_aid_requested = models.BooleanField(
        default=False,
        help_text="Whether the student requested financial aid at enrollment"
    )
    
    start_date = models.DateField(auto_now_add=True)
    completion_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['program', 'user']  # Prevent duplicate enrollments
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['program', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} -> {self.program.name}"


class Certificate(models.Model):
    """User-uploaded certificates with verification status"""
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='certificates')
    
    certificate_file = CloudinaryField('certificate', folder='certificates/')
    
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending'
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_certificates'
    )
    
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['enrollment', 'verification_status']),
        ]
    
    def __str__(self):
        return f"Certificate for {self.enrollment.user.full_name} - {self.enrollment.program.name}"
