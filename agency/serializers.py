"""Serializers for agency compliance features"""

from rest_framework import serializers
from .models import AgencyCaseLoad
from users.models import (
    CaseAssignment, ComplianceTimeline, ProgressReport, AuditLog,
    ReferredUser, JobApplication, Enrollment, CareerQuiz, Resume
)
from django.contrib.auth import get_user_model

User = get_user_model()


class CaseAssignmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='referred_user.user.full_name', read_only=True)
    user_email = serializers.CharField(source='referred_user.user.email', read_only=True)
    
    class Meta:
        model = CaseAssignment
        fields = [
            'id', 'referred_user', 'user_name', 'user_email', 'agency',
            'case_id', 'assigned_date', 'court_date', 'compliance_status',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'agency', 'assigned_date', 'created_at']


class ComplianceTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceTimeline
        fields = [
            'id', 'case_assignment', 'event_type', 'description',
            'event_date', 'created_by'
        ]
        read_only_fields = ['id', 'event_date']


class ProgressReportSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='case_assignment.referred_user.user.full_name', read_only=True)
    
    class Meta:
        model = ProgressReport
        fields = [
            'id', 'case_assignment', 'user_name', 'report_format',
            'file_url', 'generated_by', 'generated_at', 'start_date', 'end_date'
        ]
        read_only_fields = ['id', 'generated_by', 'generated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    admin_name = serializers.CharField(source='admin_user.full_name', read_only=True)
    target_name = serializers.CharField(source='target_user.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'admin_user', 'admin_name', 'action', 'target_user',
            'target_name', 'details', 'ip_address', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class UserRosterSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.CharField()
    case_id = serializers.CharField()
    quiz_status = serializers.BooleanField()
    resume_status = serializers.CharField()
    job_applications_count = serializers.IntegerField()
    training_courses_count = serializers.IntegerField()
    certificate_status = serializers.CharField()
    compliance_status = serializers.CharField()


class AgencyDashboardSerializer(serializers.Serializer):
    total_assigned_users = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    non_compliant = serializers.IntegerField()
    assigned_count = serializers.IntegerField()
    delayed_count = serializers.IntegerField()
    closed_count = serializers.IntegerField()
    quiz_completed_count = serializers.IntegerField()
    resume_completed_count = serializers.IntegerField()
    upcoming_court_dates = serializers.ListField(
        child=serializers.DictField()
    )


class CourtDateUserSerializer(serializers.ModelSerializer):
    """Serializer for users with court dates set"""
    user_id = serializers.UUIDField(source='referred_user.user.id', read_only=True)
    user_name = serializers.CharField(source='referred_user.user.full_name', read_only=True)
    user_email = serializers.CharField(source='referred_user.user.email', read_only=True)
    court_name = serializers.CharField(source='referred_user.court_name', read_only=True)
    referred_case_id = serializers.CharField(source='referred_user.case_id', read_only=True)
    
    class Meta:
        model = CaseAssignment
        fields = [
            'id', 'user_id', 'user_name', 'user_email', 'case_id', 
            'referred_case_id', 'court_date', 'compliance_status', 'court_name',
            'assigned_date', 'notes'
        ]
        read_only_fields = ['id', 'assigned_date']


class AgencyCaseLoadSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='matched_user.full_name', read_only=True)
    is_mismatch = serializers.SerializerMethodField()
    user_reported_case_id = serializers.SerializerMethodField()

    class Meta:
        model = AgencyCaseLoad
        fields = [
            'id', 'case_id', 'court_name', 'court_date', 'status', 'email',
            'is_registered', 'matched_user', 'user_name', 'is_mismatch', 
            'user_reported_case_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'is_registered', 'matched_user']

    def get_user_reported_case_id(self, obj):
        if obj.matched_user and hasattr(obj.matched_user, 'referred_profile'):
            return obj.matched_user.referred_profile.case_id
        return None

    def get_is_mismatch(self, obj):
        if obj.matched_user and hasattr(obj.matched_user, 'referred_profile'):
            user_case_id = obj.matched_user.referred_profile.case_id
            # Compare stripping whitespace
            if user_case_id and user_case_id.strip() != obj.case_id.strip():
                return True
        return False


class CSVUploadResponseSerializer(serializers.Serializer):
    """Response serializer for CSV upload results"""
    total_rows = serializers.IntegerField()
    successful_matches = serializers.IntegerField()
    failed_matches = serializers.IntegerField()
    failures = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
