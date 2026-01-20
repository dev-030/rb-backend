"""
Test the full career analysis flow with actual data
"""
import os
import sys
import django
import json

# Setup Django
sys.path.insert(0, '/home/jamil/Desktop/rbwoodruff')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.ai_service import analyze_career_data

# Test data based on user's example
quiz_data = {
    "interests": "Working with technology",
    "work_environment": "Indoors",
    "training_flexibility": "3-6 months",
    "strengths": "Technical or computer skills",
    "job_priorities": "High salary potential",
    "location": "Online / Remote-friendly"
}

work_history = [
    {
        "job_title": "Sales Manager",
        "company_name": "Upwork",
        "location": "New York, USA",
        "start_date": "2023-03-12",
        "end_date": "2025-03-12",
        "currently_employed": False,
        "responsibilities": "Managed client relationships and sales pipelines..."
    }
]

pdf_url = "https://res.cloudinary.com/dl83bpmyz/raw/upload/v1765921195/pending/jiuraxnfiu6xv1bxvap6.pdf"

print("=" * 60)
print("TESTING FULL CAREER ANALYSIS FLOW")
print("=" * 60)

try:
    print("\n1. Starting analysis...")
    result = analyze_career_data(quiz_data, work_history, pdf_url)
    
    print("\n2. Analysis complete!")
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    
    print("\n✓ SUCCESS - Career analysis completed successfully!")
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}")
    print(f"Message: {str(e)}")
    
    # Show stack trace for debugging
    import traceback
    print("\nFull traceback:")
    print(traceback.format_exc())
