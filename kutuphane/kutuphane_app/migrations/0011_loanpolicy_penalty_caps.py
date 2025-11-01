from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0010_loanpolicy"),
    ]

    operations = [
        migrations.AddField(
            model_name="loanpolicy",
            name="penalty_max_per_loan",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name="loanpolicy",
            name="penalty_max_per_student",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
