"""
This module imports data from json (stored in GCS) to DB (postgres)
"""
import os
import glob
import json
from json.decoder import JSONDecodeError
import argparse
from datetime import datetime
import time

import pytz
from google.cloud import storage


def key_to_table(key):
    """
    For a given files key, returns the model/table it should be stored as
    """
    if 'reddit_2016' in key:
        return RedditPost
    return {
        'stackoverflow-answers': StackOverflowAnswer,
        'stackoverflow-questions': StackOverflowQuestion,
        'stackoverflow-users': StackOverflowUser,
    }[key]

SAVE_TEMPLATE = '{}_tmp.json'
TEST = False

def main(platform, table_key, bucket, must_include):
    """main driver"""
    confirmation_sent = False
    client = storage.Client()
    bucket = client.get_bucket(bucket)
    for blob in bucket.list_blobs():
        tic = time.time()
        path = blob.name
        print(path)
        if must_include not in path:
            print('skipping, does not have {}'.format(must_include))
            continue
        model = key_to_table(table_key)
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
                    model.objects.create(**kwargs)
                except IntegrityError as err:
                    # it already exists!
                    print(err)
                    continue
                except Exception as err:
                    full_msg = '\n'.join([path, str(data), str(kwargs), str(err)])
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


def from_local_filesystem(platform, path, table_prefix=None):
    """main driver"""

    confirmation_sent = False
    all_files = glob.glob(os.path.join(path, "*.json"))
    for file in all_files:
        tic = time.time()
        if table_prefix:
            prefix = table_prefix
        else:
            prefix = path[:path.find('/')]
        model = prefix_to_model(prefix)
        with open(file, 'r', encoding='utf8') as jsonfile:
            print('open took {}'.format(time.time() - tic))
            tic = time.time()
            for line in jsonfile:
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
                    model.objects.create(**kwargs)
                except IntegrityError:
                    continue
                except Exception as err:
                    full_msg = '\n'.join([path, str(data), str(kwargs), str(err)])
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
            print('processing took {}'.format(time.time() - tic))


def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='This module imports data from json (stored in GCS) to DB (postgres)')
    parser.add_argument(
        '--platform', help='the platform to use. "r" for reddit and "s" for stack overflow')
    parser.add_argument(
        '--key', default='reddit_2016')
    parser.add_argument(
        '--mode', help='the mode to use',
        default="from_local_filesystem")
    parser.add_argument(
        '--path', help='where your json files live',
        default="/home/nvl0834/reddit_data/submissions")
    parser.add_argument(
        '--bucket', help='where your json files live in BQ',
        default="nmvg_stackoverflow")
    parser.add_argument(
        '--must_include', help='path must include this...',
        default="/answers")

    # python json2db.py --platform s --key stackoverflow-answers --mode bq --bucket nmvg_stackoverflow/answers --must_include /answers

        
    args = parser.parse_args()
    if args.mode == 'from_local_filesystem':
        from_local_filesystem(args.platform, args.path, args.key)
    elif args.mode == 'test_mail':
        send_mail(
            'test subject',
            'test body',
            settings.EMAIL_HOST_USER,
            ['nickmvincent@gmail.com'],
            fail_silently=False,
        )
    else:
        main(args.platform, args.key, args.bucket, args.must_include)


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
    print('Warning: this script may fail if you have not configured email properly! Head to settings.py to set your email up. Or comment it out (not advised)')
