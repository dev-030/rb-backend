# Generated migration for renaming case_name to case_id

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_agency_status_field'),
    ]

    operations = [
        migrations.RenameField(
            model_name='referreduser',
            old_name='case_name',
            new_name='case_id',
        ),
    ]
