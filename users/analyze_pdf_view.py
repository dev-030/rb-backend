"""
Simple Resume PDF URL Analysis
Just analyze PDF from URL - no database saves, just return analysis
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from users.ai_service import analyze_career_data
import logging

logger = logging.getLogger(__name__)


class ResumePDFURLSerializer(serializers.Serializer):
    """Serializer for PDF URL analysis request"""
    url = serializers.URLField(help_text="URL of the resume PDF")
    public_id = serializers.CharField(required=False, allow_blank=True, help_text="Optional Cloudinary public_id")


class AnalyzeResumePDFView(APIView):
    """
    Analyze resume PDF from URL - returns only analysis, doesn't save
    
    Simple endpoint: provide PDF URL, get analysis back
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Analyze resume PDF from URL
        
        Request body:
        {
            "url": "https://cloudinary-url.pdf",
            "public_id": "optional-cloudinary-public-id"
        }
        
        Returns:
        {
            "resume_analysis": {...},
            "career_recommendations": [...],
            "resume_pdf_url": "...",
            "resume_public_id": "..."
        }
        """
        # Validate input
        serializer = ResumePDFURLSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid request data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        pdf_url = serializer.validated_data['url']
        public_id = serializer.validated_data.get('public_id', '')
        
        try:
            # Use minimal quiz and work history for analysis
            quiz_data = {
                'interests': 'General',
                'work_environment': 'Flexible',
                'training_flexibility': 'Full-time',
                'strengths': 'Adaptable',
                'job_priorities': 'Career growth',
                'location': 'Flexible'
            }
            
            work_history = []
            
            # Analyze with AI using OLD function (returns categories)
            logger.info(f"Analyzing PDF from URL: {pdf_url}")
            analysis_result = analyze_career_data(
                quiz_data=quiz_data,
                work_history=work_history,
                pdf_url=pdf_url
            )
            
            # Add URL and public_id to response
            analysis_result['resume_pdf_url'] = pdf_url
            analysis_result['resume_public_id'] = public_id
            
            return Response(analysis_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"PDF analysis failed: {str(e)}", exc_info=True)
            return Response({
                'error': 'PDF analysis failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
