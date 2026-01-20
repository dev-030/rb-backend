from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User, Agency, ReferredUser, CaseAssignment, AuditLog
from agency.models import AgencyCaseLoad
import random

class Command(BaseCommand):
    help = 'Seeds the database with Agency Demo Data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding Agency Data...')

        # 0. CLEANUP (Delete existing demo data to start fresh)
        self.stdout.write('Cleaning up old data...')
        AgencyCaseLoad.objects.all().delete()
        CaseAssignment.objects.all().delete()
        ReferredUser.objects.all().delete()
        AuditLog.objects.all().delete()
        # Delete demo users only
        User.objects.filter(email__startswith='user').delete()
        User.objects.filter(email__startswith='pending').delete()
        
        # 1. Create or Get Agency User
        email = 'agency_demo@example.com'
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': 'Demo Agency Admin',
                'user_type': 'agency',
                'is_active': True,
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(f'Created Agency User: {email}')
        
        # Update/Create Profile
        agency_profile, _ = Agency.objects.get_or_create(
            user=user,
            defaults={
                'agency_name': 'City Court Rehab Services',
                'agency_id': 'AGENCY-001',
                'address': '123 Court St, Metro City',
                'status': 'verified',
                'verification_documents': {}
            }
        )

        self.stdout.write('Creating Demo Users and Cases...')

        # 2. Case A: Users who ARE registered and should fail to "Active" immediately
        # We create the User first, then the AgencyCaseLoad, then Link them.
        for i in range(1, 4): # 3 Active Users
            u_email = f'user{i}@example.com'
            u_name = f'Active User {i}'
            
            # Create User
            u, _ = User.objects.get_or_create(
                email=u_email,
                defaults={
                    'full_name': u_name,
                    'user_type': 'agency_referred',
                    'is_active': True
                }
            )
            if _:
                u.set_password('password123')
                u.save()

            # Create AgencyCaseLoad (The "Upload")
            case_id = f'CASE-ACT-{100+i}'
            case_load = AgencyCaseLoad.objects.create(
                agency=agency_profile,
                case_id=case_id,
                email=u_email,
                court_name='City Court',
                court_date=timezone.now().date(),
                status='on_track',
                is_registered=True, # We mimic the matching logic
                matched_user=u
            )

            # Create the Linkages (ReferredUser + Assignment)
            ref_user, _ = ReferredUser.objects.get_or_create(
                user=u,
                defaults={
                    'court_name': 'City Court',
                    'case_id': case_id,
                    'phone_number': '555-0100'
                }
            )
            CaseAssignment.objects.create(
                referred_user=ref_user,
                agency=agency_profile,
                case_id=case_id,
                court_date=timezone.now().date(),
                compliance_status='on_track'
            )

        # 3. Case B: Users who are NOT registered (Pending)
        # We only create AgencyCaseLoad. No User, No ReferredUser.
        for i in range(1, 4): # 3 Pending Cases
            p_email = f'pending{i}@example.com'
            p_case_id = f'CASE-PEN-{200+i}'
            
            AgencyCaseLoad.objects.create(
                agency=agency_profile,
                case_id=p_case_id,
                email=p_email,
                court_name='City Court',
                court_date=timezone.now().date(),
                status='on_track', # Status in CSV
                is_registered=False,
                matched_user=None
            )

        # 4. Create Audit Logs
        actions = ['case_assigned', 'report_generated', 'compliance_updated', 'document_uploaded']
        for i in range(5):
            AuditLog.objects.create(
                admin_user=user,
                action=random.choice(actions),
                details={'info': f'Demo action {i}'},
                ip_address='127.0.0.1'
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded agency data: 3 Active Users, 3 Pending Cases'))
