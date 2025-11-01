from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0013_remove_loanpolicy_role_limits"),
    ]

    operations = [
        migrations.AddField(
            model_name="roleloanpolicy",
            name="penalty_max_per_loan",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="roleloanpolicy",
            name="penalty_max_per_student",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
    ]
