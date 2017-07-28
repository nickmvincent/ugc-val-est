"""native imports"""
import os


def main():
    """driver"""


    print('AnnotatedRedditPosts: {}'.format(AnnotatedRedditPost.objects.all().count()))
    print('Errors: {}'.format(ErrorLog.objects.all().count()))


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import Post, AnnotatedRedditPost, ErrorLog

    main()
