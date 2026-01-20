"""Serializers for super admin panel"""

from rest_framework import serializers
from users.models import Agency, Employer, TrainingProvider, Payment
from authentication.models import UserAccount
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_trainers = serializers.IntegerField()
    total_employers = serializers.IntegerField()
    total_agencies = serializers.IntegerField()
    total_job_seekers = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    active_programs = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    monthly_revenue = serializers.FloatField()
    pending_verifications = serializers.IntegerField()
    placement_rate = serializers.FloatField()
    average_completion_rate = serializers.FloatField()
    enrollments_by_category = serializers.ListField(child=serializers.DictField())



class AgencyVerificationSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Agency
        fields = [
            'id', 'user', 'user_email', 'agency_id', 'agency_name',
            'representative_name', 'address', 'verification_documents',
            'document_public_id', 'document_url',
            'status', 'created_at'
        ]


class EmployerVerificationSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    total_jobs = serializers.SerializerMethodField()
    
    class Meta:
        model = Employer
        fields = [
            'id', 'user', 'user_email', 'company_name', 'industry',
            'office_location', 'status', 'total_jobs', 'created_at'
        ]
    
    def get_total_jobs(self, obj):
        return obj.jobs.count()



class TrainerVerificationSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    trainer_name = serializers.CharField(source='user.full_name', read_only=True)
    total_programs = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingProvider
        fields = [
            'id', 'user', 'user_email', 'trainer_name', 'specialization', 'experience',
            'status', 'total_learners', 'average_completion_rate', 'total_programs',
            'created_at'
        ]
    
    def get_total_programs(self, obj):
        return obj.programs.count()


class UserListSerializer(serializers.ModelSerializer):
    resume_completeness = serializers.SerializerMethodField()
    resume_pdf_url = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAccount
        fields = [
            'id', 'email', 'full_name', 'user_type', 'is_active',
            'date_joined', 'resume_completeness', 'resume_pdf_url'
        ]
    
    def get_resume_completeness(self, obj):
        try:
            if obj.user_type == 'general':
                return obj.general_profile.resume_completeness
            elif obj.user_type == 'agency_referred':
                return obj.referred_profile.resume_completeness
        except:
            return 0
        return 0
    
    def get_resume_pdf_url(self, obj):
        """Get resume PDF URL from Resume model"""
        try:
            from users.models import Resume
            resume = Resume.objects.get(user=obj)
            return resume.resume_pdf_url if resume.resume_pdf_url else None
        except:
            return None


class PaymentListSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'user_name', 'amount', 'currency',
            'status', 'payment_method', 'receipt_number', 'receipt_url', 'case_id',
            'created_at'
        ]





class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category CRUD operations"""
    job_count = serializers.SerializerMethodField()
    training_count = serializers.SerializerMethodField()
    
    class Meta:
        from users.models import Category
        model = Category
        fields = [
            "id", "name", "slug", "description", "is_active",
            "job_count", "training_count", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at", "job_count", "training_count"]
    
    def get_job_count(self, obj):
        return obj.jobs.count() if hasattr(obj, "jobs") else 0
    
    def get_training_count(self, obj):
        return obj.training_programs.count() if hasattr(obj, "training_programs") else 0

