"""
Cloudinary Upload Service
Upload PDFs to Cloudinary pending/ folder
"""

import cloudinary
import cloudinary.uploader
from django.conf import settings


class CloudinaryUploadService:
    """Handle Cloudinary uploads for resume PDFs"""
    
    @staticmethod
    def upload_resume_pdf(pdf_buffer, filename='resume'):
        """
        Upload PDF to Cloudinary pending/ folder
        
        Uses resource_type='image' for preview support
        
        Args:
            pdf_buffer: BytesIO object containing PDF data
            filename: Base filename (without extension)
            
        Returns:
            dict: {'public_id': '...', 'url': '...', 'secure_url': '...'}
        """
        try:
            # Upload as image for preview support (Cloudinary can preview PDFs this way)
            result = cloudinary.uploader.upload(
                pdf_buffer,
                folder='pending',
                resource_type='image',  # Changed from 'raw' to enable preview
                format='pdf',  # Specify PDF format
                public_id=filename,
                upload_preset='registration_uploads',
                tags=['registration_uploads'],
                overwrite=True
            )
            
            return {
                'public_id': result.get('public_id'),
                'url': result.get('url'),
                'secure_url': result.get('secure_url')
            }
            
        except Exception as e:
            raise Exception(f"Cloudinary upload failed: {str(e)}")
