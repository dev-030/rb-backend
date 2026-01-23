
import os
import django
import threading
import time
from unittest.mock import patch, MagicMock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from authentication.email_service import send_email_thread
from users.views import JobListView, TrainingProgramListView
from users.models import Job, TrainingProgram, JobApplication, Enrollment
from users.serializers import JobSerializer, TrainingProgramSerializer

User = get_user_model()

def test_async_email():
    print("\n--- Testing Async Email ---")
    with patch('authentication.email_service.send_mail') as mock_send_mail:
        thread = threading.Thread(
            target=send_email_thread, 
            args=('Test', 'Body', 'from@example.com', ['to@example.com'])
        )
        thread.start()
        thread.join()
        
        if mock_send_mail.called:
            print("✅ Email sent successfully via thread.")
        else:
            print("❌ Email was NOT sent.")

def test_job_list_queries():
    print("\n--- Testing JobListView Query Count ---")
    factory = RequestFactory()
    request = factory.get('/jobs/')
    request.query_params = request.GET
    
    # Create a dummy user
    user = User(email='test@example.com', user_type='general')
    # user.is_authenticated is True by default for User instances

    request.user = user
    
    view = JobListView()
    view.request = request
    
    # Mock queryset to avoid hitting real DB if empty, but we want to inspect the query structure primarily
    # However, to test query counting we need real DB access or mock the DB cursor.
    # checking the select_related/annotate is present in get_queryset result is safer here.
    
    qs = view.get_queryset()
    print(f"Query: {str(qs.query)}")
    
    if 'select_related' in str(qs.query) or 'INNER JOIN "employer_employerprofile"' in str(qs.query): # Check for join
         print("✅ Job queryset has JOINs (select_related).")
    else:
         print("❌ Job queryset missing JOINs.")
         
    if 'EXISTS' in str(qs.query):
        print("✅ Job queryset has EXISTS subquery for has_applied.")
    else:
        print("❌ Job queryset missing EXISTS subquery.")


def test_training_list_queries():
    print("\n--- Testing TrainingProgramListView Query Count ---")
    factory = RequestFactory()
    request = factory.get('/trainings/')
    request.query_params = request.GET
    
    user = User(email='test@example.com', user_type='general')
    # user.is_authenticated is True by default for User instances

    request.user = user
    
    view = TrainingProgramListView()
    view.request = request
    
    qs = view.get_queryset()
    print(f"Query: {str(qs.query)}")
    
    if 'INNER JOIN "trainer_trainerprofile"' in str(qs.query): 
         print("✅ Training queryset has JOINs.")
    else:
         print("❌ Training queryset missing JOINs.")

    if 'EXISTS' in str(qs.query):
        print("✅ Training queryset has EXISTS subquery for is_enrolled.")
    else:
        print("❌ Training queryset missing EXISTS subquery.")


if __name__ == "__main__":
    try:
        test_async_email()
        test_job_list_queries()
        test_training_list_queries()
        print("\n✅ Verification Script Completed.")
    except Exception as e:
        print(f"\n❌ Verification Script Failed: {e}")
