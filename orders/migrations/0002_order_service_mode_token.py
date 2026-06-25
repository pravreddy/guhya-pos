from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="service_mode",
            field=models.CharField(
                choices=[("dine_in", "Dine-in"), ("takeaway", "Takeaway")],
                default="dine_in",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="token",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
