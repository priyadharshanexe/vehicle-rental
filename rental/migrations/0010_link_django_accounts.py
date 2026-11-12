import uuid

from django.conf import settings
from django.db import migrations, models
from django.db.models import deletion


def link_legacy_accounts(apps, schema_editor):
    profile_model = apps.get_model("rental", "CustomUser")
    account_model = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    alias = schema_editor.connection.alias
    for profile in profile_model.objects.using(alias).iterator():
        account = account_model.objects.using(alias).create(
            username=f"rental-{uuid.uuid4().hex}",
            email=profile.email,
            first_name=profile.name[:150],
            password="!",
        )
        profile.account_id = account.pk
        profile.save(using=alias, update_fields=["account"])


class Migration(migrations.Migration):
    dependencies = [
        ("rental", "0009_feedback"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="account",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=deletion.PROTECT,
                related_name="rental_profile", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(link_legacy_accounts),
        migrations.RemoveField(model_name="customuser", name="password"),
        migrations.AlterField(model_name="customuser", name="email", field=models.EmailField(max_length=254)),
    ]
