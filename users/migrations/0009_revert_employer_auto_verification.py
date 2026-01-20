from django.db import migrations


def unverify_employers(apps, schema_editor):
    """Revert auto-verification - set employers back to unverified"""
    Employer = apps.get_model('users', 'Employer')
    
    # Set all employers back to unverified (they need admin approval)
    verified_employers = Employer.objects.filter(is_verified=True)
    count = verified_employers.count()
    
    if count > 0:
        verified_employers.update(
            is_verified=False,
            verification_date=None
        )
        print(f"Reverted auto-verification for {count} employer(s) - they now require admin approval")


def reverse_unverify(apps, schema_editor):
    """Reverse the unverification (for rollback)"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_verify_employers'),
    ]

    operations = [
        migrations.RunPython(unverify_employers, reverse_unverify),
    ]
