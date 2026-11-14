from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('rental', '0017_vehicle_details_favorites')]
    operations = [
        migrations.AddField(model_name='booking', name='contact_name', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='booking', name='contact_phone', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='booking', name='pickup_notes', field=models.CharField(blank=True, max_length=1000)),
    ]
