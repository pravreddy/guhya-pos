from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_customer_contacts'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='discount_type',
            field=models.CharField(
                choices=[('none', 'None'), ('flat', 'Flat ₹'), ('percent', 'Percent')],
                default='none', max_length=8),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_reason',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_by',
            field=models.ForeignKey(blank=True, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to=settings.AUTH_USER_MODEL),
        ),
    ]
