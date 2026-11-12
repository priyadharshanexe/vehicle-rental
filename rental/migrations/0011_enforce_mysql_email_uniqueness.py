from django.db import migrations


def add_mysql_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute("""
        ALTER TABLE account_emailaddress
        ADD COLUMN rental_primary_user BIGINT
            GENERATED ALWAYS AS (CASE WHEN `primary` THEN user_id END) STORED,
        ADD COLUMN rental_verified_email VARCHAR(254)
            GENERATED ALWAYS AS (CASE WHEN verified THEN email END) STORED,
        ADD UNIQUE INDEX rental_unique_primary_email (rental_primary_user),
        ADD UNIQUE INDEX rental_unique_verified_email (rental_verified_email)
    """)


def remove_mysql_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute("""
        ALTER TABLE account_emailaddress
        DROP INDEX rental_unique_primary_email,
        DROP INDEX rental_unique_verified_email,
        DROP COLUMN rental_primary_user,
        DROP COLUMN rental_verified_email
    """)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("account", "0009_emailaddress_unique_primary_email"),
        ("rental", "0010_link_django_accounts"),
    ]

    operations = [
        migrations.RunPython(add_mysql_constraints, remove_mysql_constraints),
    ]
