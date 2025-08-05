from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('canteen_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='khalti_pidx',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='khalti_transaction_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='timestamp',
            new_name='created_at',
        ),
        migrations.AddField(
            model_name='payment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ] 