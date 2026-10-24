
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fablabs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='fablab',
            name='is_approved',
            field=models.BooleanField(default=False, verbose_name='Approuvé par le SuperAdmin'),
        ),
        migrations.AddField(
            model_name='fablab',
            name='justification_document',
            field=models.FileField(blank=True, null=True, upload_to='justificatifs/', verbose_name='Justificatif officiel (KBIS, attestation)'),
        ),
    ]
