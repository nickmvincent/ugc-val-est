"""
This module imports data from json (stored in GCS) to DB (postgres)
"""
import os
import json
import argparse
from datetime import datetime

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
    


SAVE_LOC = 'tmp.json'
TEST = False

def main(platform):
    prefixes = {}

    client = storage.Client()
    bucket = client.get_bucket('datadumpsforme')
    for blob in bucket.list_blobs():
        path = blob.name
        print(path)
        prefix = path[:path.find('/')]
        if TEST and prefixes.get(prefix):
            continue
        model = prefix_to_model(prefix)
        blob.download_to_filename(SAVE_LOC)
        with open(SAVE_LOC, 'r', encoding='utf8') as jsonfile:
            test_counter = 0
            for line in jsonfile:
                test_counter += 1
                data = json.loads(line)
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
                        as_dt = datetime.strptime(kwargs[field.name], "%Y-%m-%d %H:%M:%S %Z")
                        kwargs[field.name] = as_dt.astimezone(pytz.UTC)
                try:
                    obj, created= model.objects.get_or_create(**kwargs)
                    prefixes[prefix] = True
                except Exception as err:
                    print(path)
                    print(data)
                    print(kwargs)
                    print(err)
                if TEST and test_counter > 100:
                    break


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
    from portal.models import (
        RedditPost, StackOverflowAnswer, StackOverflowQuestion, StackOverflowUser
    )
    parse()
