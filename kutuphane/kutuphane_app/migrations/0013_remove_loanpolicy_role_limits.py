from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0012_roleloanpolicy"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="loanpolicy",
            name="role_limits",
        ),
    ]
