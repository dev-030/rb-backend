from django.db import models
from django.conf import settings
import uuid

# Create your models here.
class AgencyCaseLoad(models.Model):
    """
    Stores case data uploaded via CSV by Agencies.
    Acts as a staging area to link Users to Agencies when they sign up
    or when they are matched by Email/Case ID.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey('users.Agency', on_delete=models.CASCADE, related_name='case_loads')
    
    # CSV Provided Data
    case_id = models.CharField(max_length=100, help_text="Case ID from the Court")
    court_name = models.CharField(max_length=200)
    court_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default='on_track', help_text="Initial status assigned by Agency")
    email = models.EmailField(help_text="Email of the offender/user")
    
    # System Status
    is_registered = models.BooleanField(default=False, help_text="True if a matching User account has been found/linked")
    matched_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='agency_case_matches')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Constraint: An agency shouldn't upload the same case_id twice? 
        # Or maybe they update it. We'll allow duplicates but maybe warn or update_or_create.
        # Actually, let's enforce uniqueness per agency for sanity.
        unique_together = ('agency', 'case_id')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.case_id} - {self.email} ({'Registered' if self.is_registered else 'Pending'})"
