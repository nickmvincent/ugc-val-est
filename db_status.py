"""native imports"""
import os



def main():
    """driver"""


    report_body = ""
    count_template = "Table {} has {} rows"
    report_body += count_template.format(
        'SampledRedditThread',
        SampledRedditThread.objects.all().count(),
    )
    print(report_body)
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
    from portal.models import Post, ErrorLog, SampledRedditThread
    from dja import settings
    from django.core.mail import send_mail
    main()
