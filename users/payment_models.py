from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid


User = get_user_model()


class Payment(models.Model):
    """Records all financial transactions on the platform"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    # Stripe integration (both fields for backward compatibility)
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='stripe')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Receipt
    receipt_url = models.URLField(blank=True)
    receipt_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Metadata
    description = models.CharField(max_length=255, default='Registration Fee')
    
    # Case reference for court-referred users
    case_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['stripe_payment_intent_id']),
            models.Index(fields=['stripe_checkout_session_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.receipt_number}: ${self.amount} - {self.status}"
    
    def generate_receipt_number(self):
        """Generate unique receipt number"""
        if not self.receipt_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.receipt_number = f"REC-{timestamp}-{str(self.id)[:8].upper()}"
            self.save(update_fields=['receipt_number'])
        return self.receipt_number


class TransactionLog(models.Model):
    """Detailed logging for admin financial monitoring"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transaction_logs')
    
    event_type = models.CharField(max_length=50)  # e.g., "created", "authorized", "captured", "failed"
    details = models.JSONField(default=dict)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.event_type} - {self.payment.receipt_number}"
