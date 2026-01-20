from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Notification(models.Model):
    """In-app notifications for all user types"""
    
    NOTIFICATION_TYPES = [
        # User (Agency) notifications
        ('training_enrolled', 'Training Enrollment'),
        ('certificate_uploaded', 'Certificate Uploaded'),
        ('certificate_verified', 'Certificate Verified'),
        ('certificate_rejected', 'Certificate Rejected'),
        ('job_applied', 'Job Application Submitted'),
        ('application_interview', 'Interview Scheduled'),
        ('application_hired', 'Application Hired'),
        ('application_rejected', 'Application Rejected'),
        ('welcome', 'Welcome Notification'),
        
        # Trainer notifications
        ('new_enrollment', 'New Training Enrollment'),
        ('certificate_pending', 'Certificate Pending Verification'),
        
        # Employer notifications
        ('new_application', 'New Job Application'),
        
        # Admin notifications
        ('new_trainer_pending', 'New Trainer Pending Approval'),
        ('new_employer_pending', 'New Employer Pending Approval'),
        ('new_agency_pending', 'New Agency Pending Approval'),
        ('referred_user_paid', 'Referred User Completed Payment'),
        ('general_user_paid', 'General User Completed Payment'),
        ('new_job_posted', 'New Job Posted'),
        ('new_training_created', 'New Training Created'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        help_text="User who receives this notification"
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Extra context data (e.g., job_id, training_id, application_id)
    data = models.JSONField(default=dict, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type}: {self.title} -> {self.recipient.email}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
