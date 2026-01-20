"""Views for employer features - dashboard, job posting, applicant management"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count

from users.models import Job, JobApplication, Interview, Resume, Certificate
from .serializers import (
    EmployerJobSerializer, ApplicantSerializer,
    InterviewCreateSerializer, InterviewDetailSerializer,
    HiredApplicantSerializer, EmployerDashboardSerializer
)
from core.permissions import IsVerifiedEmployer, IsEmployer
from users.notifications import notify_application_status_change


class EmployerDashboardView(APIView):
    """Employer dashboard with metrics"""
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get(self, request):
        employer_profile = request.user.employer_profile
        
        # Calculate stats
        all_jobs = Job.objects.filter(employer=employer_profile)
        all_applications = JobApplication.objects.filter(job__employer=employer_profile)
        
        # Application status counts
        applied_count = all_applications.filter(status='pending').count()
        shortlisted_count = all_applications.filter(status='shortlisted').count()
        rejected_count = all_applications.filter(status='rejected').count()
        
        # Top 10 jobs by applicant count
        top_jobs = all_jobs.annotate(
            applicant_count=Count('applications')
        ).order_by('-applicant_count')[:10]
        
        top_jobs_data = [
            {
                'job_id': str(job.id),
                'job_title': job.title,
                'applicant_count': job.applicant_count,
                'job_status': job.status
            }
            for job in top_jobs
        ]
        
        stats = {
            'total_jobs_posted': all_jobs.count(),
            'active_jobs': all_jobs.filter(status='active').count(),
            'total_applicants': all_applications.count(),
            'applied_count': applied_count,
            'shortlisted_count': shortlisted_count,
            'rejected_count': rejected_count,
            'hired_candidates': all_applications.filter(status='hired').count(),
            'pending_applications': applied_count,  # Same as applied_count for backward compatibility
            'top_jobs': top_jobs_data
        }
        
        serializer = EmployerDashboardSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)


class JobCreateView(generics.CreateAPIView):
    """Post a new job"""
    serializer_class = EmployerJobSerializer
    permission_classes = [IsAuthenticated, IsVerifiedEmployer]
    
    def perform_create(self, serializer):
        serializer.save(employer=self.request.user.employer_profile)
        
        # Notify admins
        try:
            from users.notifications import notify_admin_new_job_posted
            notify_admin_new_job_posted(serializer.instance)
        except Exception as e:
            print(f"Error notifying admin about new job: {e}")


class JobListView(generics.ListAPIView):
    """List employer's jobs"""
    serializer_class = EmployerJobSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):
        status_filter = self.request.query_params.get('status', None)
        queryset = Job.objects.filter(employer=self.request.user.employer_profile)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


class JobUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete a job"""
    serializer_class = EmployerJobSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):
        return Job.objects.filter(employer=self.request.user.employer_profile)


class ApplicantListView(generics.ListAPIView):
    """List applicants for a specific job"""
    serializer_class = ApplicantSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):
        job_id = self.kwargs.get('job_id')
        
        # Verify job belongs to employer
        job = get_object_or_404(
            Job,
            id=job_id,
            employer=self.request.user.employer_profile
        )
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        queryset = JobApplication.objects.filter(job=job)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-applied_at')


class AllApplicantsView(generics.ListAPIView):
    """List all applicants across all employer's jobs"""
    serializer_class = ApplicantSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):
        employer = self.request.user.employer_profile
        status_filter = self.request.query_params.get('status', None)
        
        # Get all applications for all jobs posted by this employer
        queryset = JobApplication.objects.filter(job__employer=employer)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-applied_at')


class ApplicantDetailView(APIView):
    """Get single applicant details including resume"""
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get(self, request, application_id):
        # Get application and verify it belongs to employer's job
        application = get_object_or_404(
            JobApplication,
            id=application_id,
            job__employer=request.user.employer_profile
        )
        
        # Get applicant resume
        try:
            resume = Resume.objects.get(user=application.applicant)
            resume_data = {
                'summary': resume.summary,
                'phone': resume.phone,
                'linkedin_url': resume.linkedin_url,
                'portfolio_url': resume.portfolio_url,
                'work_experiences': list(resume.work_experiences.values()),
                'education': list(resume.education_entries.values()),
                'skills': list(resume.skills.values()),
            }
        except Resume.DoesNotExist:
            resume_data = None
        
        # Get certificates
        certificates = Certificate.objects.filter(
            enrollment__user=application.applicant,
            verification_status='verified'
        ).values('id', 'enrollment__program__name', 'verified_at')
        
        serializer = ApplicantSerializer(application)
        
        return Response({
            'application': serializer.data,
            'resume': resume_data,
            'certificates': list(certificates)
        }, status=status.HTTP_200_OK)


class UpdateApplicationStatusView(APIView):
    """Enhanced application status update with emails and status-specific handling"""
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def patch(self, request, application_id):
        # Get and verify application
        application = get_object_or_404(
            JobApplication,
            id=application_id,
            job__employer=request.user.employer_profile
        )
        
        # Validate request data
        from employer.serializers import EnhancedApplicationStatusSerializer
        serializer = EnhancedApplicationStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid request data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        new_status = validated_data['status']
        employer_notes = validated_data.get('employer_notes', '')
        
        # Update application status and notes
        application.status = new_status
        if employer_notes:
            application.employer_notes = employer_notes
        application.save()
        
        # Handle status-specific actions
        try:
            if new_status == 'rejected':
                # Send rejection email
                from authentication.email_service import send_rejection_email
                send_rejection_email(
                    applicant=application.applicant,
                    job=application.job,
                    employer=request.user.employer_profile
                )
            
            elif new_status == 'hired':
                # Save hired details to JobApplication
                application.hired_date = validated_data.get('start_date')
                application.hired_time = validated_data.get('joining_time')
                application.hired_location = validated_data.get('hiring_location', '')
                application.save()
                
                # Send hiring email with details
                from authentication.email_service import send_hiring_email
                hiring_details = {
                    'start_date': validated_data.get('start_date'),
                    'joining_time': validated_data.get('joining_time'),
                    'hiring_notes': validated_data.get('hiring_notes', '')
                }
                send_hiring_email(
                    applicant=application.applicant,
                    job=application.job,
                    employer=request.user.employer_profile,
                    hiring_details=hiring_details
                )
            
            elif new_status == 'interview_scheduled':
                # Create Interview object
                from users.models import Interview
                interview_data = {
                    'application': application,
                    'scheduled_date': validated_data['scheduled_date'],
                    'scheduled_time': validated_data['scheduled_time'],
                    'duration_minutes': validated_data.get('duration_minutes', 30),
                    'meeting_link': validated_data.get('meeting_link', ''),
                    'location': validated_data.get('location', ''),
                    'notes': validated_data.get('interview_notes', '')
                }
                interview = Interview.objects.create(**interview_data)
                
                # Send interview invitation email
                from authentication.email_service import send_interview_invitation_email
                send_interview_invitation_email(
                    applicant=application.applicant,
                    job=application.job,
                    employer=request.user.employer_profile,
                    interview=interview
                )
        
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email or create interview: {str(e)}")
        
        # Send in-app notification to applicant
        try:
            notify_application_status_change(
                application.applicant,
                application.job,
                new_status,
                employer_notes
            )
        except Exception:
            pass  # Don't fail if notification fails
        
        serializer = ApplicantSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ScheduleInterviewView(generics.CreateAPIView):
    """Schedule an interview"""
    serializer_class = InterviewCreateSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def create(self, request, *args, **kwargs):
        application_id = request.data.get('application')
        
        # Verify application belongs to employer
        application = get_object_or_404(
            JobApplication,
            id=application_id,
            job__employer=request.user.employer_profile
        )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = serializer.save()
        
        # Update application status
        application.status = 'interview_scheduled'
        application.save()
        
        # Send email notification to applicant
        try:
            from authentication.email_service import send_interview_invitation_email
            send_interview_invitation_email(
                applicant=application.applicant,
                job=application.job,
                employer=request.user.employer_profile,
                interview=interview
            )
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send interview invitation email: {str(e)}")
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InterviewListView(generics.ListAPIView):
    """List all interviews for employer's jobs"""
    serializer_class = InterviewDetailSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):
        return Interview.objects.filter(
            application__job__employer=self.request.user.employer_profile
        ).select_related('application__applicant', 'application__job').order_by('scheduled_date', 'scheduled_time')


class InterviewUpdateView(generics.RetrieveUpdateAPIView):
    """Get or update a specific interview's details"""
    serializer_class = InterviewDetailSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):
        return Interview.objects.filter(
            application__job__employer=self.request.user.employer_profile
        ).select_related('application__applicant', 'application__job')


class HiredApplicantsListView(generics.ListAPIView):
    """List all hired applicants for employer's jobs"""
    serializer_class = HiredApplicantSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):
        return JobApplication.objects.filter(
            job__employer=self.request.user.employer_profile,
            status='hired'
        ).select_related('applicant', 'job').order_by('-updated_at')
