from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('canteen_app', '0005_merge_0002_payment_updates_0004_userprofile_contact'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='rfid_id',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='last_rfid_scan',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ] 