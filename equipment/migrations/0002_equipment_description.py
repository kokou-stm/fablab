
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='description',
            field=models.TextField(blank=True, verbose_name='Description / Caractéristiques'),
        ),
    ]
