"""native imports"""
import os



def explore_queryset():
    """
    Explores a queryset. Meant for extended shell scripting
    """
    qs = SampledRedditThread.objects.filter(url__contains="wikipedia.org/wiki")
    for thread in qs:
        if 'imgur' in thread.url:
            print(thread.url)



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
