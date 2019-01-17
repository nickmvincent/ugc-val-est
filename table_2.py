import os
import numpy as np
from scipy import stats
from collections import defaultdict
def main():
    """
    Main method
    """
    kwargs = {
        'has_wiki_link': True,
        'day_of_avg_score__isnull': False,
        'week_after_avg_score__isnull': False,
        'sample_num__in': [0,1,2],
    }
    qsr = SampledRedditThread.objects.filter(**kwargs).order_by('timestamp')
    #qss = SampledStackOverflowPost.objects.filter(**kwargs)
    #errs = qsr.exclude(wiki_content_error=0)
    #print(len(errs))
    #for err in errs:
    #    print(err.url)
    #    input()
    print(qsr.count())

    #x = qss.values_list('num_other_answers', flat=True)
    #print(np.median(x))
    for var1, var2 in [
        ('num_edits', 'num_edits_prev_week'),
        ('num_wiki_pageviews', 'num_wiki_pageviews_prev_week',) 
    ]:
        tups_r = qsr.values_list(var1, var2, 'timestamp', 'wiki_links',) #flat=True)
        seen = {}
        links_to_stamps = defaultdict(list)
        vals1, vals2 = [], []
        skipped = 0
        for val1, val2, ts, links in tups_r:
            #print(links)
            if links not in links_to_stamps:
            #if links not in seen:
                links_to_stamps[links].append(ts)
                vals1.append(val1)
                vals2.append(val2)
            else:
                for stamp in links_to_stamps[links]:
                    dt = ts - stamp
                    secs = dt.total_seconds()
                    if secs < 24 * 3600 * 3:
                        skipped +=1
                        break
                else:    
                    links_to_stamps[links].append(ts)
                    vals1.append(val1)
                    vals2.append(val2)
                    
        #vals_s = qss.values_list(var, flat=True)
        print('Variable is', var1, var2)
        print(len(tups_r), len(vals1), np.mean(vals1), np.mean(vals2), skipped)
        _, pval = stats.ttest_rel(vals1, vals2)
        print(np.mean(vals1) - np.mean(vals2), pval)
        #print(len(vals_r), len(vals_s))
        #print('Mean for Reddit is', np.mean(vals_r))
        #print('Mean for SO is', np.mean(vals_s))



if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db import connection
    django.setup()
    from portal.models import (
        SampledRedditThread, SampledStackOverflowPost,
        StackOverflowAnswer
    )
    main()
