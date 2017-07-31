"""
This module runs through all posts in the DB, 
checks for Wikipedia content, and get ORES score
"""


import requests
import os



def check_sampled_threads():
    """
    Run through sampled threads and get corresponding Wiki data
    """
    base = 'https://en.wikipedia.org/w/api.php?action=query'
    query_params = {
        'prop': 'revisions',
        'rvprop': 'ids%7Ctimestamp',
        'rvdir': 'older',
        'rvlimit': '1',
    }
    query_pairs = ['{}={}'.format(key, val) for key, val in query_params.items()]
    endpoint = base + '&'.join(query_pairs)
    print(endpoint)


    filtered = SampledRedditThread.objects.filter(wiki_content_analyzed=False)
    print('About to run through {} threads'.format(len(filtered)))
    w = 'wikipedia.org/wiki/'
    for thread in filtered:
        if w in thread.url:
            wiki_timestamp = thread.timestamp.strftime('%Y%m%d%H%M%S')
            print(wiki_timestamp)
            i = thread.url.find(w) + len(w)
            title = thread.url[i:]
            full_endpoint = endpoint + '&titles={}&rvstart={}'.format(
                title, wiki_timestamp
            )
            resp = requests.get(full_endpoint)
            print(resp)
            input()
        

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import (
        Post, AnnotatedRedditPost, ErrorLog, ThreadLog, SampledRedditThread
    )
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:\\Users\\nickm\\Desktop\\research\\wikipedia_and_stack_overflow\\client_secrets.json"
    print('Django settings initialized, running "check_sampled_threads"')
    check_sampled_threads()
