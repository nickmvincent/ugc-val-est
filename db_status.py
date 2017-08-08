"""native imports"""
import os
from pprint import pprint


def explore_queryset():
    """
    Explores a queryset. Meant for extended shell scripting
    """
    qs = SampledRedditThread.objects.filter(url__contains="wikipedia.org/wiki")
    for thread in qs:
        if 'imgur' in thread.url:
            print(thread.url)


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


def main():
    """driver"""


    report_body = ""
    count_template = "Table {} has {} rows"
    report_body += count_template.format(
        'SampledRedditThread',
        SampledRedditThread.objects.all().count(),
    ) + '\n'
    report_body += count_template.format(
        'SampledRedditThread with wiki links',
        SampledRedditThread.objects.filter(url__contains='wikipedia.org/wiki/').count(),
    ) + '\n'
    report_body += count_template.format(
        'SampledStackOverflowPost',
        SampledStackOverflowPost.objects.all().count(),
    )
    print(report_body)
    show_errors()
    explore_queryset()
    # send_mail(
    #     'DB Status Report',
    #     report_body,
    #     settings.EMAIL_HOST_USER,
    #     ['nickmvincent@gmail.com'],
    #     fail_silently=False,
    # )

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import Post, ErrorLog, SampledRedditThread, SampledStackOverflowPost
    from dja import settings
    from django.core.mail import send_mail
    main()
