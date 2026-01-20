# Generated manually for compliance_models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_rename_case_name_to_case_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='caseassignment',
            name='compliance_status',
            field=models.CharField(
                choices=[
                    ('on_track', 'On Track'), 
                    ('delayed', 'Delayed'), 
                    ('non_compliant', 'Non-Compliant'), 
                    ('completed', 'Completed'), 
                    ('closed', 'Closed')
                ],
                default='on_track',
                max_length=20
            ),
        ),
    ]
