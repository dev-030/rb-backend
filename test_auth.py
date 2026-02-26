import sys
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import RequestFactory
from users.views import JobListView
from rest_framework.request import Request

factory = RequestFactory()
request = factory.get('/api/users/jobs/')
view = JobListView.as_view()
response = view(request)
print('STATUS:', response.status_code)
print('DATA:', response.data)
