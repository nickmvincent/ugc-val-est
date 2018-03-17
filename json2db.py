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
        'stackoverflow-questions2': StackOverflowQuestion,
        'stackoverflow-users': StackOverflowUser,
    }[prefix]

SAVE_TEMPLATE = '{}_tmp.json'
TEST = False

def main(platform):
    """main driver"""

    prefixes = {}
    confirmation_sent = False
    client = storage.Client()
    bucket = client.get_bucket('datadumpsforme')
    for blob in bucket.list_blobs():
        tic = time.time()
        path = blob.name
        print(path)
        prefix = path[:path.find('/')]
        if TEST and prefixes.get(prefix):
            continue
        model = prefix_to_model(prefix)
        save_location = SAVE_TEMPLATE.format(platform)
        blob.download_to_filename(save_location)
        with open(save_location, 'r', encoding='utf8') as jsonfile:
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
                        ['REDACTED'],
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
                    model.objects.create(**kwargs)
                    prefixes[prefix] = True
                except IntegrityError:
                    continue
                except Exception as err:
                    full_msg = '\n'.join([path, str(data), str(kwargs), str(err)])
                    print(full_msg)
                    send_mail(
                        'json2db Error!',
                        full_msg,
                        settings.EMAIL_HOST_USER,
                        ['REDACTED'],
                        fail_silently=False,
                    )
            if not confirmation_sent:
                send_mail(
                    'Confirmation email: json2db ran successfully for one round',
                    path,
                    settings.EMAIL_HOST_USER,
                    ['REDACTED'],
                    fail_silently=False,
                )
                confirmation_sent = True
            print('Blob processing took {}'.format(time.time() - tic))


def json_to_table(model):
    """
    Take a json file and get it directly into a table

    abstract this later
    """

    confirmation_sent = False
    json_path = '/home/nvl0834/so_data/answers/samples/40k_dated_WP.json'

    paths = [json_path]

    test_dicts = []
    tests = 5
    test_counter = 0
    for path in paths:
        tic = time.time()
        print(path)
        with open(path, 'r', encoding='utf8') as jsonfile:
            print('open took {}'.format(time.time() - tic))
            tic = time.time()
            for line in jsonfile:
                test_counter += 1
                try:
                    data = json.loads(line)
                    if test_counter < 10:
                        test_dict = {}
                        test_dict['json'] = data
                except JSONDecodeError:
                    send_mail(
                        'json2db JSONDecode Error',
                        path,
                        settings.EMAIL_HOST_USER,
                        ['REDACTED'],
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
                    obj = model.objects.create(**kwargs)
                    if test_counter < 10:
                        test_dict['model'] = obj.__dict__
                        test_dicts.append(test_dict)
                        test_counter += 1
                    prefixes[prefix] = True
                except IntegrityError:
                    continue
                except Exception as err:
                    full_msg = '\n'.join([path, str(data), str(kwargs), str(err)])
                    print(full_msg)
                    send_mail(
                        'json2db Error!',
                        full_msg,
                        settings.EMAIL_HOST_USER,
                        ['REDACTED'],
                        fail_silently=False,
                    )
            if not confirmation_sent:
                send_mail(
                    'Confirmation email: json2db ran successfully for one round',
                    path,
                    settings.EMAIL_HOST_USER,
                    ['REDACTED'],
                    fail_silently=False,
                )
                confirmation_sent = True
            print('processing took {}'.format(time.time() - tic))
            print(test_dicts)
            with open('json_load_test_dicts.json', 'w') as file:
                json.dump(test_dicts, file)


def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='This module imports data from json (stored in GCS) to DB (postgres)')
    parser.add_argument(
        '--platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--mode', help='the mode to use. default is json_to_table',
        default="json_to_table")
    args = parser.parse_args()
    if args.mode == 'json_to_table':
        json_to_table(SampledStackOverflowPost)
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
        ErrorLog, SampledStackOverflowPost
    )
    parse()
