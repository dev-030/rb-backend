"""Serializers for training provider features"""

from rest_framework import serializers
from users.models import TrainingProgram, Enrollment, Certificate, EmployerTrainingLinkage
from django.contrib.auth import get_user_model

User = get_user_model()


class TrainerProgramSerializer(serializers.ModelSerializer):
    learner_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingProgram
        fields = [
            'id', 'name', 'description', 'category', 'external_link',
            'duration', 'duration_unit', 'deadline', 'is_active', 'created_at',
            'learner_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_learner_count(self, obj):
        # Look for annotated value
        if hasattr(obj, 'learner_count'):
            return obj.learner_count
        return obj.enrollments.count()


class LearnerSerializer(serializers.ModelSerializer):
    learner_name = serializers.CharField(source='user.full_name', read_only=True)
    learner_email = serializers.CharField(source='user.email', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    certificate_id = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()
    certificate_status = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'learner_name', 'learner_email', 'program',
            'program_name', 'status', 'progress_percentage',
            'financial_aid_requested',
            'start_date', 'completion_date', 'certificate_id', 'certificate_url',
            'certificate_status', 'rejection_reason', 'resume_url'
        ]
    
    def get_certificate_id(self, obj):
        """Return certificate ID if exists, otherwise None"""
        # Get the latest certificate
        certificate = Certificate.objects.filter(enrollment=obj).first()
        return certificate.id if certificate else None
    
    def get_certificate_url(self, obj):
        """Return certificate file URL if exists, otherwise None"""
        certificate = Certificate.objects.filter(enrollment=obj).first()
        return certificate.certificate_file.url if certificate and certificate.certificate_file else None
    
    def get_certificate_status(self, obj):
        """Return certificate verification status if exists, otherwise None"""
        certificate = Certificate.objects.filter(enrollment=obj).first()
        return certificate.verification_status if certificate else None
    
    def get_rejection_reason(self, obj):
        """Return rejection reason if certificate was rejected, otherwise None"""
        certificate = Certificate.objects.filter(enrollment=obj).first()
        return certificate.rejection_reason if certificate and certificate.rejection_reason else None
    
    def get_resume_url(self, obj):
        """Return resume PDF URL if available, otherwise null"""
        try:
            resume = obj.user.resume
            return resume.resume_pdf_url if resume.resume_pdf_url else None
        except:
            return None



class CertificateVerificationSerializer(serializers.ModelSerializer):
    learner_name = serializers.CharField(source='enrollment.user.full_name', read_only=True)
    program_name = serializers.CharField(source='enrollment.program.name', read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'enrollment', 'learner_name', 'program_name',
            'certificate_file', 'verification_status', 'uploaded_at',
            'rejection_reason'
        ]
        read_only_fields = ['id', 'enrollment', 'uploaded_at']


class EmployerLinkageSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source='employer.company_name', read_only=True)
    program_name = serializers.CharField(source='training_program.name', read_only=True)
    
    class Meta:
        model = EmployerTrainingLinkage
        fields = [
            'id', 'employer', 'employer_name', 'training_program',
            'program_name', 'roles_hiring', 'salary_range',
            'active_listings', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TrainerDashboardSerializer(serializers.Serializer):
    total_learners = serializers.IntegerField()
    active_learners = serializers.IntegerField()
    completed_learners = serializers.IntegerField()
    pending_enrollments = serializers.IntegerField()
    average_completion_rate = serializers.FloatField()
    pending_certificate_verifications = serializers.IntegerField()


class JobOpportunitiesSerializer(serializers.Serializer):
    """Serializer for job opportunities available for trainer's learners"""
    job_id = serializers.UUIDField()
    employer_name = serializers.CharField()
    employer_id = serializers.UUIDField()
    employer_location = serializers.CharField()
    employer_industry = serializers.CharField()
    
    job_title = serializers.CharField()
    job_category = serializers.CharField()
    employment_type = serializers.CharField()
    location = serializers.CharField()
    is_remote = serializers.BooleanField()
    
    salary_min = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    salary_max = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    salary_range = serializers.CharField()
    
    number_of_openings = serializers.IntegerField(allow_null=True)
    skills_required = serializers.ListField()
    
    deadline = serializers.DateField(allow_null=True)
    status = serializers.CharField()
    posted_date = serializers.DateTimeField()
