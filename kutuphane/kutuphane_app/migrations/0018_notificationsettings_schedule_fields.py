from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0017_notificationsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationsettings",
            name="email_schedule_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="email_schedule_hour",
            field=models.PositiveSmallIntegerField(default=9),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="email_schedule_minute",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="email_schedule_timezone",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="sms_schedule_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="sms_schedule_hour",
            field=models.PositiveSmallIntegerField(default=9),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="sms_schedule_minute",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="sms_schedule_timezone",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="mobile_schedule_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="mobile_schedule_hour",
            field=models.PositiveSmallIntegerField(default=9),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="mobile_schedule_minute",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="mobile_schedule_timezone",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="overdue_last_run",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="email_schedule_last_run",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="sms_schedule_last_run",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="mobile_schedule_last_run",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="due_reminder_email_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="due_reminder_sms_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="due_reminder_mobile_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="overdue_email_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="overdue_sms_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="overdue_mobile_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
