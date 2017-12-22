import os
import numpy as np
from scipy import stats

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
    qsr = SampledRedditThread.objects.filter(**kwargs)
    qss = SampledStackOverflowPost.objects.filter(**kwargs)

    for var in [
        'num_edits', 'num_edits_prev_week'
    ]:
        vals_r = qsr.values_list(var, flat=True)
        vals_s = qss.values_list(var, flat=True)
        print('Variable is', var)
        print(len(vals_r), len(vals_s))
        print('Mean for Reddit is', np.mean(vals_r))
        print('Mean for SO is', np.mean(vals_s))



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
