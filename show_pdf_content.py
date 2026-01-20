"""
Show what was extracted from the PDF to prove it was read
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/jamil/Desktop/rbwoodruff')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.ai_service import PDFParser

pdf_url = "https://res.cloudinary.com/dl83bpmyz/raw/upload/v1765921195/pending/jiuraxnfiu6xv1bxvap6.pdf"

print("=" * 60)
print("PDF CONTENT EXTRACTION TEST")
print("=" * 60)

try:
    print(f"\n1. Downloading PDF from: {pdf_url}\n")
    
    parser = PDFParser()
    text = parser.download_and_extract_text(pdf_url)
    
    print("✓ PDF downloaded and parsed successfully!")
    print(f"\n2. Extracted Text Length: {len(text)} characters")
    print(f"\n3. First 1000 characters of extracted text:")
    print("=" * 60)
    print(text[:1000])
    print("=" * 60)
    
    if len(text) > 1000:
        print(f"\n4. Last 500 characters:")
        print("=" * 60)
        print(text[-500:])
        print("=" * 60)
    
    print(f"\n✓ SUCCESS - PDF was fully read and text extracted!")
    print(f"\nTotal content: {len(text)} characters from the resume")
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
