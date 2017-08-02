"""Calculate and save features"""

import os


def main():
    for i, thread in enumerate(SampledRedditThread.objects.all()):
        if i % 1000 == 0 and i != 0:
            print(i)
        thread.save()
        



if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import SampledRedditThread

    print('Performing feature calculations...')
    main()