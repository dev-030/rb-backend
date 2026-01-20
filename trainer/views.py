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
        
        all_enrollments = Enrollment.objects.filter(program__provider=provider)
        
        stats = {
            'total_learners': all_enrollments.values('user').distinct().count(),
            'active_learners': all_enrollments.filter(
                status__in=['enrolled', 'in_progress']
            ).values('user').distinct().count(),
            'completed_learners': all_enrollments.filter(
                status='completed'
            ).values('user').distinct().count(),
            'pending_enrollments': all_enrollments.filter(status='enrolled').count(),
            'average_completion_rate': 0.0,
            'pending_certificate_verifications': Certificate.objects.filter(
                enrollment__program__provider=provider,
                verification_status='pending'
            ).count()
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
            Enrollment,
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
        ).order_by('-uploaded_at')


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
        programs = TrainingProgram.objects.filter(provider=provider)
        
        # Learners by program
        learners_by_program = []
        for program in programs:
            learners_by_program.append({
                'program_name': program.name,
                'total_learners': program.enrollments.count(),
                'active': program.enrollments.filter(status__in=['enrolled', 'in_progress']).count(),
                'completed': program.enrollments.filter(status='completed').count()
            })
        
        # Completion rates
        completion_rates = []
        for program in programs:
            total = program.enrollments.count()
            completed = program.enrollments.filter(status='completed').count()
            rate = (completed / total * 100) if total > 0 else 0
            completion_rates.append({
                'program_name': program.name,
                'completion_rate': round(rate, 2)
            })
            
        # Category Demand Analysis
        from users.models import Category
        category_demand = []
        all_categories = Category.objects.all()
        
        # Count enrollments per category (for this provider's programs)
        category_counts = {}
        max_enrollments = 0
        
        for category in all_categories:
            count = Enrollment.objects.filter(
                program__provider=provider,
                program__category=category
            ).count()
            category_counts[category.name] = count
            if count > max_enrollments:
                max_enrollments = count
        
        # Determine demand level
        for category_name, count in category_counts.items():
            demand_level = "Low"
            if max_enrollments > 0:
                ratio = count / max_enrollments
                if ratio > 0.66:
                    demand_level = "High"
                elif ratio > 0.33:
                    demand_level = "Medium"
            
            # Only show categories with activity or if explicitly requested "all"
            # User said "return all the categorys". So we return all.
            category_demand.append({
                'category_name': category_name,
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
        ).order_by('-created_at')


class JobOpportunitiesView(APIView):
    """List all active job opportunities with employer details"""
    permission_classes = [IsAuthenticated, IsTrainingProvider]
    
    def get(self, request):
        from users.models import Job
        
        # Get all active jobs
        jobs = Job.objects.filter(
            status='active'
        ).select_related('employer', 'employer__user', 'category').order_by('-created_at')
        
        job_data = []
        for job in jobs:
            # Format salary range
            if job.salary_min and job.salary_max:
                salary_range = f"${job.salary_min:,.0f} - ${job.salary_max:,.0f}"
            elif job.salary_min:
                salary_range = f"${job.salary_min:,.0f}+"
            elif job.salary_max:
                salary_range = f"Up to ${job.salary_max:,.0f}"
            else:
                salary_range = "Not specified"
            
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
        
        from .serializers import JobOpportunitiesSerializer
        serializer = JobOpportunitiesSerializer(job_data, many=True)
        return Response({
            'count': len(job_data),
            'jobs': serializer.data
        }, status=status.HTTP_200_OK)
