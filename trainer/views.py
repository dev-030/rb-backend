"""Views for training provider features - dashboard, programs, learners, verification"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from django.utils import timezone

from users.models import TrainingProgram, Enrollment, Certificate, Resume, EmployerTrainingLinkage
from .serializers import (
    TrainerProgramSerializer, LearnerSerializer,
    CertificateVerificationSerializer, EmployerLinkageSerializer,
    TrainerDashboardSerializer
)
from core.permissions import IsVerifiedTrainingProvider, IsTrainingProvider
from users.notifications import notify_certificate_verified, notify_certificate_rejected


class TrainerDashboardView(APIView):
    """Training provider dashboard with metrics"""
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get(self, request):
        provider = request.user.trainer_profile
        
        # Optimize with aggregation
        enrollment_stats = Enrollment.objects.filter(program__provider=provider).aggregate(
            total_learners=Count('user', distinct=True),
            active_learners=Count('user', filter=Q(status__in=['enrolled', 'in_progress']), distinct=True),
            completed_learners=Count('user', filter=Q(status='completed'), distinct=True),
            pending_enrollments=Count('id', filter=Q(status='enrolled'))
        )
        
        pending_cert_count = Certificate.objects.filter(
            enrollment__program__provider=provider,
            verification_status='pending'
        ).count()
        
        stats = {
            'total_learners': enrollment_stats['total_learners'],
            'active_learners': enrollment_stats['active_learners'],
            'completed_learners': enrollment_stats['completed_learners'],
            'pending_enrollments': enrollment_stats['pending_enrollments'],
            'average_completion_rate': 0.0,
            'pending_certificate_verifications': pending_cert_count
        }
        
        # Calculate real completion rate
        total = stats['total_learners']
        if total > 0:
            stats['average_completion_rate'] = round((stats['completed_learners'] / total) * 100, 2)
            
        # Update provider record if needed
        if provider.average_completion_rate != stats['average_completion_rate']:
            provider.average_completion_rate = stats['average_completion_rate']
            provider.save(update_fields=['average_completion_rate'])
        
        serializer = TrainerDashboardSerializer(stats) 
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProgramCreateView(generics.CreateAPIView):
    """Create a new training program"""
    serializer_class = TrainerProgramSerializer
    permission_classes = [IsAuthenticated, IsVerifiedTrainingProvider]
    
    def perform_create(self, serializer):
        serializer.save(provider=self.request.user.trainer_profile)
        
        # Notify admins
        try:
            from users.notifications import notify_admin_new_training_created
            notify_admin_new_training_created(serializer.instance)
        except Exception as e:
            print(f"Error notifying admin about new training: {e}")


class ProgramListView(generics.ListAPIView):
    """List all provider's programs"""
    serializer_class = TrainerProgramSerializer
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get_queryset(self):
        return TrainingProgram.objects.filter(
            provider=self.request.user.trainer_profile
        ).annotate(
            learner_count=Count('enrollments')
        ).order_by('-created_at')


class ProgramUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete a program"""
    serializer_class = TrainerProgramSerializer
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get_queryset(self):
        return TrainingProgram.objects.filter(
            provider=self.request.user.trainer_profile
        )
    
    def destroy(self, request, *args, **kwargs):
        """Delete a training program with custom message"""
        instance = self.get_object()
        program_name = instance.name
        self.perform_destroy(instance)
        return Response({
            'message': f'Training program "{program_name}" has been deleted successfully'
        }, status=status.HTTP_200_OK)


class LearnerListView(generics.ListAPIView):
    """List all enrolled learners"""
    serializer_class = LearnerSerializer
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get_queryset(self):
        program_id = self.request.query_params.get('program', None)
        queryset = Enrollment.objects.filter(
            program__provider=self.request.user.trainer_profile
        ).select_related('user', 'program').prefetch_related(
            # Prefetch resume for the serializer to access without N+1
            'user__resume',
            # Prefetch certificates
            'user__enrollments__certificates' # This might be complex, simplified below using subqueries or just caching
        )
        
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-start_date')


class LearnerDetailView(APIView):
    """Get learner details including resume"""
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get(self, request, enrollment_id):
        enrollment = get_object_or_404(
            Enrollment.objects.select_related('user', 'program'),
            id=enrollment_id,
            program__provider=request.user.trainer_profile
        )
        
        # Get resume
        try:
            resume = Resume.objects.get(user=enrollment.user)
            resume_data = {
                'summary': resume.summary,
                'phone': resume.phone,
                'work_experiences': list(resume.work_experiences.values()),
                'education': list(resume.education_entries.values()),
                'skills': list(resume.skills.values()),
            }
        except Resume.DoesNotExist:
            resume_data = None
        
        serializer = LearnerSerializer(enrollment)
        
        return Response({
            'enrollment': serializer.data,
            'resume': resume_data
        }, status=status.HTTP_200_OK)

    def patch(self, request, enrollment_id):
        """Update learner status"""
        enrollment = get_object_or_404(
            Enrollment,
            id=enrollment_id,
            program__provider=request.user.trainer_profile
        )
        
        status_value = request.data.get('status')
        if status_value:
            # If status is changing to something other than completed, clear the date
            if status_value != 'completed':
                enrollment.completion_date = None
            # If status is completed and date is not set, set it to now
            elif status_value == 'completed' and not enrollment.completion_date:
                enrollment.completion_date = timezone.now().date()

            enrollment.status = status_value
            enrollment.save()
            
            serializer = LearnerSerializer(enrollment)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        return Response(
            {'error': 'Status is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class PendingCertificatesView(generics.ListAPIView):
    """List pending certificate verifications"""
    serializer_class = CertificateVerificationSerializer
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get_queryset(self):
        return Certificate.objects.filter(
            enrollment__program__provider=self.request.user.trainer_profile,
            verification_status='pending'
        ).select_related('enrollment', 'enrollment__user', 'enrollment__program').order_by('-uploaded_at')


class VerifyCertificateView(APIView):
    """Verify or reject a certificate"""
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def post(self, request, certificate_id):
        certificate = get_object_or_404(
            Certificate,
            id=certificate_id,
            enrollment__program__provider=request.user.trainer_profile
        )
        
        action = request.data.get('action')  # 'verify' or 'reject'
        rejection_reason = request.data.get('rejection_reason', '')
        
        if action == 'verify':
            certificate.verification_status = 'verified'
            certificate.verified_at = timezone.now()
            certificate.verified_by = request.user
            certificate.save()
            
            # Update enrollment status
            enrollment = certificate.enrollment
            enrollment.status = 'completed'
            enrollment.completion_date = timezone.now().date()
            enrollment.save()
            
            # Notify user
            try:
                notify_certificate_verified(enrollment.user, enrollment.program)
            except Exception:
                pass
            
            return Response({
                'message': 'Certificate verified successfully'
            }, status=status.HTTP_200_OK)
            
        elif action == 'reject':
            certificate.verification_status = 'rejected'
            certificate.rejection_reason = rejection_reason
            certificate.save()
            
            # Notify user
            try:
                notify_certificate_rejected(
                    certificate.enrollment.user, 
                    certificate.enrollment.program, 
                    rejection_reason
                )
            except Exception:
                pass
            
            return Response({
                'message': 'Certificate rejected'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Invalid action'
            }, status=status.HTTP_400_BAD_REQUEST)


class AnalyticsView(APIView):
    """Program analytics and statistics"""
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get(self, request):
        provider = request.user.trainer_profile
        
        # Optimize Learners by program using annotation
        programs = TrainingProgram.objects.filter(provider=provider).annotate(
            total_learners=Count('enrollments'),
            active=Count('enrollments', filter=Q(enrollments__status__in=['enrolled', 'in_progress'])),
            completed=Count('enrollments', filter=Q(enrollments__status='completed'))
        )
        
        learners_by_program = []
        completion_rates = []
        
        for program in programs:
            learners_by_program.append({
                'program_name': program.name,
                'total_learners': program.total_learners,
                'active': program.active,
                'completed': program.completed
            })
            
            rate = (program.completed / program.total_learners * 100) if program.total_learners > 0 else 0
            completion_rates.append({
                'program_name': program.name,
                'completion_rate': round(rate, 2)
            })
            
        # Optimize Category Demand Analysis
        from users.models import Category
        
        # Single query to get counts per category for this provider
        category_counts_qs = Enrollment.objects.filter(
            program__provider=provider
        ).values('program__category__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        category_counts_map = {item['program__category__name']: item['count'] for item in category_counts_qs if item['program__category__name']}
        
        # Determine max for ratio calculation
        max_enrollments = 0
        if category_counts_map:
            max_enrollments = max(category_counts_map.values())
        
        category_demand = []
        # Get all categories to show 0s too if needed, or just show active ones?
        # Original logic looped all categories.
        all_categories = Category.objects.all()
        
        for category in all_categories:
            count = category_counts_map.get(category.name, 0)
            
            demand_level = "Low"
            if max_enrollments > 0:
                ratio = count / max_enrollments
                if ratio > 0.66:
                    demand_level = "High"
                elif ratio > 0.33:
                    demand_level = "Medium"
            
            category_demand.append({
                'category_name': category.name,
                'enrollment_count': count,
                'demand_level': demand_level
            })
            
        # Sort by count desc
        category_demand.sort(key=lambda x: x['enrollment_count'], reverse=True)
        
        return Response({
            'learners_by_program': learners_by_program,
            'completion_rates': completion_rates,
            'category_demand': category_demand
        }, status=status.HTTP_200_OK)


class EmployerLinkageListView(generics.ListAPIView):
    """List employer-training linkages"""
    serializer_class = EmployerLinkageSerializer
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get_queryset(self):
        return EmployerTrainingLinkage.objects.filter(
            training_provider=self.request.user.trainer_profile
        ).select_related('employer', 'training_program').order_by('-created_at')


class JobOpportunitiesView(APIView):
    """List all active job opportunities with employer details"""
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get(self, request):
        from users.models import Job
        
        # Get all active jobs
        jobs = Job.objects.filter(
            status='active'
        ).select_related('employer', 'employer__user', 'category').order_by('-created_at')
        
        # Use optimized serializer instead of manual loop
        # We need to create a dedicated serializer that formats the data as expected by frontend
        # reusing JobOpportunitiesSerializer from .serializers
        from .serializers import JobOpportunitiesSerializer
        
        # To match the expected output format of JobOpportunitiesSerializer fields, 
        # we can prep the data or adjust the serializer.
        # The serializer expects flattened fields. Let's annotate or map.
        
        # Actually simplest way to keep API contract without massive serializer rewrite 
        # is to keep the transformation but do it more efficiently.
        # But we can optimize the transformation.
        
        job_data = []
        for job in jobs:
             # Fast formatting
             salary_range = "Not specified"
             if job.salary_min and job.salary_max:
                 salary_range = f"${job.salary_min:,.0f} - ${job.salary_max:,.0f}"
             elif job.salary_min:
                 salary_range = f"${job.salary_min:,.0f}+"
             elif job.salary_max:
                 salary_range = f"Up to ${job.salary_max:,.0f}"
             
             # Construct dict directly to avoid serializer overhead if just reading
             job_data.append({
                'job_id': job.id,
                'employer_name': job.employer.company_name,
                'employer_id': job.employer.id,
                'employer_location': job.employer.office_location,
                'employer_industry': job.employer.get_industry_display(),
                
                'job_title': job.title,
                'job_category': job.category.name if job.category else 'Uncategorized',
                'employment_type': job.get_employment_type_display(),
                'location': job.location,
                'is_remote': job.is_remote,
                
                'salary_min': job.salary_min,
                'salary_max': job.salary_max,
                'salary_range': salary_range,
                
                'number_of_openings': job.number_of_openings,
                'skills_required': job.skills_required if job.skills_required else [],
                
                'deadline': job.deadline,
                'status': job.status,
                'posted_date': job.created_at
            })
            
        return Response({
            'count': len(job_data),
            'jobs': job_data
        }, status=status.HTTP_200_OK)
