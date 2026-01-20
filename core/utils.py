import cloudinary
import cloudinary.uploader
from django.conf import settings
import random
import string
from django.utils import timezone
from datetime import timedelta


def generate_otp(length=6):
    """Generate a random numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


def calculate_resume_completeness(resume):
    """
    Calculate resume completion percentage based on filled sections
    Returns an integer from 0 to 100
    """
    if not resume:
        return 0
    
    total_sections = 8
    completed_sections = 0
    
    # Check each section
    if resume.summary:
        completed_sections += 1
    if resume.phone:
        completed_sections += 1
    if resume.work_experiences.exists():
        completed_sections += 1
    if resume.education_entries.exists():
        completed_sections += 1
    if resume.skills.exists():
        completed_sections += 1
    if resume.linkedin_url:
        completed_sections += 1
    if resume.user.documents.filter(document_type='resume_pdf').exists():
        completed_sections += 1
    if resume.portfolio_url:
        completed_sections += 1
    
    return int((completed_sections / total_sections) * 100)


def parse_resume_pdf(pdf_file):
    """
    Parse uploaded PDF resume and extract structured data
    Returns a dictionary with extracted information
    """
    try:
        import PyPDF2
        from io import BytesIO
        
        # Read PDF
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
        text = ""
        
        # Extract text from all pages
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        # Basic extraction (this is simplified - in production, use NLP/AI)
        extracted_data = {
            'full_text': text,
            'summary': '',
            'work_experiences': [],
            'education': [],
            'skills': [],
            'contact': {}
        }
        
        # Extract email
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            extracted_data['contact']['email'] = emails[0]
        
        # Extract phone (basic US/international format)
        phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
        phones = re.findall(phone_pattern, text)
        if phones:
            extracted_data['contact']['phone'] = phones[0]
        
        # TODO: Implement more sophisticated parsing for:
        # - Work experience sections
        # - Education sections
        # - Skills extraction
        # Consider using libraries like spaCy, or OpenAI API for better accuracy
        
        return extracted_data
        
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return None


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_otp_valid(otp_instance):
    """Check if an OTP is still valid"""
    from django.conf import settings
    
    expiry_minutes = getattr(settings, 'OTP_VALIDITY_DURATION', 5)
    expiry_time = otp_instance.created_at + timedelta(minutes=expiry_minutes)
    
    return timezone.now() <= expiry_time


def generate_receipt_number():
    """Generate unique receipt number for payments"""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"REC-{timestamp}-{random_suffix}"




def move_cloudinary_document(public_id, user_id, document_type='verification'):
    """
    Move document from pending/ to verified/ folder in Cloudinary
    
    Structure: 
    - verified/documents/ - for signup/verification documents
    - verified/resume/ - for resume PDFs
    """
    try:
        # Extract just the filename without folder path
        filename = public_id.split('/')[-1]
        
        # Determine subfolder based on document type
        if document_type == 'resume':
            subfolder = 'resume'
        else:
            subfolder = 'documents'
        
        # New path: verified/subfolder/filename
        new_public_id = f"verified/{subfolder}/{filename}"
        
        result = cloudinary.uploader.rename(
            public_id,
            new_public_id,
            resource_type='image',  # Changed from 'raw' to 'image' for preview
            invalidate=True,  
            overwrite=False  
        )
        
        # Update tags to match registration flow
        cloudinary.uploader.add_tag('registration_uploads', [new_public_id], resource_type='image')
        cloudinary.uploader.remove_tag('temp', [new_public_id], resource_type='image')
        
        return {
            'public_id': result.get('public_id'),
            'url': result.get('url'),
            'secure_url': result.get('secure_url')
        }
        
    except Exception as e:
        raise Exception(f"Failed to move document in Cloudinary: {str(e)}")
