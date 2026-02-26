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
from users.models import Resume, Document
from django.db import transaction
import uuid
import logging

logger = logging.getLogger(__name__)


import json

class ResumeGenerationPipelineView(APIView):
    """
    Generate PDF resume, upload to Cloudinary, analyze with AI, and save results
    
    All-in-one endpoint that automates the full resume workflow
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Execute full resume generation pipeline
        
        Accepts multipart/form-data:
        - data: JSON string 
        - file: Optional file upload
        
        Or application/json
        """
        # Parse input data
        raw_data = request.data
        if 'data' in raw_data and isinstance(raw_data['data'], str):
            try:
                input_data = json.loads(raw_data['data'])
            except json.JSONDecodeError:
                return Response({'error': 'Invalid JSON in data field'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            input_data = raw_data

        # Validate input
        serializer = ResumeGenerationRequestSerializer(data=input_data)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid request data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        user = request.user
        
        try:
            # Map new structure to internal domain structure (backward compatibility for PDF Gen & AI)
            personal_details = validated_data.get('personalDetails', {})
            address = personal_details.get('address', {})
            formatted_address = f"{address.get('city', '')}, {address.get('state', '')}".strip(', ')
            
            # Helper to map date strings if needed
            
            internal_data = {
                'personalInfo': {
                    'fullName': personal_details.get('fullName', ''),
                    'email': personal_details.get('emailAddress', ''),
                    'phone': personal_details.get('phoneNumber', ''),
                    'location': formatted_address,
                    # 'profilePicture': ''  # Removed
                },
                'skills': personal_details.get('skills', []),
                'education': [],
                'workExperience': [],
                'quiz_data': validated_data.get('quiz_data', {})
            }
            
            # Map Education
            for edu in validated_data.get('education', []):
                internal_data['education'].append({
                    'institutionName': edu.get('institutionName', ''),
                    'degree': edu.get('highestEducationCompleted', ''),
                    'fieldOfStudy': edu.get('program', ''),
                    'startYear': edu.get('startYear', ''),
                    'endYear': edu.get('endYear', ''),
                    'location': edu.get('location', '')
                })

            # Map Work Experience
            work_history_wrapper = validated_data.get('workHistory', {})
            if not work_history_wrapper.get('noWorkHistory', False):
                for exp in work_history_wrapper.get('experiences', []):
                    internal_data['workExperience'].append({
                        'jobTitle': exp.get('jobTitle', ''),
                        'company': exp.get('companyName', ''),
                        'location': exp.get('location', ''),
                        'startDate': exp.get('startDate', ''),
                        'endDate': exp.get('endDate', ''),
                        'current': exp.get('isCurrentlyEmployed', False),
                        'description': exp.get('responsibilitiesAndDescription', ''),
                        'responsibilities': [] # Content merged in description
                    })

            # Handle Credential File Upload
            credential_url = None
            
            if 'file' in request.FILES:
                uploaded_file = request.FILES['file']
                license_name = validated_data.get('credentialsAndLicenses', {}).get('otherLicense', 'Other License')
                logger.info(f"Saving credential file for user {user.id}")
                
                try:
                    # Create Document entry (which handles Cloudinary upload via model field)
                    doc = Document.objects.create(
                        user=user,
                        document_type='certificate',
                        file=uploaded_file,
                        filename=uploaded_file.name,
                        description=f"Uploaded via Resume Builder: {license_name}",
                        uploaded_by=user
                    )
                    credential_url = doc.file.url
                    
                    internal_data.setdefault('credentials', {})['otherLicenseFileUrl'] = credential_url
                    internal_data['credentials']['otherLicenseName'] = license_name
                    internal_data['credentials']['selectedLicenses'] = validated_data.get('credentialsAndLicenses', {}).get('selectedLicenses', [])
                except Exception as e:
                    logger.error(f"Failed to save credential document: {e}")
                    # Continue without the file if upload fails, but log it


            # Step 1: Generate PDF from resume data (using mapped internal_data)
            logger.info(f"Generating PDF for user {user.id}")
            pdf_generator = ResumePDFGenerator()
            pdf_buffer = pdf_generator.generate(internal_data)
            
            # Step 2: Upload PDF to Cloudinary
            logger.info(f"Uploading PDF to Cloudinary for user {user.id}")
            cloudinary_service = CloudinaryUploadService()
            filename = f"resume_{user.id}_{uuid.uuid4().hex[:8]}"
            upload_result = cloudinary_service.upload_resume_pdf(pdf_buffer, filename)
            
            public_id = upload_result['public_id']
            pdf_url = upload_result['secure_url']
            
            logger.info(f"PDF uploaded: {public_id}")
            
            # Step 3: Prepare data for AI analysis
            # Convert work experience to format expected by AI
            work_history_ai = []
            for exp in internal_data['workExperience']:
                work_history_ai.append({
                    'job_title': exp.get('jobTitle', ''),
                    'company': exp.get('company', ''),
                    'duration': f"{exp.get('startDate', '')} to {exp.get('endDate', 'Present')}"
                })
            
            # Use provided quiz_data or create default
            personal_info = internal_data.get('personalInfo', {})
            quiz_data = internal_data.get('quiz_data', {
                'interests': 'General',
                'work_environment': 'Flexible',
                'training_flexibility': 'Full-time',
                'strengths': 'Adaptable',
                'job_priorities': 'Career growth',
                'location': personal_info.get('location', 'Not specified')
            })
            
            # Step 4: Analyze with AI
            logger.info(f"Starting AI career analysis for user {user.id}")
            analysis_result = analyze_career_data(
                quiz_data=quiz_data,
                work_history=work_history_ai,
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
