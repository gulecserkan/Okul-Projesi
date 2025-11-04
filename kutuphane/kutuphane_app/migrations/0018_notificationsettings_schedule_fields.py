from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("kutuphane_app", "0017_notificationsettings"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE kutuphane_app_notificationsettings
                    ADD COLUMN IF NOT EXISTS email_schedule_enabled boolean NOT NULL DEFAULT false,
                    ADD COLUMN IF NOT EXISTS email_schedule_hour smallint NOT NULL DEFAULT 9,
                    ADD COLUMN IF NOT EXISTS email_schedule_minute smallint NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS email_schedule_timezone varchar(64) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS sms_schedule_enabled boolean NOT NULL DEFAULT false,
                    ADD COLUMN IF NOT EXISTS sms_schedule_hour smallint NOT NULL DEFAULT 9,
                    ADD COLUMN IF NOT EXISTS sms_schedule_minute smallint NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS sms_schedule_timezone varchar(64) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS mobile_schedule_enabled boolean NOT NULL DEFAULT false,
                    ADD COLUMN IF NOT EXISTS mobile_schedule_hour smallint NOT NULL DEFAULT 9,
                    ADD COLUMN IF NOT EXISTS mobile_schedule_minute smallint NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS mobile_schedule_timezone varchar(64) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS overdue_last_run date,
                    ADD COLUMN IF NOT EXISTS email_schedule_last_run timestamp with time zone,
                    ADD COLUMN IF NOT EXISTS sms_schedule_last_run timestamp with time zone,
                    ADD COLUMN IF NOT EXISTS mobile_schedule_last_run timestamp with time zone,
                    ADD COLUMN IF NOT EXISTS due_reminder_email_enabled boolean NOT NULL DEFAULT true,
                    ADD COLUMN IF NOT EXISTS due_reminder_sms_enabled boolean NOT NULL DEFAULT true,
                    ADD COLUMN IF NOT EXISTS due_reminder_mobile_enabled boolean NOT NULL DEFAULT true,
                    ADD COLUMN IF NOT EXISTS overdue_email_enabled boolean NOT NULL DEFAULT true,
                    ADD COLUMN IF NOT EXISTS overdue_sms_enabled boolean NOT NULL DEFAULT true,
                    ADD COLUMN IF NOT EXISTS overdue_mobile_enabled boolean NOT NULL DEFAULT true;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
