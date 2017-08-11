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
    if total is None:
        total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])

def utcstamp_to_utcdatetime(timestamp):
    """Takes a UTC stamp and returns UTC datetime"""
    return datetime.datetime.fromtimestamp(timestamp).replace(tzinfo=pytz.UTC)