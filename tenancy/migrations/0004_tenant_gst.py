from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0003_tenant_whatsapp'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='gst_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='tenant',
            name='default_gst_rate',
            field=models.DecimalField(decimal_places=2, default=5, max_digits=5),
        ),
    ]
