import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.views import InterviewAndRejectedApplicationsView
from authentication.models import UserAccount
from rest_framework.test import APIRequestFactory

user = UserAccount.objects.first()

class TestView(InterviewAndRejectedApplicationsView):
    permission_classes = []
    authentication_classes = []

factory = APIRequestFactory()
request = factory.get('/')
request.user = user

view = TestView.as_view()
try:
    response = view(request)
    print("SUCCESS", response.data)
except Exception as e:
    import traceback
    traceback.print_exc()
