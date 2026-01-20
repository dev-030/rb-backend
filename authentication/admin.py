from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserAccount, OTP


@admin.register(UserAccount)
class UserAccountAdmin(BaseUserAdmin):
    """Admin panel for UserAccount model"""
    list_display = ('email', 'full_name', 'user_type', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'full_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('Account Info', {'fields': ('email', 'password', 'full_name', 'profile_pic')}),
        ('User Type', {'fields': ('user_type',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('OAuth', {'fields': ('google_id', 'apple_id', 'is_google_auth', 'did_google_auth')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'deletion_scheduled_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'user_type', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """Admin panel for OTP model"""
    list_display = ('user', 'otp', 'created_at', 'is_valid_status')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'otp')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def is_valid_status(self, obj):
        return "✓ Valid" if obj.is_valid() else "✗ Expired"
    is_valid_status.short_description = 'Status'
