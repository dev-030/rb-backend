"""Serializers for job seeker/user features"""

from rest_framework import serializers
from users.models import (
    Job, JobApplication, Interview, TrainingProgram, Enrollment, Certificate,
    CareerQuiz, Resume, WorkExperience, Education, Skill, Document,
    SavedJob, ContactMessage,
    ManualJobApplication, ManualTraining, ManualCertificate, ManualInterview
)
from django.contrib.auth import get_user_model

User = get_user_model()


# Job related serializers
class JobSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source='employer.company_name', read_only=True)
    has_applied = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'employer', 'employer_name', 'title', 'category', 'description',
            'requirements', 'employment_type', 'location', 'is_remote',
            'salary_min', 'salary_max', 'skills_required', 'deadline',
            'status', 'created_at', 'has_applied'
        ]
        read_only_fields = ['id', 'employer', 'created_at', 'has_applied']
    
    def get_has_applied(self, obj):
        """Check if the current user has already applied to this job"""
        # First check if we annotated this in the view (performance optimization)
        if hasattr(obj, 'has_applied_val'):
            return obj.has_applied_val
            
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return JobApplication.objects.filter(
                job=obj,
                applicant=request.user
            ).exists()
        return False



class JobApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.employer.company_name', read_only=True)
    interview_details = serializers.SerializerMethodField()
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_title', 'company_name', 'applicant',
            'status', 'cover_letter', 'applied_at', 'employer_notes',
            'interview_details',
            'hired_date', 'hired_time', 'hired_location'
        ]
        read_only_fields = ['id', 'applicant', 'applied_at', 'employer_notes']

    def get_interview_details(self, obj):
        """Get the detailed interview info if status is interview_scheduled"""
        # Return interview details for relevant statuses
        if obj.status in ['interview_scheduled', 'hired', 'offer_received']:
            # Get the latest interview
            interview = obj.interviews.all().order_by('-created_at').first()
            if interview:
                return InterviewSerializer(interview).data
        return None


class InterviewSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='application.job.title', read_only=True)
    company_name = serializers.CharField(source='application.job.employer.company_name', read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'id', 'application', 'job_title', 'company_name',
            'scheduled_date', 'scheduled_time', 'duration_minutes',
            'meeting_link', 'location', 'status', 'notes'
        ]
        read_only_fields = ['id', 'application']


# Training related serializers
class TrainingProgramSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.user.full_name', read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingProgram
        fields = [
            'id', 'provider', 'provider_name', 'name', 'description',
            'category', 'external_link', 'duration', 'duration_unit', 'deadline',
            'is_active', 'created_at', 'is_enrolled'
        ]
        read_only_fields = ['id', 'provider', 'created_at', 'is_enrolled']

    def get_is_enrolled(self, obj):
        """Check if the current user is already enrolled in this program"""
        # Check for optimized annotation
        if hasattr(obj, 'is_enrolled_val'):
            return obj.is_enrolled_val
            
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(
                program=obj,
                user=request.user
            ).exists()
        return False


class EnrollmentSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)
    provider_name = serializers.CharField(source='program.provider.user.full_name', read_only=True)
    
    external_link = serializers.URLField(source='program.external_link', read_only=True)
    certificate_url = serializers.SerializerMethodField()
    certificate_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'program', 'program_name', 'provider_name', 'external_link', 'user',
            'status', 'progress_percentage', 'start_date', 'completion_date',
            'certificate_url', 'certificate_status', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'start_date', 'created_at']
    
    def get_certificate_url(self, obj):
        """Return certificate file URL if exists, otherwise None"""
        try:
            certificate = Certificate.objects.get(enrollment=obj)
            return certificate.certificate_file.url if certificate.certificate_file else None
        except Certificate.DoesNotExist:
            return None
    
    def get_certificate_status(self, obj):
        """Return certificate verification status if exists, otherwise None"""
        try:
            certificate = Certificate.objects.get(enrollment=obj)
            return certificate.verification_status
        except Certificate.DoesNotExist:
            return None



class CertificateSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='enrollment.program.name', read_only=True)
    certificate_file = serializers.SerializerMethodField()
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'enrollment', 'program_name', 'certificate_file',
            'verification_status', 'uploaded_at', 'verified_at',
            'verified_by', 'rejection_reason'
        ]
        read_only_fields = ['id', 'uploaded_at', 'verified_at', 'verified_by']
    
    def get_certificate_file(self, obj):
        """Return full Cloudinary URL for certificate file"""
        if obj.certificate_file:
            return obj.certificate_file.url
        return None



# Resume related serializers
class CareerQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerQuiz
        fields = [
            'id', 'user', 'responses', 'recommended_career',
            'recommended_industry', 'work_environment_preference',
            'time_commitment', 'completed_at'
        ]
        read_only_fields = ['id', 'user', 'completed_at']


class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = [
            'id', 'resume', 'job_title', 'company_name', 'location',
            'start_date', 'end_date', 'is_current', 'description'
        ]
        read_only_fields = ['id']


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            'id', 'resume', 'institution_name', 'degree', 'field_of_study',
            'start_date', 'end_date', 'gpa'
        ]
        read_only_fields = ['id']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'resume', 'skill_name', 'proficiency']
        read_only_fields = ['id']


class ResumeSerializer(serializers.ModelSerializer):
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    education_entries = EducationSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    
    class Meta:
        model = Resume
        fields = [
            'id', 'user', 'summary', 'phone', 'linkedin_url',
            'portfolio_url', 'resume_pdf_url', 'completeness_percentage', 'work_experiences',
            'education_entries', 'skills', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'completeness_percentage', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id', 'user', 'document_type', 'file', 'filename',
            'description', 'uploaded_at', 'uploaded_by'
        ]
        read_only_fields = ['id', 'user', 'uploaded_at']


class SavedJobSerializer(serializers.ModelSerializer):
    job = JobSerializer(read_only=True)
    
    class Meta:
        model = SavedJob
        fields = ['id', 'user', 'job', 'saved_at']
        read_only_fields = ['id', 'user', 'saved_at']


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'user', 'name', 'email', 'phone', 'subject', 'message',
            'status', 'admin_response', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'admin_response', 'created_at']


# Dashboard serializer
class DashboardStatsSerializer(serializers.Serializer):
    live_jobs = serializers.IntegerField()
    trainers_count = serializers.IntegerField()
    total_trainings = serializers.IntegerField()
    certificates_earned = serializers.IntegerField()


# AI Career Analysis serializers (New Version - Job & Training Recommendations)
class QuizDataSerializer(serializers.Serializer):
    """Serializer for quiz data input."""
    interests = serializers.CharField(max_length=500)
    work_environment = serializers.CharField(max_length=200)
    training_flexibility = serializers.CharField(max_length=200)
    strengths = serializers.CharField(max_length=500)
    job_priorities = serializers.CharField(max_length=500)
    location = serializers.CharField(max_length=200)


class CareerRecommendationRequestSerializer(serializers.Serializer):
    """Simplified request serializer - only quiz data needed"""
    quiz_data = QuizDataSerializer()


class JobRecommendationSerializer(serializers.Serializer):
    """Serializer for recommended jobs"""
    id = serializers.UUIDField()
    title = serializers.CharField()
    company_name = serializers.CharField()
    description = serializers.CharField()
    location = serializers.CharField()
    employment_type = serializers.CharField()
    salary_min = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    salary_max = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    skills_required = serializers.ListField(child=serializers.CharField())
    is_remote = serializers.BooleanField()
    match_reason = serializers.CharField()


class TrainingRecommendationSerializer(serializers.Serializer):
    """Serializer for recommended training programs"""
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    provider_name = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    duration = serializers.IntegerField()
    duration_unit = serializers.CharField()
    external_link = serializers.URLField()
    match_reason = serializers.CharField()


class CareerRecommendationResponseSerializer(serializers.Serializer):
    """Response serializer with job and training recommendations"""
    recommended_jobs = JobRecommendationSerializer(many=True)
    recommended_trainings = TrainingRecommendationSerializer(many=True)




# Resume Generation Request Serializers
class PersonalInfoInputSerializer(serializers.Serializer):
    """Personal information for resume generation"""
    fullName = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    zipCode = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    dateOfBirth = serializers.DateField(required=False, allow_null=True)
    profilePicture = serializers.CharField(required=False, allow_blank=True)  # base64


class WorkExperienceGenerationSerializer(serializers.Serializer):
    """Work experience for resume generation"""
    jobTitle = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    startDate = serializers.DateField(required=False, allow_null=True)
    endDate = serializers.DateField(required=False, allow_null=True)
    current = serializers.BooleanField(default=False)
    responsibilities = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    description = serializers.CharField(required=False, allow_blank=True)


class EducationInputSerializer(serializers.Serializer):
    """Education for resume generation"""
    institutionName = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    degree = serializers.CharField(required=False, allow_blank=True)
    fieldOfStudy = serializers.CharField(required=False, allow_blank=True)
    grade = serializers.CharField(required=False, allow_blank=True)
    startYear = serializers.CharField(required=False, allow_blank=True)
    endYear = serializers.CharField(required=False, allow_blank=True)
    current = serializers.BooleanField(default=False)

class CredentialsInputSerializer(serializers.Serializer):
    """Credentials and licenses for resume generation"""
    selectedLicenses = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    otherLicense = serializers.CharField(required=False, allow_blank=True)
    credential_url = serializers.URLField(required=False, allow_blank=True)


class ResumeGenerationRequestSerializer(serializers.Serializer):
    """Main request for resume generation and analysis"""
    personalInfo = PersonalInfoInputSerializer(required=False)
    workExperience = WorkExperienceGenerationSerializer(many=True, required=False)
    skills = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    education = EducationInputSerializer(many=True, required=False)
    credentials = CredentialsInputSerializer(required=False)
    quiz_data = QuizDataSerializer(required=False)  # Optional quiz data for AI


# ==========================================
# MANUAL ENTRIES SERIALIZERS
# ==========================================

class ManualJobApplicationSerializer(serializers.ModelSerializer):
    """Serializer for manual applications, polyfilled to match JobApplicationSerializer shape"""
    is_manual = serializers.BooleanField(default=True, read_only=True)
    job_title = serializers.CharField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    job = serializers.SerializerMethodField()
    interview_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ManualJobApplication
        fields = [
            'id', 'job', 'job_title', 'company_name', 'user', 'location',
            'status', 'applied_at', 'is_manual', 'interview_details'
        ]
        read_only_fields = ['id', 'user', 'applied_at']
        
    def get_job(self, obj):
        return None
        
    def get_interview_details(self, obj):
        return None


class ManualTrainingSerializer(serializers.ModelSerializer):
    """Serializer for manual trainings, polyfilled to match EnrollmentSerializer shape"""
    is_manual = serializers.BooleanField(default=True, read_only=True)
    # program_name is a virtual field that maps to model's `name`
    program_name = serializers.CharField(source='name')  # writable for POST
    completion_date = serializers.DateField(source='date_completed', required=False, allow_null=True)
    progress_percentage = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()
    certificate_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ManualTraining
        fields = [
            'id', 'program_name', 'provider_name', 'external_link', 'user',
            'status', 'progress_percentage', 'start_date', 'completion_date',
            'certificate_url', 'certificate_status', 'created_at', 'is_manual'
        ]
        read_only_fields = ['id', 'user', 'created_at']
        
    def get_progress_percentage(self, obj):
        return 100 if obj.status == 'completed' else 0
        
    def get_start_date(self, obj):
        return obj.created_at.date() if obj.created_at else None
        
    def get_certificate_url(self, obj):
        return None
        
    def get_certificate_status(self, obj):
        return None


class ManualCertificateSerializer(serializers.ModelSerializer):
    """Serializer for manual certificates, polyfilled to match CertificateSerializer shape"""
    is_manual = serializers.BooleanField(default=True, read_only=True)
    # certificate_file is returned to match the platform shape (maps to certificate_url)
    certificate_file = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()
    verified_at = serializers.SerializerMethodField()
    verified_by = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    enrollment = serializers.SerializerMethodField()
    
    class Meta:
        model = ManualCertificate
        fields = [
            'id', 'enrollment', 'program_name', 'certificate_file', 'certificate_url',
            'verification_status', 'uploaded_at', 'verified_at',
            'verified_by', 'rejection_reason', 'is_manual'
        ]
        read_only_fields = ['id', 'uploaded_at']
        
    def get_certificate_file(self, obj):
        # Return the URL stored in certificate_url field
        return obj.certificate_url or None
        
    def get_enrollment(self, obj):
        return None
        
    def get_verification_status(self, obj):
        return "verified"
        
    def get_verified_at(self, obj):
        return obj.uploaded_at
        
    def get_verified_by(self, obj):
        return None
        
    def get_rejection_reason(self, obj):
        return ""


class ManualInterviewSerializer(serializers.ModelSerializer):
    """Serializer for manual interviews, polyfilled to match InterviewSerializer shape"""
    is_manual = serializers.BooleanField(default=True, read_only=True)
    application = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = ManualInterview
        fields = [
            'id', 'application', 'job_title', 'company_name', 'interview_details',
            'scheduled_date', 'scheduled_time', 'duration_minutes',
            'meeting_link', 'location', 'status', 'notes', 'is_manual', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        
    def get_application(self, obj):
        return None
        
    def get_notes(self, obj):
        return obj.interview_details or "Manual entry"
        
    def get_duration_minutes(self, obj):
        return 30

