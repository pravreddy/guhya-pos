from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='customer',
            name='telegram',
            field=models.CharField(blank=True, default='', max_length=64),
            preserve_default=False,
        ),
    ]
