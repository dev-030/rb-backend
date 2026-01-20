from django.urls import path
from .views import (
    AdminDashboardView, AgencyListView, PendingAgenciesView, ApproveAgencyView,
    EmployerListView, VerifyEmployerView, TrainerListView, VerifyTrainerView,
    AllUsersListView, LockUserAccountView, PaymentHistoryView, UserResumeView,
    TrainingEnrollmentListView, CategoryViewSet
)


urlpatterns = [
    # Dashboard
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Agency Verification
    path('agencies/', AgencyListView.as_view(), name='agencies'),
    path('agencies/pending/', PendingAgenciesView.as_view(), name='pending_agencies'),
    path('agencies/<uuid:agency_id>/approve/', ApproveAgencyView.as_view(), name='approve_agency'),
    path('agencies/<uuid:agency_id>/verify/', ApproveAgencyView.as_view(), name='verify_agency'),  # Alias for consistency
    
    # Employer Verification
    path('employers/', EmployerListView.as_view(), name='employers'),
    path('employers/<uuid:employer_id>/verify/', VerifyEmployerView.as_view(), name='verify_employer'),
    
    # Trainer Verification
    path('trainers/', TrainerListView.as_view(), name='trainers'),
    path('trainers/<uuid:trainer_id>/verify/', VerifyTrainerView.as_view(), name='verify_trainer'),
    
    # User Management
    path('users/', AllUsersListView.as_view(), name='all_users'),
    path('users/<uuid:user_id>/lock/', LockUserAccountView.as_view(), name='lock_user'),
    path('users/<uuid:user_id>/resume/', UserResumeView.as_view(), name='user_resume'),
    
    # Payments
    path('payments/', PaymentHistoryView.as_view(), name='payment_history'),
    
    # Training Enrollments
    path('training-enrollments/', TrainingEnrollmentListView.as_view(), name='training_enrollments'),
    
    # Category Management
    path('categories/', CategoryViewSet.as_view(), name='categories'),
    path('categories/<uuid:category_id>/', CategoryViewSet.as_view(), name='category_detail'),
]
