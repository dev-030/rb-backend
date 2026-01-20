from django.db import migrations
from django.utils import timezone


def auto_verify_employers(apps, schema_editor):
    """Auto-verify all existing unverified employers"""
    Employer = apps.get_model('users', 'Employer')
    
    unverified_employers = Employer.objects.filter(is_verified=False)
    count = unverified_employers.count()
    
    if count > 0:
        unverified_employers.update(
            is_verified=True,
            verification_date=timezone.now()
        )
        print(f"Auto-verified {count} existing employer(s)")


def reverse_verification(apps, schema_editor):
    """Reverse the auto-verification (for rollback)"""
    # Don't actually reverse - we want to keep employers verified
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_add_ai_analysis_fields'),  # Update this to your latest migration
    ]

    operations = [
        migrations.RunPython(auto_verify_employers, reverse_verification),
    ]
