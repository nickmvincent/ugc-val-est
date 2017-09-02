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
            # 'lexicon_count',
            'sentence_count',
            'length', 'percent_uppercase',
            'percent_spaces', 'percent_punctuation',
            'starts_capitalized',
            'coleman_liau_index',
            'includes_question_mark',
            'sentiment_polarity', 'sentiment_subjectivity',
    ]:
        ret.append('{}_{}'.format(prefix, metric))
    return ret

def list_common_features():
    """
    Returns common features.
    Does NOT return outcome variables
    Helpful for prediction functions
    that make heavy use of getattr
    """
    return [
        'mon', 'tues', 'wed', 'thurs',
        'fri', 'sat',
        'jan', 'feb', 'mar', 'apr',
        'may', 'jun', 'jul', 'aug', 'sep',
        'octo', 'nov',
        'zero_to_six', 'six_to_twelve', 'twelve_to_eighteen',
        'seconds_since_user_creation',
    ]

def list_reddit_specific_features():
    """Features unique to reddit posts"""
    textual = list_textual_metrics('title')
    return textual + [
        'user_comment_karma', 'user_link_karma', 
        'user_is_mod', 'user_is_suspended', 'user_is_deleted',
        #'in_todayilearned', 
        #'in_borntoday', 'in_wikipedia', 'in_CelebrityBornToday','in_The_Donald',
    ]

def list_stack_specific_features():
    """Features unique to SO answers"""
    body_features = list_textual_metrics('body')
    return body_features + [
        'user_reputation', 
#        'body_includes_code',
        'num_tags',
        'response_time',
        'year2008', 'year2009', 'year2010',
        'year2011', 'year2012', 'year2013',
        'year2014', 'year2015',
    ]
