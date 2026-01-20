"""
Test resume generation pipeline
"""
import os
os.environ.setdefault('DJANGO_SETUP_COMPLETE', '1')

import django
django.setup()

from users.resume_pdf_generator import ResumePDFGenerator

# Sample resume data
sample_data = {
    "personalInfo": {
        "fullName": "Sally Branders",
        "email": "sally@example.com",
        "location": "NY, USA",
        "dateOfBirth": "1990-11-18"
    },
    "workExperience": [
        {
            "jobTitle": "Senior UI/UX Designer",
            "company": "Tech Corp",
            "location": "NY, USA",
            "startDate": "2018-01-01",
            "endDate": "2023-12-31",
            "current": False,
            "responsibilities": [
                "Led design team of 5 designers",
                "Created design system used across 10+ products",
                "Increased user engagement by 45%"
            ],
            "description": "Led user experience initiatives for enterprise software."
        }
    ],
    "skills": ["Figma", "Adobe XD", "React", "TypeScript", "User Research"],
    "education": [
        {
            "institutionName": "Victoria University",
            "degree": "Bachelor's Degree",
            "fieldOfStudy": "Computer Science",
            "grade": "3.8 GPA",
            "startYear": "2014",
            "endYear": "2018",
            "current": False
        }
    ]
}

try:
    print("Generating PDF resume...")
    generator = ResumePDFGenerator()
    pdf_buffer = generator.generate(sample_data)
    
    # Save to file for inspection
    with open('/tmp/test_resume.pdf', 'wb') as f:
        f.write(pdf_buffer.getvalue())
    
    print(f"✓ PDF generated successfully!")
    print(f"  Saved to: /tmp/test_resume.pdf")
    print(f"  Size: {len(pdf_buffer.getvalue())} bytes")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
