"""
This module imports data from json (stored in GCS) to DB (postgres)
"""
import os
import json
import argparse

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
TEST = True

def main(platform):
    prefixes = {}

    client = storage.Client()
    bucket = client.get_bucket('datadumpsforme')
    for blob in bucket.list_blobs():
        path = blob.name
        prefix = path[:path.find('/')]
        print(path)
        if TEST and prefixes.get(prefix):
            continue
        if prefix != 'stackoverflow-answers':
            continue
        model = prefix_to_model(prefix)
        blob.download_to_filename(SAVE_LOC)
        with open(SAVE_LOC, 'r', encoding='utf8') as jsonfile:
            for line in jsonfile:
                data = json.loads(line)
                print(data)
                kwargs = {}
                for field in model._meta.get_fields():
                    kwargs[field.name] = data.get(field.name)
                    if kwargs[field.name] == 'null':
                        kwargs[field.name] = None
                    if (field._description() == 'Field of type: DateTimeField' and 
                        kwargs[field.name] and
                        ' UTC' in kwargs[field.name]):
                        kwargs[field.name] = kwargs[field.name].replace(' UTC', '')
                print(kwargs)
                try:
                    obj, created= model.objects.get_or_create(**kwargs)
                    prefixes[prefix] = True
                except Exception as err:
                    print(err)
                if TEST:
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
