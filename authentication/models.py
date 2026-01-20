from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from cloudinary.models import CloudinaryField
import uuid
from django.utils import timezone
from django.conf import settings



class CustomAccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("user_type", "admin")  # Automatically set user_type to admin

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(email, password, **extra_fields)
    

class UserAccount(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=50)
    profile_pic = CloudinaryField('profile_pic', blank=True, null=True)

    user_type = models.CharField(max_length=20, choices=[
        ('general', 'General'),
        ('agency_referred', 'Agency Referred'),
        ('employer', 'Employer'),
        ('training_provider', 'Training Provider'),
        ('agency', 'Agency'),
        ('admin', 'Admin')
    ])

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    apple_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    is_google_auth = models.BooleanField(default=False)
    did_google_auth = models.BooleanField(default=False)
    deletion_scheduled_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomAccountManager()


    def __str__(self):
        return f"{self.full_name} - {self.email}"
    
    def get_full_name(self):
        return self.full_name
    
    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email

    class Meta:
        verbose_name = "User Account"
        verbose_name_plural = "User Accounts"


class OTP(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    user = models.ForeignKey('UserAccount', on_delete=models.CASCADE, related_name='otps')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_valid(self):
        expiry_duration = getattr(settings, 'OTP_VALIDITY_DURATION', 5)  # minutes
        return timezone.now() <= self.created_at + timezone.timedelta(minutes=expiry_duration)

    def __str__(self):
        return f"OTP({self.otp}) for {self.user.email}"

    class Meta:
        verbose_name = "One-Time Password"
        verbose_name_plural = "One-Time Passwords"
        indexes = [
            models.Index(fields=['created_at']),  # speeds up deletion queries
        ]

