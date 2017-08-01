"""
Helper functions to interface with DB so we don't have to use pgadmin...
"""
import os
import sys
from pprint import pprint


def show_errors():
    """Show error messages"""
    logs = ErrorLog.objects.all()
    print('There are {} total errors logged'.format(len(logs)))
    message_cache = {}
    for error_log in logs:
        msg = error_log.msg
        if msg not in message_cache:
            print(msg)
            message_cache[msg] = 0
        else:
            message_cache[msg] += 1
    pprint(message_cache)


def delete_old_errors():
    """one off script"""
    ErrorLog.objects.filter(msg__contains="not-null").delete()
    ErrorLog.objects.filter(msg="").delete()

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        AnnotatedRedditPost, ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
    )
    if len(sys.argv) > 1 and sys.argv[1] == 'delete':
        delete_old_errors()
    else:
        show_errors()