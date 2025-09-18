#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Execute administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ordemservico_project.settings")
    try:
        from django.core.management import execute_from_command_line
    except Exception as exc:
        # preserve the original behaviour to show helpful errors
        raise
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
