"""
This module imports data from json (stored in GCS) to DB (postgres)
"""
import os
import json
from json.decoder import JSONDecodeError
import argparse
from datetime import datetime
import time

import pytz
from google.cloud import storage


def prefix_to_model(prefix):
    """
    For a given files prefix, returns the model/table it should be stored as
    """
    if 'reddit_2016' in prefix:
        return RedditPost
    return {
        'stackoverflow-answers': StackOverflowAnswer,
        'stackoverflow-questions': StackOverflowQuestion,
        'stackoverflow-users': StackOverflowUser,
    }[prefix]

# completed stackoverflow-answers 0 to 63
# error occurred in 64

SAVE_LOC = 'tmp.json'
TEST = False

def main(platform):
    """main driver"""
    soa_template = 'stackoverflow-answers/0000000000{}'
    completed = []
    for i in range(0, 10):
        completed.append(soa_template.format('0' + str(i)))
    for i in range (10, 64):
        completed.append(soa_template.format(str(i)))
    

    prefixes = {}
    confirmation_sent = False

    client = storage.Client()
    bucket = client.get_bucket('datadumpsforme')
    for blob in bucket.list_blobs():
        tic = time.time()
        path = blob.name
        print(path)
        if path in completed:
            print('Bypassing completed path')
            continue
        prefix = path[:path.find('/')]
        if platform == 's':
            if 'reddit' in prefix:
                print('Bypassing {} for now'.format(path))
                continue
        elif platform == 'r':
            if 'stackoverflow' in prefix:
                print('Bypassing {} for now'.format(path))                
                continue
        if TEST and prefixes.get(prefix):
            continue
        model = prefix_to_model(prefix)
        blob.download_to_filename(SAVE_LOC)
        with open(SAVE_LOC, 'r', encoding='utf8') as jsonfile:
            print('Download + open took {}'.format(time.time() - tic))
            tic = time.time()
            test_counter = 0
            for line in jsonfile:
                test_counter += 1
                try:
                    data = json.loads(line)
                except JSONDecodeError:
                    send_mail(
                        'json2db JSONDecode Error',
                        path,
                        settings.EMAIL_HOST_USER,
                        ['nickmvincent@gmail.com'],
                        fail_silently=False,
                    )
                    continue
                kwargs = {}
                for field in model._meta.get_fields():
                    try:
                        kwargs[field.name] = data[field.name]
                    except KeyError:
                        continue
                    val = kwargs[field.name]
                    if val == 'null':
                        kwargs.pop(field.name, 0)
                    if (field._description() == 'Field of type: DateTimeField' and 
                        val):
                        if '.' in val:
                            period_index = val.find('.')
                            kwargs[field.name] = val[:period_index] + ' UTC'
                        try:
                            as_dt = datetime.strptime(kwargs[field.name], "%Y-%m-%d %H:%M:%S %Z")
                            kwargs[field.name] = as_dt.astimezone(pytz.UTC)
                        except ValueError:
                            print(data)
                            continue
                try:
                    obj, created = model.objects.create(**kwargs)
                    prefixes[prefix] = True
                except IntegrityError:
                    continue
                except Exception as err:
                    full_msg = '\n'.join([path, data, kwargs, err])
                    print(full_msg)
                    send_mail(
                        'json2db Error!',
                        full_msg,
                        settings.EMAIL_HOST_USER,
                        ['nickmvincent@gmail.com'],
                        fail_silently=False,
                    )
            if not confirmation_sent:
                send_mail(
                    'Confirmation email: json2db ran successfully for one round',
                    path,
                    settings.EMAIL_HOST_USER,
                    ['nickmvincent@gmail.com'],
                    fail_silently=False,
                )
                confirmation_sent = True
            print('Blob processing took {}'.format(time.time() - tic))
def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='This module imports data from json (stored in GCS) to DB (postgres)')
    parser.add_argument(
        'platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
    args = parser.parse_args()
    main(args.platform)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from django.db import IntegrityError
    from django.core.mail import send_mail
    from dja import settings
    from portal.models import (
        RedditPost, StackOverflowAnswer, 
        StackOverflowQuestion, StackOverflowUser,
        ErrorLog
    )
    parse()
