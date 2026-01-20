from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid


User = get_user_model()


class CaseAssignment(models.Model):
    """Links court-referred users to agencies for compliance monitoring"""
    
    COMPLIANCE_STATUS_CHOICES = [
        ('on_track', 'On Track'),
        ('delayed', 'Delayed'),
        ('non_compliant', 'Non-Compliant'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referred_user = models.ForeignKey('users.ReferredUser', on_delete=models.CASCADE, related_name='case_assignments')
    agency = models.ForeignKey('users.Agency', on_delete=models.CASCADE, related_name='assigned_cases')
    
    case_id = models.CharField(max_length=100, unique=True, help_text="Unique case identifier assigned by agency")
    
    assigned_date = models.DateField(auto_now_add=True)
    court_date = models.DateField(null=True, blank=True)
    
    compliance_status = models.CharField(
        max_length=20, 
        choices=COMPLIANCE_STATUS_CHOICES, 
        default='on_track'
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-assigned_date']
        indexes = [
            models.Index(fields=['agency', 'compliance_status']),
            models.Index(fields=['case_id']),
        ]
    
    def __str__(self):
        return f"Case {self.case_id}: {self.referred_user.user.full_name}"


class ComplianceTimeline(models.Model):
    """Tracks key events in a court-referred user's journey"""
    
    EVENT_TYPE_CHOICES = [
        ('referral', 'Referral Received'),
        ('registration', 'User Registration'),
        ('quiz_completed', 'Career Quiz Completed'),
        ('resume_completed', 'Resume Completed'),
        ('job_application', 'Job Application Submitted'),
        ('training_enrolled', 'Training Enrollment'),
        ('training_completed', 'Training Completed'),
        ('certificate_verified', 'Certificate Verified'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('hired', 'Hired'),
        ('court_appearance', 'Court Appearance'),
        ('case_closed', 'Case Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_assignment = models.ForeignKey(CaseAssignment, on_delete=models.CASCADE, related_name='timeline_events')
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    description = models.TextField()
    
    event_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-event_date']
        indexes = [
            models.Index(fields=['case_assignment', 'event_type']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.case_assignment.case_id}"


class ProgressReport(models.Model):
    """Generated reports for court submission"""
    
    REPORT_FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_assignment = models.ForeignKey(CaseAssignment, on_delete=models.CASCADE, related_name='progress_reports')
    
    report_format = models.CharField(max_length=10, choices=REPORT_FORMAT_CHOICES, default='pdf')
    file_url = models.URLField(blank=True)  # Cloudinary or storage URL
    
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Report metadata
    start_date = models.DateField()
    end_date = models.DateField()
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"Report for {self.case_assignment.case_id} - {self.generated_at.date()}"


class AuditLog(models.Model):
    """Security logging for all administrative actions"""
    
    ACTION_CHOICES = [
        ('case_assigned', 'Case ID Assigned'),
        ('document_uploaded', 'Document Uploaded'),
        ('report_generated', 'Report Generated'),
        ('report_downloaded', 'Report Downloaded'),
        ('compliance_updated', 'Compliance Status Updated'),
        ('user_verified', 'User Verified'),
        ('user_suspended', 'User Suspended'),
        ('payment_processed', 'Payment Processed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_targets')
    
    details = models.JSONField(default=dict, help_text="Additional action details")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['admin_user', 'timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.action} by {self.admin_user.full_name if self.admin_user else 'Unknown'} at {self.timestamp}"
