"""Views for job seeker/user features - dashboard, jobs, training, resume"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, Count, OuterRef, Exists
from django.shortcuts import get_object_or_404

from users.models import (
    Job, JobApplication, Interview, TrainingProgram, Enrollment, Certificate,
    CareerQuiz, Resume, WorkExperience, Education, Skill, Document,
    SavedJob, ContactMessage, GeneralUser, ReferredUser
)
from .serializers import (
    JobSerializer, JobApplicationSerializer, InterviewSerializer,
    TrainingProgramSerializer, EnrollmentSerializer, CertificateSerializer,
    CareerQuizSerializer, ResumeSerializer, WorkExperienceSerializer,
    EducationSerializer, SkillSerializer, DocumentSerializer,
    SavedJobSerializer, ContactMessageSerializer, DashboardStatsSerializer
)
from core.permissions import IsJobSeeker, IsPaidUser
from core.utils import calculate_resume_completeness, parse_resume_pdf
from .notifications import (
    notify_training_enrolled, notify_certificate_uploaded,
    notify_job_applied, notify_trainer_new_enrollment,
    notify_trainer_certificate_pending, notify_employer_new_application
)


# ===== DASHBOARD =====
class DashboardView(APIView):
    """Job seeker dashboard with KPIs and overview"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get(self, request):
        from users.models import TrainingProvider
        user = request.user
        
        # Calculate platform stats
        stats = {
            'live_jobs': Job.objects.filter(status='active').count(),
            'trainers_count': TrainingProvider.objects.count(),
            'total_trainings': TrainingProgram.objects.filter(is_active=True).count(),
            'certificates_earned': Certificate.objects.filter(
                enrollment__user=user, verification_status='verified'
            ).count(),
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ===== JOB SEARCH & APPLICATIONS =====
class JobListView(generics.ListAPIView):
    """List all active jobs with search and filters (public access)"""
    serializer_class = JobSerializer
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]  # Avoid SessionAuth CSRF issues
    
    def get_queryset(self):
        user = self.request.user
        
        queryset = Job.objects.filter(status='active').select_related(
            'employer', 'employer__user'
        )
        
        # Only annotate has_applied for authenticated users
        if user.is_authenticated:
            has_applied_subquery = JobApplication.objects.filter(
                job=OuterRef('pk'),
                applicant=user
            )
            queryset = queryset.annotate(
                has_applied_val=Exists(has_applied_subquery)
            )
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(requirements__icontains=search)
            )
        
        # Filters
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        employment_type = self.request.query_params.get('employment_type', None)
        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)
        
        is_remote = self.request.query_params.get('is_remote', None)
        if is_remote:
            queryset = queryset.filter(is_remote=is_remote.lower() == 'true')
        
        # Salary range
        min_salary = self.request.query_params.get('min_salary', None)
        if min_salary:
            queryset = queryset.filter(salary_min__gte=min_salary)
        
        return queryset.order_by('-created_at')


class JobDetailView(generics.RetrieveAPIView):
    """Get single job details (public access)"""
    serializer_class = JobSerializer
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]  # Avoid SessionAuth CSRF issues
    
    def get_queryset(self):
        user = self.request.user
        queryset = Job.objects.select_related('employer', 'employer__user')
        
        # Only annotate has_applied for authenticated users
        if user.is_authenticated:
            has_applied_subquery = JobApplication.objects.filter(
                job=OuterRef('pk'),
                applicant=user
            )
            queryset = queryset.annotate(
                has_applied_val=Exists(has_applied_subquery)
            )
        
        return queryset


class JobApplicationCreateView(APIView):
    """Apply to a job"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id, status='active')
        except Job.DoesNotExist:
            return Response({
                'error': 'Job not found or no longer active'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already applied
        if JobApplication.objects.filter(job=job, applicant=request.user).exists():
            return Response({
                'error': 'You have already applied to this job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create application
        cover_letter = request.data.get('cover_letter', '')
        application = JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=cover_letter,
            status='pending'
        )
        
        # Send notifications
        try:
            print(f"DEBUG: Notifying job applied. Job: {job.id}, Employer: {job.employer}")
            notify_job_applied(request.user, job)
            # Notify employer
            if job.employer and job.employer.user:
                print(f"DEBUG: Notifying employer {job.employer.user.email}")
                notify_employer_new_application(job.employer.user, request.user, job)
            else:
                print("DEBUG: No employer user found to notify")
        except Exception as e:
            print(f"DEBUG: Notification failed: {e}")
            pass  # Don't fail application if notification fails
        
        serializer = JobApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JobApplicationListView(generics.ListAPIView):
    """List user's job applications with optional status filtering"""
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        queryset = JobApplication.objects.filter(
            applicant=self.request.user
        ).select_related('job', 'job__employer')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-applied_at')


class JobApplicationDetailView(generics.RetrieveAPIView):
    """Get single application details"""
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        return JobApplication.objects.filter(applicant=self.request.user).select_related('job', 'job__employer')


class InterviewAndRejectedApplicationsView(generics.ListAPIView):
    """List user's applications that are either interview_scheduled or rejected"""
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        return JobApplication.objects.filter(
            applicant=self.request.user,
            status__in=['interview_scheduled', 'rejected']
        ).select_related('job', 'job__employer').order_by('-applied_at')


class InterviewListView(generics.ListAPIView):
    """List user's interviews"""
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        return Interview.objects.filter(
            application__applicant=self.request.user
        ).select_related('application', 'application__job', 'application__job__employer').order_by('scheduled_date', 'scheduled_time')


# ===== SAVED JOBS =====
class SavedJobCreateView(APIView):
    """Save/bookmark a job"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({
                'error': 'Job not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already saved
        if SavedJob.objects.filter(user=request.user, job=job).exists():
            return Response({
                'message': 'Job already saved'
            }, status=status.HTTP_200_OK)
        
        saved_job = SavedJob.objects.create(user=request.user, job=job)
        serializer = SavedJobSerializer(saved_job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SavedJobListView(generics.ListAPIView):
    """List user's saved jobs"""
    serializer_class = SavedJobSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        return SavedJob.objects.filter(user=self.request.user).select_related('job', 'job__employer')


class SavedJobDeleteView(generics.DestroyAPIView):
    """Remove job from saved list"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        return SavedJob.objects.filter(user=self.request.user)


# ===== TRAINING & CERTIFICATES =====
class TrainingProgramListView(generics.ListAPIView):
    """List all available training programs (public access)"""
    serializer_class = TrainingProgramSerializer
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]  # Avoid SessionAuth CSRF issues
    
    def get_queryset(self):
        user = self.request.user
        
        queryset = TrainingProgram.objects.filter(is_active=True).select_related(
            'provider', 'provider__user'
        )
        
        # Only annotate is_enrolled for authenticated users
        if user.is_authenticated:
            is_enrolled_subquery = Enrollment.objects.filter(
                program=OuterRef('pk'),
                user=user
            )
            queryset = queryset.annotate(
                is_enrolled_val=Exists(is_enrolled_subquery)
            )
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('-created_at')


class TrainingEnrollView(APIView):
    """Enroll in a training program"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request, program_id):
        try:
            program = TrainingProgram.objects.get(id=program_id, is_active=True)
        except TrainingProgram.DoesNotExist:
            return Response({
                'error': 'Training program not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already enrolled
        if Enrollment.objects.filter(program=program, user=request.user).exists():
            return Response({
                'error': 'Already enrolled in this program'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create enrollment
        enrollment = Enrollment.objects.create(
            program=program,
            user=request.user,
            status='enrolled'
        )
        
        # Send notifications
        try:
            notify_training_enrolled(request.user, program)
            # Notify trainer
            if program.provider and program.provider.user:
                notify_trainer_new_enrollment(program.provider.user, request.user, program)
        except Exception:
            pass  # Don't fail enrollment if notification fails
        
        serializer = EnrollmentSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyTrainingView(generics.ListAPIView):
    """List user's training enrollments"""
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        status_filter = self.request.query_params.get('status', None)
        queryset = Enrollment.objects.filter(user=self.request.user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


class CertificateUploadView(APIView):
    """Upload certificate for verification"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request, enrollment_id):
        try:
            enrollment = Enrollment.objects.get(id=enrollment_id, user=request.user)
        except Enrollment.DoesNotExist:
            return Response({
                'error': 'Enrollment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already uploaded
        if Certificate.objects.filter(enrollment=enrollment).exists():
            return Response({
                'error': 'Certificate already uploaded for this enrollment'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        certificate_file = request.FILES.get('certificate_file')
        if not certificate_file:
            return Response({
                'error': 'Certificate file is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create certificate
        certificate = Certificate.objects.create(
            enrollment=enrollment,
            certificate_file=certificate_file,
            verification_status='pending'
        )
        
        # Send notifications
        try:
            notify_certificate_uploaded(request.user, enrollment.program)
            # Notify trainer
            if enrollment.program.provider and enrollment.program.provider.user:
                notify_trainer_certificate_pending(
                    enrollment.program.provider.user, 
                    request.user, 
                    enrollment.program
                )
        except Exception:
            pass  # Don't fail upload if notification fails
        
        serializer = CertificateSerializer(certificate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CertificateListView(generics.ListAPIView):
    """List user's certificates"""
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        return Certificate.objects.filter(
            enrollment__user=self.request.user
        ).order_by('-uploaded_at')


# ===== RESUME & PROFILE =====
class CareerQuizView(APIView):
    """Submit career quiz and get recommendations"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request):
        # Delete existing quiz if any
        CareerQuiz.objects.filter(user=request.user).delete()
        
        serializer = CareerQuizSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        try:
            quiz = CareerQuiz.objects.get(user=request.user)
            serializer = CareerQuizSerializer(quiz)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CareerQuiz.DoesNotExist:
            return Response({
                'message': 'No career quiz found'
            }, status=status.HTTP_404_NOT_FOUND)


class ResumeView(APIView):
    """Get or create/update resume"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get(self, request):
        resume, created = Resume.objects.get_or_create(user=request.user)
        
        # Update completeness
        resume.completeness_percentage = calculate_resume_completeness(resume)
        resume.save()
        
        serializer = ResumeSerializer(resume)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        resume, created = Resume.objects.get_or_create(user=request.user)
        
        serializer = ResumeSerializer(resume, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Update completeness
        resume.completeness_percentage = calculate_resume_completeness(resume)
        resume.save()
        
        # Update user profile completeness
        if request.user.user_type == 'general':
            profile = request.user.general_profile
        else:
            profile = request.user.referred_profile
        profile.resume_completeness = resume.completeness_percentage
        profile.save()
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkExperienceView(generics.ListCreateAPIView):
    """List and create work experiences"""
    serializer_class = WorkExperienceSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        return WorkExperience.objects.filter(resume=resume)
    
    def perform_create(self, serializer):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        serializer.save(resume=resume)


class WorkExperienceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a work experience"""
    serializer_class = WorkExperienceSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        return WorkExperience.objects.filter(resume=resume)


class EducationView(generics.ListCreateAPIView):
    """List and create education entries"""
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        return Education.objects.filter(resume=resume)
    
    def perform_create(self, serializer):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        serializer.save(resume=resume)


class EducationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete education entry"""
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        return Education.objects.filter(resume=resume)


class SkillView(generics.ListCreateAPIView):
    """List and create skills"""
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        return Skill.objects.filter(resume=resume)
    
    def perform_create(self, serializer):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        serializer.save(resume=resume)


class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete skill"""
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        resume, created = Resume.objects.get_or_create(user=self.request.user)
        return Skill.objects.filter(resume=resume)


class ResumeParseView(APIView):
    """Parse uploaded PDF resume"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request):
        resume_file = request.FILES.get('resume_file')
        if not resume_file:
            return Response({
                'error': 'Resume file is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse the PDF
        parsed_data = parse_resume_pdf(resume_file)
        
        if not parsed_data:
            return Response({
                'error': 'Failed to parse resume'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'Resume parsed successfully',
            'data': parsed_data
        }, status=status.HTTP_200_OK)


# ===== DOCUMENTS =====
class DocumentUploadView(APIView):
    """Upload documents"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request):
        file = request.FILES.get('file')
        document_type = request.data.get('document_type')
        description = request.data.get('description', '')
        
        if not file or not document_type:
            return Response({
                'error': 'File and document type are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        document = Document.objects.create(
            user=request.user,
            document_type=document_type,
            file=file,
            filename=file.name,
            description=description
        )
        
        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DocumentListView(generics.ListAPIView):
    """List user's documents"""
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        document_type = self.request.query_params.get('document_type', None)
        queryset = Document.objects.filter(user=self.request.user)
        
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        
        return queryset.order_by('-uploaded_at')


class DocumentDeleteView(generics.DestroyAPIView):
    """Delete document"""
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


# ===== CONTACT =====
class ContactMessageView(generics.CreateAPIView):
    """Submit contact us message"""
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        contact_message = serializer.save(user=self.request.user)
        
        # Send email notification to admin
        try:
            from authentication.email_service import send_contact_form_to_admin
            send_contact_form_to_admin(contact_message)
        except Exception as e:
            # Log error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send contact form email to admin: {str(e)}")


# ===== AI CAREER ANALYSIS =====
class CareerAnalysisView(APIView):
    """AI-powered job and training recommendations based on quiz responses"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Analyze quiz data and provide job and training recommendations.
        
        Expected request body:
        {
            "quiz_data": {
                "interests": "...",
                "work_environment": "...",
                "training_flexibility": "...",
                "strengths": "...",
                "job_priorities": "...",
                "location": "..."
            }
        }
        """
        import logging
        from users.ai_service import recommend_jobs_and_trainings
        from users.serializers import CareerRecommendationRequestSerializer, CareerRecommendationResponseSerializer
        
        logger = logging.getLogger(__name__)
        
        # Validate request data
        request_serializer = CareerRecommendationRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            logger.error(f"Invalid request data: {request_serializer.errors}")
            return Response({
                'error': 'Invalid request data',
                'details': request_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = request_serializer.validated_data
        
        try:
            # Extract validated quiz data
            quiz_data = validated_data['quiz_data']
            
            logger.info(f"Starting career recommendations for user {request.user.id}")
            
            # Call AI service
            recommendations = recommend_jobs_and_trainings(quiz_data=quiz_data)
            
            logger.info(f"Career recommendations completed for user {request.user.id}")
            
            # Validate response data
            response_serializer = CareerRecommendationResponseSerializer(data=recommendations)
            if not response_serializer.is_valid():
                logger.error(f"Invalid AI response: {response_serializer.errors}")
                return Response({
                    'error': 'AI service returned invalid data',
                    'details': response_serializer.errors
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            # Configuration errors (missing API key, etc.)
            logger.error(f"Configuration error: {str(e)}")
            return Response({
                'error': 'Service configuration error',
                'message': 'AI service is not properly configured. Please contact support.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            # Handle any other errors
            logger.error(f"Career recommendations failed: {str(e)}", exc_info=True)
            

            
            # Check if it's an OpenAI error
            if 'openai' in str(e).lower() or 'api' in str(e).lower():
                return Response({
                    'error': 'AI analysis failed',
                    'message': 'The AI service encountered an error. Please try again later.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Generic error
            return Response({
                'error': 'Analysis failed',
                'message': 'An unexpected error occurred. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAccountView(APIView):
    """Permanently delete user account"""
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def delete(self, request):
        user = request.user
        
        # Double check user type safety, though IsJobSeeker permission handles most of it
        if user.user_type not in ['general', 'agency_referred']:
            return Response({
                'error': 'Account deletion not allowed for this user type'
            }, status=status.HTTP_403_FORBIDDEN)
            
        try:
            # Perform deletion
            user.delete()
            return Response({
                'message': 'Account deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to delete account: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

