import datetime
import pytz

def batch_qs(qs, total=None, batch_size=1000):
    """
    Returns a (start, end, total, queryset) tuple for each batch in the given
    queryset.

    The purpose of the `total` parameter is to save memory/query time
    if the length of the queryset has already been determined in
    the parent code.

    Usage:
        # Make sure to order your querset
        article_qs = Article.objects.order_by('id')
        total = article_qs.count()
        for start, end, total, qs in batch_qs(article_qs, total, 1500):
            print "Now processing %s - %s of %s" % (start + 1, end, total)
            for article in qs:
                print article.body
    """
    if not qs.query.order_by:
        raise ValueError("batch_qs was used without an order_by choice")
    if total is None:
        total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])

def utcstamp_to_utcdatetime(timestamp):
    """Takes a UTC stamp and returns UTC datetime"""
    return datetime.datetime.fromtimestamp(timestamp).replace(tzinfo=pytz.UTC)


def list_textual_metrics(prefix):
    """Takes a prefix string (body or title)
    and returns a list of all the metrics associated with
    the text. The purpose of this is to help with
    analysis that wants a list of all
    textual metric feature names"""
    ret = []
    for metric in [
            'length', 'percent_uppercase',
            'percent_spaces', 'percent_punctuation',
            'starts_capitalized',
            'coleman_liau_index',
    ]:
        ret.append('{}_{}'.format(prefix, metric))
    return ret

def list_common_features():
    """
    Returns common features.
    Does NOT return outcome variables
    Helpful for stats/prediction functions
    that make heavy use of getattr
    """
    return [
        'day_of_week', 'day_of_month',
        'hour', 'seconds_since_user_creation',
    ]

def list_reddit_specific_features():
    """Features unique to reddit posts"""
    textual = list_textual_metrics('title')
    return textual + [
        'user_comment_karma', 'user_link_karma', 
        'user_is_mod', 'user_is_suspended', 'user_is_deleted'
    ]

def list_stack_specific_features():
    """Features unique to SO answers"""
    body_features = list_textual_metrics('body')
    return body_features + [
        'user_reputation', 
        'body_num_links',
        'num_tags',
        # commented out until this is implemente fully
        'response_time',
    ]
