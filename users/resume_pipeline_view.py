"""
Resume Generation and AI Analysis Pipeline
Orchestrates: PDF generation → Cloudinary upload → AI analysis → Save results
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.serializers import ResumeGenerationRequestSerializer
from users.resume_pdf_generator import ResumePDFGenerator
from users.cloudinary_service import CloudinaryUploadService
from users.ai_service import analyze_career_data
from users.models import Resume
from django.db import transaction
import uuid
import logging
import json

logger = logging.getLogger(__name__)


class ResumeGenerationPipelineView(APIView):
    """
    Generate PDF resume, upload to Cloudinary, analyze with AI, and save results
    
    All-in-one endpoint that automates the full resume workflow
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Execute full resume generation pipeline
        
        Request body:
        {
            "personalInfo": {...},
            "workExperience": [...],
            "skills": [...],
            "education": [...],
            "quiz_data": {...}  // optional
        }
        
        Returns:
        {
            "resume_analysis": {...},
            "career_recommendations": [...],
            "resume_pdf_url": "...",
            "resume_id": "..."
        }
        """
        # Extract data from FormData
        try:
            # When sent via FormData, the JSON payload is usually in 'data'
            if 'data' in request.data:
                payload = json.loads(request.data['data'])
            else:
                payload = request.data
        except Exception as e:
            return Response({
                'error': 'Invalid JSON data in FormData',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate input
        serializer = ResumeGenerationRequestSerializer(data=payload)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid request data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        user = request.user
        
        # Handle optional credential file upload
        credential_file = request.FILES.get('file')
        credential_url = None
        if credential_file:
            try:
                cloudinary_service = CloudinaryUploadService()
                doc_filename = f"credential_{user.id}_{uuid.uuid4().hex[:8]}"
                # Using the existing upload_resume_pdf logic for general documents as well
                doc_upload_result = cloudinary_service.upload_resume_pdf(credential_file.read(), doc_filename)
                credential_url = doc_upload_result.get('secure_url')
                logger.info(f"Credential file uploaded: {doc_upload_result.get('public_id')}")
            except Exception as e:
                logger.warning(f"Failed to upload credential file: {e}")
        
        # Inject credential URL if obtained
        if credential_url and 'credentials' in validated_data:
            validated_data['credentials']['credential_url'] = credential_url
        elif credential_url:
            validated_data['credentials'] = {'credential_url': credential_url}
        
        try:
            # Step 1: Generate PDF from resume data
            logger.info(f"Generating PDF for user {user.id}")
            pdf_generator = ResumePDFGenerator()
            pdf_buffer = pdf_generator.generate(validated_data)
            
            # Step 2: Upload PDF to Cloudinary (pending/ folder)
            logger.info(f"Uploading PDF to Cloudinary for user {user.id}")
            cloudinary_service = CloudinaryUploadService()
            filename = f"resume_{user.id}_{uuid.uuid4().hex[:8]}"
            upload_result = cloudinary_service.upload_resume_pdf(pdf_buffer, filename)
            
            public_id = upload_result['public_id']
            pdf_url = upload_result['secure_url']
            
            logger.info(f"PDF uploaded: {public_id}")
            
            # Step 3: Prepare data for AI analysis
            # Convert work experience to format expected by AI
            work_history = []
            for exp in validated_data.get('workExperience', []):
                work_history.append({
                    'job_title': exp.get('jobTitle', ''),
                    'company': exp.get('company', ''),
                    'duration': f"{exp.get('startDate', '')} to {exp.get('endDate', 'Present')}"
                })
            
            # Use provided quiz_data or create default
            quiz_data = validated_data.get('quiz_data', {
                'interests': 'General',
                'work_environment': 'Flexible',
                'training_flexibility': 'Full-time',
                'strengths': 'Adaptable',
                'job_priorities': 'Career growth',
                'location': validated_data.get('personalInfo', {}).get('location', 'Not specified')
            })
            
            # Step 4: Analyze with AI
            logger.info(f"Starting AI career analysis for user {user.id}")
            analysis_result = analyze_career_data(
                quiz_data=quiz_data,
                work_history=work_history,
                pdf_url=pdf_url
            )
            
            # Step 5: Save results to database
            logger.info(f"Saving resume analysis for user {user.id}")
            with transaction.atomic():
                # Get or create resume
                resume, created = Resume.objects.get_or_create(user=user)
                
                # Save analysis data
                resume_analysis = analysis_result.get('resume_analysis', {})
                
                # Completeness score
                if resume_analysis.get('completeness_score') is not None:
                    resume.completeness_percentage = int(resume_analysis['completeness_score'])
                
                # Section status
                if resume_analysis.get('section_status'):
                    resume.section_status_data = resume_analysis['section_status']
                
                # Suggestions
                if resume_analysis.get('suggestions'):
                    resume.ai_suggestions = resume_analysis['suggestions']
                
                # Move PDF from pending to verified using Cloudinary
                try:
                    from core.utils import move_cloudinary_document
                    
                    move_result = move_cloudinary_document(
                        public_id=public_id,
                        user_id=str(user.id),
                        document_type='resume'
                    )
                    
                    # Use new URL after moving
                    resume.resume_pdf_url = move_result.get('secure_url', pdf_url)
                    logger.info(f"PDF moved to verified folder: {move_result['public_id']}")
                    
                except Exception as e:
                    # If move fails, use original URL
                    resume.resume_pdf_url = pdf_url
                    logger.warning(f"Cloudinary move failed, using original URL: {e}")
                
                resume.save()
            
            # Step 6: Return complete response
            return Response({
                'message': 'Resume generated and analyzed successfully',
                'resume_id': str(resume.id),
                'resume_analysis': resume_analysis,
                'career_recommendations': analysis_result.get('career_recommendations', []),
                'resume_pdf_url': resume.resume_pdf_url,
                'completeness_score': resume.completeness_percentage
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Resume generation pipeline failed for user {user.id}: {str(e)}")
            return Response({
                'error': 'Resume generation failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
