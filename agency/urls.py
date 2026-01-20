from django.urls import path
from .views import (
    AgencyDashboardView, UserRosterView, AssignCaseIDView,
    UserDetailView, UploadUserDocumentView, GenerateReportView,
    AuditLogListView, CourtDateCSVUploadView, CourtDateUsersListView,
    UpdateComplianceStatusView, UserHistoryReportView, AgencyCaseLoadListView,
    AgencyCaseDetailView
)


urlpatterns = [
    # Dashboard
    path('dashboard/', AgencyDashboardView.as_view(), name='agency_dashboard'),
    
    # User Roster
    path('users/', UserRosterView.as_view(), name='user_roster'),
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<uuid:user_id>/assign-case/', AssignCaseIDView.as_view(), name='assign_case'),
    path('users/<uuid:user_id>/upload-document/', UploadUserDocumentView.as_view(), name='upload_user_document'),
    
    # Reports
    path('reports/generate/<str:case_id>/', GenerateReportView.as_view(), name='generate_report'),
    path('reports/user-history/<uuid:user_id>/', UserHistoryReportView.as_view(), name='user_history_report'),
    
    # Court Date Management
    path('court-dates/upload-csv/', CourtDateCSVUploadView.as_view(), name='upload_court_dates'),
    path('court-dates/users/', CourtDateUsersListView.as_view(), name='court_date_users'),
    path('court-dates/<uuid:case_id>/status/', UpdateComplianceStatusView.as_view(), name='update_compliance_status'),
    
    # Audit
    path('audit-logs/', AuditLogListView.as_view(), name='audit_logs'),

    # Case Management (New)
    path('cases/', AgencyCaseLoadListView.as_view(), name='case_list'),
    path('cases/upload-csv/', CourtDateCSVUploadView.as_view(), name='upload_case_csv'),
    path('cases/<uuid:pk>/', AgencyCaseDetailView.as_view(), name='case_detail'),
]
