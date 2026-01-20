#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from users.models import ReferredUser, CaseAssignment

print('=== Database Check ===')
print(f'\nTotal ReferredUsers: {ReferredUser.objects.count()}')
print(f'Total CaseAssignments: {CaseAssignment.objects.count()}')

print('\n=== ReferredUser Details ===')
for ru in ReferredUser.objects.all():
    has_case = CaseAssignment.objects.filter(referred_user=ru).exists()
    print(f'\nUser: {ru.user.email}')
    print(f'  - Court Name: {ru.court_name}')
    print(f'  - Case ID: {ru.case_id}')
    print(f'  - Has CaseAssignment: {has_case}')
    
    if has_case:
        case = CaseAssignment.objects.get(referred_user=ru)
        print(f'  - Agency: {case.agency.agency_name}')
        print(f'  - Agency Case ID: {case.case_id}')

print('\n=== Agency Users ===')
from users.models import Agency
for agency in Agency.objects.all():
    print(f'\nAgency: {agency.agency_name} ({agency.user.email})')
    assigned_cases = CaseAssignment.objects.filter(agency=agency).count()
    print(f'  - Assigned Cases: {assigned_cases}')
