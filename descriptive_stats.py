import os
import operator
from collections import Counter, defaultdict
import numpy as np
import matplotlib.pyplot as plt



def plot_bar_from_counter(counter, label=True, ax=None):
    """"
    This function creates a bar plot from a counter.

    :param counter: This is a counter object, a dictionary with the item as the key
     and the frequency as the value
    :param ax: an axis of matplotlib
    :return: the axis wit the object in it
    """

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111)

    frequencies = counter.values()
    names = counter.keys()
    x_coordinates = np.arange(len(counter))
    ax.bar(x_coordinates, frequencies, align='center')

    if label:
        ax.xaxis.set_major_locator(plt.FixedLocator(x_coordinates))
        ax.xaxis.set_major_formatter(plt.FixedFormatter(list(names)))

    return ax

TOP_TEN = [
    'announcements',
    'funny',
    'AskReddit',
    'todayilearned',
    'science',
    'worldnews',
    'pics',
    'IAmA',
    'gaming',
    'videos',
]

def main():
    """Driver"""
    subreddits = list(SampledRedditThread.objects.filter(url__contains='wikipedia.org/wiki/').values_list('context', flat=True))
    subreddit_counts = Counter(subreddits)
    wikicount_in_TIL = subreddit_counts.get('todayilearned')
    plot_bar_from_counter(subreddit_counts, label=False)
    key_list = list(subreddit_counts.keys())
    index_to_key = {i: key for i, key in enumerate(key_list)}


    def get_base(url):
        """Return the base of a given url"""
        aliases = {
            'youtu.be': 'youtube.com',
            'i.reddituploads.com': 'reddit.com',
            'i.redd.it': 'reddit.com',
            'np.reddit.com': 'reddit.com',
            'i.sli.mg': 'imgur.com',
            'i.imgur.com': 'imgur.com',
        }
        double_slash = url.find('//')
        single_slash = url.find('/', double_slash+2)
        base = url[double_slash+2:single_slash]
        base = base.replace('www.', '')
        base = base.replace('.m.', '.')
        if base[0:2] == 'm.':
            base = base.replace('m.', '')
        if 'wikipedia.org' in base:
            return 'wikipedia.org'
        for alias_domain, actual_domain in aliases.items():
            if base == alias_domain:
                return actual_domain
        return base

    def identify_link_distribution(qs):
        """Takes a qs a figure out which base urls the linsk go to"""
        num_threads = qs.count()
        print('Identifying link distribution for {} threads'.format(num_threads))
        domain_to_count = defaultdict(int)
        batch_index = 0
        batch_size = 10000
        while batch_index < num_threads:
            batch = qs[batch_index:batch_index+batch_size]
            for thread in batch:
                base = get_base(thread.url)
                domain_to_count[base] += 1
            sorted_domain_to_count = sorted(
                domain_to_count.items(), key=operator.itemgetter(1), reverse=True)
            batch_index += batch_size
        for i, domain_tup in enumerate(sorted_domain_to_count[:30]):
            domain = domain_tup[0]
            count = domain_to_count[domain]
            percent = count / num_threads * 100
            print(i, domain_tup, percent) 

    til_threads = SampledRedditThread.objects.filter(context='todayilearned')
    top_ten_threads = SampledRedditThread.objects.filter(context__in=TOP_TEN)
    print('=== TIL ===')
    identify_link_distribution(til_threads)
    print(' === All ===')
    identify_link_distribution(SampledRedditThread.objects.all())
    print('=== TOP TEN ===')
    identify_link_distribution(top_ten_threads)

    num_til_threads = len(til_threads) 
    wikipercent_in_TIL = wikicount_in_TIL / num_til_threads * 100
    print(wikicount_in_TIL, num_til_threads, wikipercent_in_TIL)

    # print(index_to_key)
    # plt.show()    



if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    django.setup()
    from portal.models import SampledRedditThread
    main()

