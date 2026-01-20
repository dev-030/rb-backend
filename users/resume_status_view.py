"""
Resume Completeness Status API

GET: View current resume status
POST: Save AI analysis results to user's resume
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import Resume, Document
from django.utils import timezone


class ResumeCompletenessView(APIView):
    """
    GET: View resume completeness status
    POST: Save AI analysis results
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current resume completeness status - returns exactly what was saved"""
        user = request.user
        
        try:
            resume = Resume.objects.get(user=user)
        except Resume.DoesNotExist:
            return Response({
                'error': 'No resume found. Please create your resume first.',
                'has_resume': False
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Return exactly what was saved - no calculations
        response_data = {
            'resume_id': str(resume.id),
            'completeness_score': resume.completeness_percentage,
            'section_status': resume.section_status_data or {},
            'resume_pdf_url': resume.resume_pdf_url or None,
            'last_updated': resume.updated_at,
            'suggestions': resume.ai_suggestions or []
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """
        Save AI analysis results and move PDF from pending to permanent folder
        
        Request body:
        {
            "resume_analysis": {...},
            "resume_pdf_url": "...",
            "resume_public_id": "pending/xyz123"
        }
        """
        user = request.user
        data = request.data
        
        # Get or create resume
        resume, created = Resume.objects.get_or_create(user=user)
        
        # Extract resume analysis
        resume_analysis = data.get('resume_analysis', {})
        
        if not resume_analysis:
            return Response({
                'error': 'resume_analysis is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Save completeness score
        completeness_score = resume_analysis.get('completeness_score')
        if completeness_score is not None:
            resume.completeness_percentage = int(completeness_score)
        
        # Save section status (AI's assessment)
        section_status = resume_analysis.get('section_status')
        if section_status:
            resume.section_status_data = section_status
        
        # Save AI suggestions
        suggestions = resume_analysis.get('suggestions')
        if suggestions:
            resume.ai_suggestions = suggestions
        
        # Move PDF in Cloudinary if public_id provided
        public_id = data.get('resume_public_id')
        pdf_url = data.get('resume_pdf_url')
        
        if public_id:
            try:
                from core.utils import move_cloudinary_document
                
                # Move from pending/ to verified/{user_id}/
                result = move_cloudinary_document(
                    public_id=public_id,
                    user_id=str(user.id),
                    document_type='resume'
                )
                
                # Use the new secure URL after moving
                resume.resume_pdf_url = result.get('secure_url', pdf_url)
                
            except Exception as e:
                # If move fails, still save with original URL
                resume.resume_pdf_url = pdf_url
                print(f"Cloudinary move failed: {e}")
        elif pdf_url:
            # No public_id provided, just save URL as-is
            resume.resume_pdf_url = pdf_url
        
        # Save to resume
        resume.save()
        
        return Response({
            'message': 'Resume analysis saved successfully',
            'resume_id': str(resume.id),
            'completeness_score': resume.completeness_percentage,
            'resume_pdf_url': resume.resume_pdf_url,
            'updated_at': resume.updated_at
        }, status=status.HTTP_200_OK)
    
    def _check_personal_info(self, resume):
        """Check if personal information is complete"""
        if resume.phone and resume.summary:
            return 'complete'
        return 'incomplete'
    
    def _check_education(self, resume):
        """Check if education section has entries"""
        if resume.education_entries.exists():
            return 'complete'
        return 'incomplete'
    
    def _check_work_experience(self, resume):
        """Check if work experience section has entries"""
        if resume.work_experiences.exists():
            return 'complete'
        return 'incomplete'
    
    def _check_skills(self, resume):
        """Check if skills section has entries"""
        if resume.skills.exists():
            return 'complete'
        return 'incomplete'
    
    def _generate_suggestions(self, section_status):
        """Generate suggestions for incomplete sections"""
        suggestions = []
        
        if section_status['personal_info'] == 'incomplete':
            suggestions.append('Add your phone number and professional summary')
        
        if section_status['education'] == 'incomplete':
            suggestions.append('Add your education history')
        
        if section_status['work_experience'] == 'incomplete':
            suggestions.append('Add your work experience')
        
        if section_status['skills'] == 'incomplete':
            suggestions.append('Add your skills and proficiencies')
        
        if not suggestions:
            suggestions.append('Your resume is complete!')
        
        return suggestions
