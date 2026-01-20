from django.urls import path
from .views import (
    EmployerDashboardView, JobCreateView, JobListView, JobUpdateView,
    ApplicantListView, AllApplicantsView, ApplicantDetailView, UpdateApplicationStatusView,
    ScheduleInterviewView, InterviewListView, InterviewUpdateView, HiredApplicantsListView
)


urlpatterns = [
    # Dashboard
    path('dashboard/', EmployerDashboardView.as_view(), name='employer_dashboard'),
    
    # Job Management
    path('jobs/create/', JobCreateView.as_view(), name='job_create'),
    path('jobs/', JobListView.as_view(), name='employer_jobs'),
    path('jobs/<uuid:pk>/', JobUpdateView.as_view(), name='job_update'),
    
    # Applicant Management
    path('applicants/', AllApplicantsView.as_view(), name='all_applicants'),
    path('applicants/hired/', HiredApplicantsListView.as_view(), name='hired_applicants'),
    path('jobs/<uuid:job_id>/applicants/', ApplicantListView.as_view(), name='applicants'),
    path('applicants/<uuid:application_id>/', ApplicantDetailView.as_view(), name='applicant_detail'),
    path('applicants/<uuid:application_id>/status/', UpdateApplicationStatusView.as_view(), name='update_status'),
    
    # Interviews
    path('interviews/schedule/', ScheduleInterviewView.as_view(), name='schedule_interview'),
    path('interviews/', InterviewListView.as_view(), name='employer_interviews'),
    path('interviews/<uuid:pk>/', InterviewUpdateView.as_view(), name='interview_detail'),
]
