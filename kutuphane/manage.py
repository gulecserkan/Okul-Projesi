#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kutuphane.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    if len(sys.argv) > 1 and sys.argv[1] == "update_overdue_loans":
        import django

        django.setup()
        from kutuphane_app.jobs import update_overdue_loans

        result = update_overdue_loans()
        total_penalty = result.get("total_penalty")
        summary = (
            "Güncelleme tamamlandı: {updated} kayıt gecikmeye alındı, "
            "{reverted} kayıt normale döndü, {recalc} ceza güncellendi, "
            "toplam ceza: {penalty}".format(
                updated=result.get("updated_overdue", 0),
                reverted=result.get("reverted", 0),
                recalc=result.get("recalculated", 0),
                penalty=str(total_penalty),
            )
        )
        print(summary)
        return

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
