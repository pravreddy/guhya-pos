from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenancy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='upi_vpa',
            field=models.CharField(blank=True, default='', max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tenant',
            name='upi_payee_name',
            field=models.CharField(blank=True, default='', max_length=80),
            preserve_default=False,
        ),
    ]
