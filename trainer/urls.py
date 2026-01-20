from django.urls import path
from .views import (
    TrainerDashboardView, ProgramCreateView, ProgramListView, ProgramUpdateView,
    LearnerListView, LearnerDetailView, PendingCertificatesView,
    VerifyCertificateView, AnalyticsView, EmployerLinkageListView, JobOpportunitiesView
)



urlpatterns = [
    # Dashboard
    path('dashboard/', TrainerDashboardView.as_view(), name='trainer_dashboard'),
    
    # Programs
    path('programs/create/', ProgramCreateView.as_view(), name='program_create'),
    path('programs/', ProgramListView.as_view(), name='programs'),
    path('programs/<uuid:pk>/', ProgramUpdateView.as_view(), name='program_update'),
    
    # Learners
    path('learners/', LearnerListView.as_view(), name='learners'),
    path('learners/<uuid:enrollment_id>/', LearnerDetailView.as_view(), name='learner_detail'),
    
    # Certificate Verification
    path('certificates/pending/', PendingCertificatesView.as_view(), name='pending_certificates'),
    path('certificates/<uuid:certificate_id>/verify/', VerifyCertificateView.as_view(), name='verify_certificate'),
    
    # Analytics
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    
    # Employer Linkage
    path('employer-linkages/', EmployerLinkageListView.as_view(), name='employer_linkages'),
    
    # Job Opportunities
    path('job-opportunities/', JobOpportunitiesView.as_view(), name='job_opportunities'),
]
