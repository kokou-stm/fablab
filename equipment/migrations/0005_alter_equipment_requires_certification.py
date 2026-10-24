
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0004_equipment_doc_file_equipment_doc_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipment',
            name='requires_certification',
            field=models.BooleanField(default=False, verbose_name='Nécessite une Habilitation/Formation'),
        ),
    ]
