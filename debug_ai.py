"""
Debug script to test AI career analysis and show detailed error messages
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/jamil/Desktop/rbwoodruff')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings

# Test 1: Check OpenAI API Key
print("=" * 50)
print("TEST 1: OpenAI Configuration")
print("=" * 50)
api_key = settings.OPENAI_API_KEY
if api_key:
    print(f"✓ API Key found: {api_key[:15]}...")
    print(f"  Key length: {len(api_key)} characters")
else:
    print("✗ API Key not found!")
    sys.exit(1)

print(f"  Model: {settings.OPENAI_MODEL}")

# Test 2: Test OpenAI Connection
print("\n" + "=" * 50)
print("TEST 2: OpenAI API Connection")
print("=" * 50)
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    # Simple test call
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use cheaper model for testing
        messages=[{"role": "user", "content": "Say 'test successful'"}],
        max_tokens=10
    )
    print("✓ OpenAI API connection successful!")
    print(f"  Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"✗ OpenAI API error: {type(e).__name__}")
    print(f"  Message: {str(e)}")
    sys.exit(1)

# Test 3: Test PDF Download
print("\n" + "=" * 50)
print("TEST 3: PDF Download from Cloudinary")
print("=" * 50)
test_url = "https://res.cloudinary.com/dl83bpmyz/raw/upload/v1765921195/pending/jiuraxnfiu6xv1bxvap6.pdf"
try:
    import requests
    response = requests.get(test_url, timeout=10)
    print(f"✓ PDF download successful!")
    print(f"  Status: {response.status_code}")
    print(f"  Size: {len(response.content)} bytes")
    print(f"  Content-Type: {response.headers.get('Content-Type')}")
except Exception as e:
    print(f"✗ PDF download failed: {type(e).__name__}")
    print(f"  Message: {str(e)}")

# Test 4: Test PDF Parsing
print("\n" + "=" * 50)
print("TEST 4: PDF Text Extraction")
print("=" * 50)
try:
    import fitz
    import requests
    response = requests.get(test_url, timeout=10)
    pdf_doc = fitz.open(stream=response.content, filetype="pdf")
    text = ""
    for page in pdf_doc:
        text += page.get_text()
    pdf_doc.close()
    print(f"✓ PDF parsing successful!")
    print(f"  Pages: {len(pdf_doc)}")
    print(f"  Text length: {len(text)} characters")
    print(f"  Preview: {text[:200]}...")
except Exception as e:
    print(f"✗ PDF parsing failed: {type(e).__name__}")
    print(f"  Message: {str(e)}")

print("\n" + "=" * 50)
print("TESTS COMPLETE")
print("=" * 50)
