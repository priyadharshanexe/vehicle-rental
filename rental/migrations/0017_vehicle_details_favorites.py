from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('rental', '0016_validate_booking_records'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='vehicle', name='description', field=models.TextField(blank=True, max_length=3000)),
        migrations.AddField(model_name='vehicle', name='transmission', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='vehicle', name='seats', field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='vehicle', name='model_year', field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='vehicle', name='pickup_instructions', field=models.TextField(blank=True, max_length=1000)),
        migrations.CreateModel(name='Favorite', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rental.vehicle')),
        ], options={'constraints': [models.UniqueConstraint(fields=('user', 'vehicle'), name='unique_saved_vehicle')]}),
    ]
