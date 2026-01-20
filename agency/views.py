"""Views for agency compliance monitoring - dashboard, user roster, case management"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from django.http import HttpResponse
import csv

from users.models import (
    CaseAssignment, ComplianceTimeline, ProgressReport, AuditLog,
    ReferredUser, JobApplication, Enrollment, CareerQuiz, Resume, Document
)
from .serializers import (
    CaseAssignmentSerializer, ComplianceTimelineSerializer,
    ProgressReportSerializer, AuditLogSerializer, UserRosterSerializer,
    AgencyDashboardSerializer
)
from core.permissions import IsVerifiedAgency, IsAgency
from core.utils import get_client_ip


class AgencyDashboardView(APIView):
    """Agency dashboard with compliance metrics"""
    permission_classes = [IsAuthenticated, IsAgency]
    
    def get(self, request):
        agency = request.user.agency_profile
        
        all_cases = CaseAssignment.objects.filter(agency=agency)
        
        # Upcoming Court Dates (Next 5)
        upcoming_cases = all_cases.filter(
            court_date__gte=timezone.now().date()
        ).order_by('court_date')[:5]

        upcoming_data = [{
            'name': c.referred_user.user.full_name,
            'caseId': c.case_id or c.referred_user.case_id,
            'date': c.court_date,
            'status': c.compliance_status
        } for c in upcoming_cases]

        # Stats
        stats = {
            'total_assigned_users': all_cases.count(),
            'in_progress': all_cases.filter(compliance_status='on_track').count(),
            'completed': all_cases.filter(compliance_status='completed').count(),
            'non_compliant': all_cases.filter(compliance_status='non_compliant').count(),
            'assigned_count': all_cases.filter(compliance_status='assigned').count(), # if exists
            'delayed_count': all_cases.filter(compliance_status='delayed').count(),
            'closed_count': all_cases.filter(compliance_status='closed').count(),
            'quiz_completed_count': sum(
                1 for case in all_cases if CareerQuiz.objects.filter(user=case.referred_user.user).exists()
            ),
            'resume_completed_count': sum(
                1 for case in all_cases if Resume.objects.filter(user=case.referred_user.user).exists()
            ),
            'upcoming_court_dates': upcoming_data
        }
        
        serializer = AgencyDashboardSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRosterView(APIView):
    """List all referred users with their case assignment status for the current agency"""
    permission_classes = [IsAuthenticated, IsAgency]
    
    def get(self, request):
        agency = request.user.agency_profile
        
        # Get users assienged to THIS agency
        # We find CaseAssignments for this agency
        assignments = CaseAssignment.objects.filter(agency=agency).select_related('referred_user__user')
        
        roster_data = []
        for case in assignments:
            referred_user = case.referred_user
            user = referred_user.user
            
            # Check quiz status
            quiz_status = CareerQuiz.objects.filter(user=user).exists()
            
            # Check resume status
            try:
                resume = Resume.objects.get(user=user)
                resume_status = f"{resume.completeness_percentage}% Complete"
            except Resume.DoesNotExist:
                resume_status = "Not Started"
            
            # Count applications and training
            job_applications = JobApplication.objects.filter(applicant=user).count()
            enrollments = Enrollment.objects.filter(user=user).count()
            
            # Certificate status
            verified_certs = Enrollment.objects.filter(
                user=user,
                certificates__verification_status='verified'
            ).count()
            certificate_status = f"{verified_certs} Verified"
            
            # Agency has assigned a tracking case ID
            case_id = case.case_id if case.case_id else referred_user.case_id
            compliance_status = case.compliance_status
            
            roster_data.append({
                'id': str(user.id),
                'name': user.full_name,
                'email': user.email,
                'case_id': case_id,
                'quiz_status': quiz_status,
                'resume_status': resume_status,
                'job_applications_count': job_applications,
                'training_courses_count': enrollments,
                'certificate_status': certificate_status,
                'compliance_status': compliance_status
            })
        
        serializer = UserRosterSerializer(roster_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class AssignCaseIDView(APIView):
    """Assign case ID to a referred user"""
    permission_classes = [IsAuthenticated, IsVerifiedAgency]
    
    def post(self, request, user_id):
        agency = request.user.agency_profile
        
        # Get referred user
        try:
            referred_user = ReferredUser.objects.get(user__id=user_id)
        except ReferredUser.DoesNotExist:
            return Response({
                'error': 'Referred user not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        case_id = request.data.get('case_id')
        court_date = request.data.get('court_date', None)
        
        if not case_id:
            return Response({
                'error': 'Case ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or update case assignment
        case, created = CaseAssignment.objects.get_or_create(
            referred_user=referred_user,
            agency=agency,
            defaults={'case_id': case_id, 'court_date': court_date}
        )
        
        if not created:
            case.case_id = case_id
            if court_date:
                case.court_date = court_date
            case.save()
        
        # Log event
        ComplianceTimeline.objects.create(
            case_assignment=case,
            event_type='referral',
            description=f'Case ID {case_id} assigned',
            created_by=request.user
        )
        
        # Audit log
        AuditLog.objects.create(
            admin_user=request.user,
            action='case_assigned',
            target_user=referred_user.user,
            details={'case_id': case_id},
            ip_address=get_client_ip(request)
        )
        
        serializer = CaseAssignmentSerializer(case)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class UserDetailView(APIView):
    """Get detailed user compliance information"""
    permission_classes = [IsAuthenticated, IsAgency]
    
    def get(self, request, user_id):
        # Get referred user
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            referred_user = user.referred_profile
        except (User.DoesNotExist, ReferredUser.DoesNotExist):
            return Response({
                'error': 'Referred user not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get case assignment if exists
        case_data = None
        timeline_data = []
        try:
            case = CaseAssignment.objects.get(referred_user=referred_user)
            case_serializer = CaseAssignmentSerializer(case)
            case_data = case_serializer.data
            
            # Get timeline
            timeline = ComplianceTimeline.objects.filter(case_assignment=case).order_by('-event_date')
            timeline_serializer = ComplianceTimelineSerializer(timeline, many=True)
            timeline_data = timeline_serializer.data
        except CaseAssignment.DoesNotExist:
            # No case assignment exists - that's okay, continue without it
            pass
        
        # Get resume details
        try:
            resume = Resume.objects.get(user=user)
            resume_data = {
                'contact_info': resume.phone is not None,
                'work_experience': resume.work_experiences.exists(),
                'skills': resume.skills.exists(),
                'resume_completeness': resume.completeness_percentage,
            }
        except Resume.DoesNotExist:
            resume_data = None
        
        return Response({
            'case_details': case_data,
            'timeline': timeline_data,
            'resume': resume_data,
            'applications_count': JobApplication.objects.filter(applicant=user).count(),
            'enrollments_count': Enrollment.objects.filter(user=user).count()
        }, status=status.HTTP_200_OK)


class UploadUserDocumentView(APIView):
    """Upload document on behalf of user"""
    permission_classes = [IsAuthenticated, IsVerifiedAgency]
    
    def post(self, request, user_id):
        # Verify user is assigned to agency
        try:
            case = CaseAssignment.objects.get(
                referred_user__user__id=user_id,
                agency=request.user.agency_profile
            )
        except CaseAssignment.DoesNotExist:
            return Response({
                'error': 'User not assigned to this agency'
            }, status=status.HTTP_404_NOT_FOUND)
        
        file = request.FILES.get('file')
        document_type = request.data.get('document_type')
        
        if not file or not document_type:
            return Response({
                'error': 'File and document type are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create document
        document = Document.objects.create(
            user=case.referred_user.user,
            document_type=document_type,
            file=file,
            filename=file.name,
            uploaded_by=request.user
        )
        
        # Audit log
        AuditLog.objects.create(
            admin_user=request.user,
            action='document_uploaded',
            target_user=case.referred_user.user,
            details={'document_type': document_type},
            ip_address=get_client_ip(request)
        )
        
        return Response({
            'message': 'Document uploaded successfully',
            'document_id': str(document.id)
        }, status=status.HTTP_201_CREATED)


class GenerateReportView(APIView):
    """Generate progress report for court"""
    permission_classes = [IsAuthenticated, IsVerifiedAgency]
    
    def get(self, request, case_id):
        case = get_object_or_404(
            CaseAssignment,
            case_id=case_id,
            agency=request.user.agency_profile
        )
        
        format_type = request.query_params.get('format', 'csv')
        
        # Generate CSV
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="report_{case_id}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Case Report', case_id])
            writer.writerow(['User', case.referred_user.user.full_name])
            writer.writerow(['Email', case.referred_user.user.email])
            writer.writerow(['Court Name', case.referred_user.court_name])
            writer.writerow(['Court Case ID', case.referred_user.case_id])
            writer.writerow(['Agency Case ID', case.case_id])
            writer.writerow(['Compliance Status', case.compliance_status])
            writer.writerow(['Court Date', case.court_date])
            writer.writerow([])
            writer.writerow(['Applications', JobApplication.objects.filter(applicant=case.referred_user.user).count()])
            writer.writerow(['Training Courses', Enrollment.objects.filter(user=case.referred_user.user).count()])
            
            # Audit log
            AuditLog.objects.create(
                admin_user=request.user,
                action='report_generated',
                target_user=case.referred_user.user,
                details={'case_id': case_id, 'format': 'csv'},
                ip_address=get_client_ip(request)
            )
            
            return response
        
        return Response({'error': 'Invalid format'}, status=status.HTTP_400_BAD_REQUEST)


class AuditLogListView(generics.ListAPIView):
    """List audit logs"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAgency]
    pagination_class = None
    
    def get_queryset(self):
        return AuditLog.objects.filter(
            admin_user__agency_profile=self.request.user.agency_profile
        ).order_by('-timestamp')[:100]


class CourtDateCSVUploadView(APIView):
    """
    Upload CSV or Excel file to bulk-import cases.
    Handles 'Active' (matched to user) and 'Pending' (waiting for signup) cases.
    """
    permission_classes = [IsAuthenticated, IsVerifiedAgency]
    
    def post(self, request):
        from datetime import datetime
        from .models import AgencyCaseLoad
        from django.contrib.auth import get_user_model
        import openpyxl
        
        User = get_user_model()
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        filename = uploaded_file.name.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            return Response({'error': 'File must be CSV or Excel (.xlsx)'}, status=status.HTTP_400_BAD_REQUEST)
        
        agency = request.user.agency_profile
        
        try:
            records = []
            
            # --- PARSE FILE ---
            if filename.endswith('.csv'):
                decoded_file = uploaded_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                # Normalize headers
                fieldnames = [h.lower().strip() for h in reader.fieldnames] if reader.fieldnames else []
                for row in reader:
                    # Map row to normalized dict
                    records.append({k.lower().strip(): v.strip() for k, v in row.items()})
                    
            elif filename.endswith('.xlsx'):
                wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                sheet = wb.active
                rows = list(sheet.iter_rows(values_only=True))
                
                if not rows:
                    return Response({'error': 'Empty Excel file'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Header row
                header_row = rows[0]
                headers = [str(h).lower().strip() if h else '' for h in header_row]
                
                for row_idx, row_data in enumerate(rows[1:], start=2):
                    record = {}
                    has_data = False
                    for i, val in enumerate(row_data):
                        if i < len(headers) and headers[i]:
                            val_str = str(val).strip() if val is not None else ''
                            record[headers[i]] = val_str
                            if val_str: has_data = True
                    if has_data:
                        records.append(record)

            total_rows = 0
            successful_matches = 0
            pending_cases = 0
            failed_matches = 0
            skipped_rows = 0
            failures = []
            
            for row_num, row in enumerate(records, start=2): # approx row number
                total_rows += 1
                
                email = row.get('email', '').strip()
                case_id = row.get('case_id', '').strip()
                court_name = row.get('court_name', 'Unknown Court').strip()
                court_date_str = row.get('court_date', '').strip()
                status_val = row.get('status', 'on_track').strip().lower().replace(' ', '_')
                
                if not email or not case_id:
                     failed_matches += 1
                     failures.append({'row': row_num, 'error': 'Missing email or case_id'})
                     continue

                # --- VALIDATION: STRICT UPDATE ONLY ---
                # "if the case id doesnt match ... dont add them"
                # "if email match but case id doesnt ... dont add them"
                # Logic: We ONLY process if the Case ID already exists in our system (AgencyCaseLoad or ReferredUser)
                
                case_exists = AgencyCaseLoad.objects.filter(agency=agency, case_id=case_id).exists()
                if not case_exists:
                    # Check ReferredUser as fallback (maybe manually added but not in load table yet)
                    case_exists = ReferredUser.objects.filter(case_id=case_id).exists()
                
                if not case_exists:
                    skipped_rows += 1
                    failures.append({'row': row_num, 'error': 'Skipped: Case ID not found in system', 'case_id': case_id})
                    continue
                
                # --- PROCESS (Case ID Exists) ---

                # Parse Date
                court_date = None
                if court_date_str:
                    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                         try:
                             if ' ' in court_date_str and fmt.count(' ') == 0: continue 
                             court_date = datetime.strptime(court_date_str.split(' ')[0], fmt).date() 
                             break
                         except ValueError:
                             pass

                # 1. Update/Create AgencyCaseLoad (We know case_id exists comfortably or we want to sync it)
                case_load, _ = AgencyCaseLoad.objects.update_or_create(
                    agency=agency,
                    case_id=case_id,
                    defaults={
                        'email': email,
                        'court_name': court_name,
                        'court_date': court_date,
                        'status': status_val,
                    }
                )
                
                # 2. Check User Link
                # "if case id matches but email doesnt match then show pending registration"
                user = User.objects.filter(email=email).first()
                
                if user:
                    # LINK
                    case_load.matched_user = user
                    case_load.is_registered = True
                    case_load.save()
                    
                    referred_user, _ = ReferredUser.objects.get_or_create(
                        user=user,
                        defaults={
                            'phone_number': '', 
                            'court_name': court_name,
                            'case_id': case_id
                        }
                    )
                    
                    CaseAssignment.objects.update_or_create(
                        referred_user=referred_user,
                        agency=agency,
                        defaults={
                            'case_id': case_id,
                            'court_date': court_date,
                            'compliance_status': status_val if status_val in ['on_track', 'delayed', 'non_compliant', 'completed'] else 'on_track'
                        }
                    )
                    successful_matches += 1
                else:
                    # PENDING (Email not found, but Case ID matched, so we hold it pending)
                    case_load.is_registered = False
                    case_load.matched_user = None
                    case_load.save()
                    pending_cases += 1

            # Log
            AuditLog.objects.create(
                admin_user=request.user,
                action='compliance_updated',
                details={
                    'action': 'bulk_upload', 
                    'type': 'csv/xlsx',
                    'total': total_rows, 
                    'matched': successful_matches, 
                    'pending': pending_cases,
                    'skipped': skipped_rows
                },
                ip_address=get_client_ip(request)
            )

            data = {
                'total_rows': total_rows,
                'successful_matches': successful_matches,
                'failed_matches': failed_matches + pending_cases + skipped_rows, 
                'failures': failures
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AgencyCaseLoadListView(generics.ListAPIView):
    """List all CSV-uploaded cases (Pending and Active)"""
    permission_classes = [IsAuthenticated, IsVerifiedAgency]
    pagination_class = None
    
    def get_queryset(self):
        from .models import AgencyCaseLoad
        return AgencyCaseLoad.objects.filter(agency=self.request.user.agency_profile)
    
    def get_serializer_class(self):
        from .serializers import AgencyCaseLoadSerializer
        return AgencyCaseLoadSerializer


class CourtDateUsersListView(APIView):
    """List all users with court dates set"""
    permission_classes = [IsAuthenticated, IsAgency]
    
    def get(self, request):
        agency = request.user.agency_profile
        
        # Get all case assignments with court dates
        queryset = CaseAssignment.objects.filter(
            agency=agency,
            court_date__isnull=False
        ).select_related('referred_user__user')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(compliance_status=status_filter)
        
        # Order by court_date (upcoming first)
        queryset = queryset.order_by('court_date')
        
        from .serializers import CourtDateUserSerializer
        serializer = CourtDateUserSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateComplianceStatusView(APIView):
    """Update compliance status for a case"""
    permission_classes = [IsAuthenticated, IsVerifiedAgency]
    
    def patch(self, request, case_id):
        agency = request.user.agency_profile
        
        # Get case assignment
        try:
            case_assignment = CaseAssignment.objects.get(
                id=case_id,
                agency=agency
            )
        except CaseAssignment.DoesNotExist:
            return Response({
                'error': 'Case not found or not assigned to this agency'
            }, status=status.HTTP_404_NOT_FOUND)
        
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({
                'error': 'Status is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate status
        valid_statuses = ['on_track', 'delayed', 'non_compliant', 'completed', 'closed']
        if new_status not in valid_statuses:
            return Response({
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update status
        old_status = case_assignment.compliance_status
        case_assignment.compliance_status = new_status
        case_assignment.save()
        
        # Log event
        ComplianceTimeline.objects.create(
            case_assignment=case_assignment,
            event_type='court_appearance',
            description=f'Compliance status updated from {old_status} to {new_status}',
            created_by=request.user
        )
        
        # Audit log
        AuditLog.objects.create(
            admin_user=request.user,
            action='compliance_updated',
            target_user=case_assignment.referred_user.user,
            details={
                'case_id': str(case_assignment.id),
                'old_status': old_status,
                'new_status': new_status
            },
            ip_address=get_client_ip(request)
        )
        
        from .serializers import CaseAssignmentSerializer
        serializer = CaseAssignmentSerializer(case_assignment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserHistoryReportView(APIView):
    """Get comprehensive user history report for download"""
    permission_classes = [IsAuthenticated, IsAgency]
    
    def get(self, request, user_id):
        agency = request.user.agency_profile
        
        # Get user
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            referred_user = user.referred_profile
        except (User.DoesNotExist, ReferredUser.DoesNotExist):
            return Response({
                'error': 'Referred user not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get case assignment
        case_info = None
        try:
            case = CaseAssignment.objects.get(referred_user=referred_user, agency=agency)
            case_info = {
                'case_id': case.case_id,
                'court_date': case.court_date,
                'compliance_status': case.compliance_status,
                'assigned_date': case.assigned_date,
                'notes': case.notes
            }
        except CaseAssignment.DoesNotExist:
            pass
        
        # Get resume data
        resume_data = None
        
        try:
            from users.models import Resume
            resume = Resume.objects.get(user=user)
            resume_data = {
                'summary': resume.summary,
                'phone': resume.phone,
                'linkedin_url': resume.linkedin_url,
                'portfolio_url': resume.portfolio_url,
                'resume_pdf_url': resume.resume_pdf_url,
                'completeness_percentage': resume.completeness_percentage
            }
            
        except Resume.DoesNotExist:
            pass
        
        # Get training enrollments
        enrollments = Enrollment.objects.filter(user=user).select_related('program')
        training_data = [{
            'program_name': e.program.name,
            'category': e.program.category.name if e.program.category else None,
            'status': e.status,
            'progress_percentage': e.progress_percentage,
            'start_date': e.start_date,
            'completion_date': e.completion_date,
            'external_link': e.program.external_link
        } for e in enrollments]
        
        # Get certificates
        from users.models import Certificate
        certificates = Certificate.objects.filter(
            enrollment__user=user
        ).select_related('enrollment__program')
        
        certificates_data = [{
            'training_program': c.enrollment.program.name,
            'verification_status': c.verification_status,
            'certificate_url': c.certificate_file.url if c.certificate_file else None,
            'uploaded_at': c.uploaded_at,
            'verified_at': c.verified_at
        } for c in certificates]
        
        # Get job applications
        applications = JobApplication.objects.filter(applicant=user).select_related('job')
        job_applications_data = [{
            'job_title': app.job.title,
            'company': app.job.employer.company_name if hasattr(app.job, 'employer') else 'N/A',
            'location': app.job.location,
            'employment_type': app.job.employment_type,
            'status': app.status,
            'applied_at': app.applied_at,
            'cover_letter': app.cover_letter
        } for app in applications]
        
        # Get career quiz
        quiz_data = None
        try:
            quiz = CareerQuiz.objects.get(user=user)
            quiz_data = {
                'recommended_career': quiz.recommended_career,
                'recommended_industry': quiz.recommended_industry,
                'work_environment_preference': quiz.work_environment_preference,
                'time_commitment': quiz.time_commitment,
                'completed_at': quiz.completed_at
            }
        except CareerQuiz.DoesNotExist:
            pass
        
        # Compile complete report
        report = {
            'user_info': {
                'id': str(user.id),
                'full_name': user.full_name,
                'email': user.email,
                'user_type': user.user_type,
                'date_joined': user.date_joined
            },
            'referred_user_info': {
                'phone_number': referred_user.phone_number,
                'court_name': referred_user.court_name,
                'case_id': referred_user.case_id,
                'has_paid': referred_user.has_paid,
                'resume_completeness': referred_user.resume_completeness
            },
            'case_assignment': case_info,
            'career_quiz': quiz_data,
            'resume': resume_data,
            'training_enrollments': training_data,
            'certificates': certificates_data,
            'job_applications': job_applications_data,
            'summary_stats': {
                'total_trainings': len(training_data),
                'completed_trainings': sum(1 for t in training_data if t['status'] == 'completed'),
                'total_certificates': len(certificates_data),
                'verified_certificates': sum(1 for c in certificates_data if c['verification_status'] == 'verified'),
                'total_job_applications': len(job_applications_data),
            }
        }
        
        # Audit log
        AuditLog.objects.create(
            admin_user=request.user,
            action='report_downloaded',
            target_user=user,
            details={'report_type': 'user_history'},
            ip_address=get_client_ip(request)
        )
        
        return Response(report, status=status.HTTP_200_OK)


class AgencyCaseDetailView(APIView):
    """
    Retrieve, update or delete a case load entry.
    """
    permission_classes = [IsAuthenticated, IsVerifiedAgency]

    def get_object(self, pk, agency):
        from .models import AgencyCaseLoad
        try:
            return AgencyCaseLoad.objects.get(pk=pk, agency=agency)
        except AgencyCaseLoad.DoesNotExist:
            return None

    def put(self, request, pk):
        agency = request.user.agency_profile
        case = self.get_object(pk, agency)
        if not case:
            return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)

        # We need to handle potential email/case_id changes MANUALLY to ensure links stay synced
        new_case_id = request.data.get('case_id', case.case_id)
        new_email = request.data.get('email', case.email)
        
        from django.contrib.auth import get_user_model
        from users.models import ReferredUser, CaseAssignment
        User = get_user_model()
        
        # 1. Check if Case ID or Email Changed
        if new_case_id != case.case_id or new_email != case.email:
            # If changed, we need to re-evaluate the User Link
            
            # Find user by NEW email
            user = User.objects.filter(email=new_email).first()
            
            if user:
                # User Exists -> Link
                case.matched_user = user
                case.is_registered = True
                case.email = new_email
                case.case_id = new_case_id
                
                # Ensure ReferredUser profile exists (but DO NOT overwrite their reported Case ID)
                # We only want to link to them. If their Case ID differs, we want to flag it as a mismatch.
                ref_user, _ = ReferredUser.objects.get_or_create(user=user, defaults={
                    'court_name': request.data.get('court_name', case.court_name),
                    'case_id': new_case_id # Only set if CREATING for the first time
                })
            else:
                # STRICT MODE: If user does not exist, REJECT the update.
                return Response(
                    {'error': 'Invalid Email Address. No active user found with this email. Please verify the email is correct.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 2. ALWAYS sync changes to CaseAssignment if a user is linked
        # This covers status updates, court date changes, etc. even if email/case_id didn't change.
        if case.matched_user:
             from users.models import ReferredUser, CaseAssignment
             # We need the ReferredUser for this user
             ref_user = ReferredUser.objects.filter(user=case.matched_user).first()
             if ref_user:
                 CaseAssignment.objects.update_or_create(
                    referred_user=ref_user,
                    agency=agency,
                    defaults={
                         'case_id': request.data.get('case_id', case.case_id),
                         'court_date': request.data.get('court_date', case.court_date),
                         'compliance_status': request.data.get('status', case.status)
                    }
                )
        
        
        from .serializers import AgencyCaseLoadSerializer
        serializer = AgencyCaseLoadSerializer(case, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            response_data = serializer.data
            
            # Post-save logic to ensure data integrity
            if not case.is_registered:
                 response_data['warning'] = "Note: This case is now PENDING registration. The email provided does not match any active user."
            
            # Audit Log for Update
            from users.models import AuditLog
            from core.utils import get_client_ip
            AuditLog.objects.create(
                admin_user=request.user,
                action='case_updated',
                target_user=case.matched_user, # Might be None if pending
                details={
                    'case_id': case.case_id,
                    'email': case.email,
                    'status': case.status,
                    'court_date': str(case.court_date) if case.court_date else None,
                    'is_registered': case.is_registered
                },
                ip_address=get_client_ip(request)
            )

            return Response(response_data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        agency = request.user.agency_profile
        case = self.get_object(pk, agency)
        if not case:
            return Response({'error': 'Case not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Audit Log for Delete (Capture data before deleting)
        from users.models import AuditLog
        from core.utils import get_client_ip
        AuditLog.objects.create(
            admin_user=request.user,
            action='case_deleted',
            target_user=case.matched_user,
            details={
                'case_id': case.case_id,
                'email': case.email,
                'court_name': case.court_name
            },
            ip_address=get_client_ip(request)
        )
        
        # Also delete the associated CaseAssignment if it exists
        # They are linked by case_id.
        if case.case_id:
            try:
                from users.models import CaseAssignment
                assignment = CaseAssignment.objects.get(
                    case_id=case.case_id,
                    agency=agency
                )
                assignment.delete()
            except CaseAssignment.DoesNotExist:
                pass # Already deleted or never existed, safe to ignore
        
        case.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

