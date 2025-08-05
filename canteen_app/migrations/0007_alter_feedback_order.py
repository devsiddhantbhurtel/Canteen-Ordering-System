from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('canteen_app', '0006_alter_order_id_alter_order_payment_method_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedback',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedbacks', to='canteen_app.order'),
        ),
    ] 