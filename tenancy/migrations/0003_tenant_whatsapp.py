from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0002_tenant_upi'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='whatsapp_number',
            field=models.CharField(blank=True, default='', max_length=20),
            preserve_default=False,
        ),
    ]
