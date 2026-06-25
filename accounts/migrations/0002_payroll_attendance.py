import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('tenancy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='wage_type',
            field=models.CharField(choices=[('monthly', 'Monthly salary'), ('daily', 'Daily wage'), ('hourly', 'Hourly wage')], default='monthly', max_length=10),
        ),
        migrations.AddField(
            model_name='user',
            name='wage_rate',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='user',
            name='attendance_pin',
            field=models.CharField(blank=True, default='', max_length=6),
        ),
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clock_in', models.DateTimeField()),
                ('clock_out', models.DateTimeField(blank=True, null=True)),
                ('source', models.CharField(default='manual', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance', to='accounts.user')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tenancy.tenant')),
            ],
            options={
                'ordering': ['-clock_in'],
            },
        ),
    ]
