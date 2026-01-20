from django.contrib import admin
from .models import (
    # User Role Models
    GeneralUser, ReferredUser, Employer, TrainingProvider, Agency,
    # Job Models
    Job, JobApplication, Interview,
    # Training Models
    TrainingProgram, Enrollment, Certificate,
    # Compliance Models
    CaseAssignment, ComplianceTimeline, ProgressReport, AuditLog,
    # Profile Models
    CareerQuiz, Resume, WorkExperience, Education, Skill, Document,
    # Payment Models
    Payment, TransactionLog,
    # Additional Models
    SavedJob, ContactMessage, EmployerTrainingLinkage
)


# ===== USER ROLE MODELS =====

@admin.register(GeneralUser)
class GeneralUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'has_paid', 'resume_completeness', 'created_at')
    list_filter = ('has_paid', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReferredUser)
class ReferredUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'case_id', 'court_name', 'has_paid', 'created_at')
    list_filter = ('has_paid', 'created_at')
    search_fields = ('user__email', 'case_id', 'court_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'industry', 'status', 'created_at')
    list_filter = ('status', 'industry', 'created_at')
    search_fields = ('user__email', 'company_name', 'office_location')
    readonly_fields = ('created_at', 'updated_at')



@admin.register(TrainingProvider)
class TrainingProviderAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'status', 'total_learners', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'specialization')
    readonly_fields = ('created_at', 'updated_at', 'total_learners', 'average_completion_rate')


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('user', 'agency_name', 'agency_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'agency_name', 'agency_id')
    readonly_fields = ('created_at', 'updated_at')


# ===== JOB MODELS =====

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer', 'category', 'location', 'salary_min', 'salary_max', 'status', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'employer__company_name', 'location')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'job', 'status', 'applied_at')
    list_filter = ('status', 'applied_at')
    search_fields = ('applicant__user__email', 'job__title')
    readonly_fields = ('applied_at',)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('application', 'scheduled_date', 'scheduled_time', 'status', 'location')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('application__applicant__email', 'application__job__title')


# ===== TRAINING MODELS =====

@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'category', 'duration', 'duration_unit', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'provider__user__full_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'program', 'status', 'progress_percentage', 'start_date')
    list_filter = ('status', 'start_date')
    search_fields = ('user__email', 'program__name')
    readonly_fields = ('start_date', 'completion_date', 'created_at', 'updated_at')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'verification_status', 'uploaded_at', 'verified_at')
    list_filter = ('verification_status', 'uploaded_at')
    search_fields = ('enrollment__user__user__email', 'enrollment__program__name')
    readonly_fields = ('uploaded_at', 'verified_at')


# ===== COMPLIANCE MODELS =====

@admin.register(CaseAssignment)
class CaseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('referred_user', 'agency', 'case_id', 'assigned_date', 'compliance_status')
    list_filter = ('compliance_status', 'assigned_date')
    search_fields = ('referred_user__user__email', 'case_id', 'agency__agency_name')
    readonly_fields = ('created_at', 'updated_at', 'assigned_date')


@admin.register(ComplianceTimeline)
class ComplianceTimelineAdmin(admin.ModelAdmin):
    list_display = ('case_assignment', 'event_type', 'event_date', 'created_by')
    list_filter = ('event_type', 'event_date')
    search_fields = ('case_assignment__case_id', 'description')


@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display = ('case_assignment', 'start_date', 'end_date', 'generated_at', 'report_format')
    list_filter = ('generated_at', 'report_format')
    search_fields = ('case_assignment__case_id',)
    readonly_fields = ('generated_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'action', 'target_user', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('admin_user__email', 'target_user__email')
    readonly_fields = ('timestamp',)


# ===== PROFILE MODELS =====

@admin.register(CareerQuiz)
class CareerQuizAdmin(admin.ModelAdmin):
    list_display = ('user', 'recommended_career', 'completed_at')
    search_fields = ('user__email', 'recommended_career')
    readonly_fields = ('completed_at',)


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'completeness_percentage', 'created_at')
    search_fields = ('user__email', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'completeness_percentage')


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ('resume', 'job_title', 'company_name', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('resume__user__email', 'job_title', 'company_name')


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('resume', 'degree', 'institution_name', 'start_date', 'end_date')
    list_filter = ('degree',)
    search_fields = ('resume__user__email', 'degree', 'institution_name')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('resume', 'skill_name', 'proficiency')
    list_filter = ('proficiency',)
    search_fields = ('resume__user__email', 'skill_name')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'filename', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('user__email', 'filename')
    readonly_fields = ('uploaded_at',)


# ===== PAYMENT MODELS =====

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('user__email', 'stripe_payment_intent_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ('payment', 'event_type', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('payment__user__email',)
    readonly_fields = ('timestamp',)


# ===== ADDITIONAL MODELS =====

@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__user__email', 'job__title')
    readonly_fields = ('saved_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject')
    readonly_fields = ('created_at',)


@admin.register(EmployerTrainingLinkage)
class EmployerTrainingLinkageAdmin(admin.ModelAdmin):
    list_display = ('employer', 'training_provider', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('employer__company_name', 'training_provider__user__email')
    readonly_fields = ('created_at',)
