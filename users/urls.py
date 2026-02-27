from django.urls import path
from .views import (
    # Dashboard
    DashboardView,
    
    # Jobs
    JobListView, JobDetailView, JobApplicationCreateView,
    JobApplicationListView, JobApplicationDetailView, InterviewAndRejectedApplicationsView,
    InterviewListView,
    
    # Saved Jobs
    SavedJobCreateView, SavedJobListView, SavedJobDeleteView,
    
    # Training
    TrainingProgramListView, TrainingEnrollView, MyTrainingView,
    CertificateUploadView, CertificateListView,
    
    # Resume
    CareerQuizView, ResumeView, WorkExperienceView, WorkExperienceDetailView,
    EducationView, EducationDetailView, SkillView, SkillDetailView,
    ResumeParseView,
    
    # Documents
    DocumentUploadView, DocumentListView, DocumentDeleteView,
    
    # Contact
    ContactMessageView,
    
    # AI Career Analysis
    CareerAnalysisView,
    DeleteAccountView
)
from .category_views import PublicCategoryListView
from .resume_status_view import ResumeCompletenessView
from .resume_pipeline_view import ResumeGenerationPipelineView
from .analyze_pdf_view import AnalyzeResumePDFView
from .notification_views import (
    NotificationListView, NotificationUnreadCountView,
    MarkNotificationReadView, MarkAllNotificationsReadView,
    DeleteNotificationView, ClearAllNotificationsView
)
from .views import (
    ManualJobApplicationViewSet, ManualTrainingViewSet,
    ManualCertificateViewSet, ManualInterviewViewSet
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'applications/manual', ManualJobApplicationViewSet, basename='manual-application')
router.register(r'training/manual', ManualTrainingViewSet, basename='manual-training')
router.register(r'certificates/manual', ManualCertificateViewSet, basename='manual-certificate')
router.register(r'interviews/manual', ManualInterviewViewSet, basename='manual-interview')

urlpatterns = [
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='user_dashboard'),
    
    # Jobs
    path('jobs/', JobListView.as_view(), name='job_list'),
    path('jobs/<uuid:pk>/', JobDetailView.as_view(), name='job_detail'),
    path('jobs/<uuid:job_id>/apply/', JobApplicationCreateView.as_view(), name='job_apply'),
    path('applications/', JobApplicationListView.as_view(), name='applications_list'),
    path('applications/interviews-and-rejected/', InterviewAndRejectedApplicationsView.as_view(), name='interviews_rejected'),
    path('applications/<uuid:pk>/', JobApplicationDetailView.as_view(), name='application_detail'),
    path('interviews/', InterviewListView.as_view(), name='interviews'),
    
    # Saved Jobs
    path('jobs/<uuid:job_id>/save/', SavedJobCreateView.as_view(), name='save_job'),
    path('saved-jobs/', SavedJobListView.as_view(), name='saved_jobs'),
    path('saved-jobs/<uuid:pk>/delete/', SavedJobDeleteView.as_view(), name='delete_saved_job'),
    
    # Training
    path('training/', TrainingProgramListView.as_view(), name='training_list'),
    path('training/<uuid:program_id>/enroll/', TrainingEnrollView.as_view(), name='enroll'),
    path('my-training/', MyTrainingView.as_view(), name='my_training'),
    path('enrollments/<uuid:enrollment_id>/certificate/', CertificateUploadView.as_view(), name='upload_certificate'),
    path('certificates/', CertificateListView.as_view(), name='certificates'),
    
    # Resume & Profile
    path('career-quiz/', CareerQuizView.as_view(), name='career_quiz'),
    path('resume/', ResumeView.as_view(), name='resume'),
    path('resume/parse/', ResumeParseView.as_view(), name='resume_parse'),
    path('resume/completeness/', ResumeCompletenessView.as_view(), name='resume_completeness'),
    path('resume/generate-and-analyze/', ResumeGenerationPipelineView.as_view(), name='resume_generate_analyze'),
    path('resume/analyze-pdf/', AnalyzeResumePDFView.as_view(), name='analyze_pdf'),
    path('resume/work-experience/', WorkExperienceView.as_view(), name='work_experience'),
    path('resume/work-experience/<uuid:pk>/', WorkExperienceDetailView.as_view(), name='work_experience_detail'),
    path('resume/education/', EducationView.as_view(), name='education'),
    path('resume/education/<uuid:pk>/', EducationDetailView.as_view(), name='education_detail'),
    path('resume/skills/', SkillView.as_view(), name='skills'),
    path('resume/skills/<uuid:pk>/', SkillDetailView.as_view(), name='skill_detail'),
    
    # Documents
    path('documents/upload/', DocumentUploadView.as_view(), name='document_upload'),
    path('documents/', DocumentListView.as_view(), name='documents'),
    path('documents/<uuid:pk>/delete/', DocumentDeleteView.as_view(), name='document_delete'),
    
    # Contact
    path('contact/', ContactMessageView.as_view(), name='contact'),
    
    # AI Career Analysis
    path('career-analysis/', CareerAnalysisView.as_view(), name='career_analysis'),
    
    # Account Settings
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),
    
    # Categories (public listing for providers)
    path('categories/', PublicCategoryListView.as_view(), name='public_categories'),
    
    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications_list'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notifications_unread_count'),
    path('notifications/<uuid:pk>/read/', MarkNotificationReadView.as_view(), name='notification_mark_read'),
    path('notifications/mark-all-read/', MarkAllNotificationsReadView.as_view(), name='notifications_mark_all_read'),
    path('notifications/<uuid:pk>/delete/', DeleteNotificationView.as_view(), name='notification_delete'),
    path('notifications/clear-all/', ClearAllNotificationsView.as_view(), name='notifications_clear_all'),
]

urlpatterns += router.urls
