"""native imports"""
import json
import os
import time
import datetime

import pytz
import praw
from prawcore.exceptions import Forbidden, NotFound
from google.cloud import bigquery
from explore import get_reddit_tables


# 21684.653096437454

ROWS_PER_QUERY = 10000
ROWS_TO_SAMPLE = 12 * 100000
QUERY_TEMPLATE = """
    SELECT {columns}, rand() as rand
    FROM {table} ORDER BY rand LIMIT {limit};
    """

SO_ANSWERS_TABLE = '`bigquery-public-data.stackoverflow.posts_answers`'
SO_QUESTIONS_TABLE = '`bigquery-public-data.stackoverflow.posts_questions`'
SO_USERS_TABLE = '`bigquery-public-data.stackoverflow.users`'

def utcstamp_to_utcdatetime(timestamp):
    """Takes a UTC stamp and returns UTC datetime"""
    return datetime.datetime.fromtimestamp(timestamp).replace(tzinfo=pytz.UTC)


def give_truncator(lim):
    """
    Gives a truncator function
    Use closure
    """

    def truncator(val):
        return val[:lim]
    return truncator


def default_to_zero(val):
    """Return zero if val is None"""
    return 0 if val is None else val

def give_author_processor(reddit):
    """
    This function uses closures to
    take a "reddit" object and returns a function that will process author information using the reddit object
    """
    def author_processor(val):
        """Process author info"""
        ret = {}
        author = reddit.redditor(val)
        try:
            if getattr(author, 'is_suspended', None):
                ret['user_is_suspended'] = True
            else:
                ret['user_comment_karma'] = author.comment_karma
                ret['user_link_karma'] = author.comment_karma
                ret['user_created_utc'] = utcstamp_to_utcdatetime(author.created_utc)
                ret['user_is_mod'] = author.is_mod
        except:
            ret['user_is_deleted'] = True
        return ret
    return author_processor

def init_count():
    """Initialize a counter dict to keep track of successes/errors"""
    count = {}
    count['posts_attempted'] = 0
    count['already_in_db'] = 0
    count['already_in_errors'] = 0
    count['rows_added'] = 0
    count['errors_added'] = 0
    return count


def process_prepared_lines(lines, model):
    """
    Args:
        lines - a list of of dicts, each corresponds to a row of data
    Returns:
        None
    """
    count = init_count()
    if not lines:
        print('process_prepared_lines was called but no lines were provided...')
    for line in lines:
        count['posts_attempted'] += 1
        try:
            _, created = model.objects.get_or_create(**line)
            if created:
                count['rows_added'] += 1
            else:
                count['already_in_db'] += 1
        except KeyError as err:
            msg = 'Err loading post: {}'.format(err)
            log, created = ErrorLog.objects.get_or_create(uid=line.get('uid'))
            log.msg = msg[:254]
            log.save()
            if created:
                count['errors_added'] += 1
            else:
                count['already_in_errors'] += 1
        except IntegrityError:
            count['already_in_db'] += 1
    print(count)




def sample_from_bq(col_objects, queries, model, rows_per_query):
    """
    Populate DB with random samples of SO answers from BigQuery
    """
    client = bigquery.Client()
    t_init = time.time()
    rows_to_sample = ROWS_TO_SAMPLE
    rows_per_iteration = rows_per_query * len(queries)
    iterations_needed = int(rows_to_sample / rows_per_iteration)
    print('To sample {} rows, will use {} iterations with {} rows per iteration'.format(
        rows_to_sample, iterations_needed, rows_per_iteration
    ))
    for iteration in range(0, iterations_needed):
        t_start_iteration = time.time()
        for query in queries:
            t_start_query = time.time()
            query_results = client.run_sync_query(query)
            query_results.use_legacy_sql = False
            query_results.run()
            lines = []
            row_iter = query_results.fetch_data()
            for row in row_iter:
                row_dict = {}
                for i, obj in enumerate(col_objects):
                    val = row[i]
                    if obj.get('processing'):
                        val = obj['processing'](val)
                    if obj['dja_name'] is None:
                        for field, fieldval in val.items():
                            row_dict[field] = fieldval
                    else:
                        row_dict[obj['dja_name']] = val
                if row_dict.get('user_created_utc') is None:
                    row_dict['user_created_utc'] = row_dict['timestamp']
                lines.append(row_dict)
            process_prepared_lines(lines, model)
            # print('Runtime for query {} was {}'.format(query, time.time() - t_start_query))
        print('Runtime for iteration {} was {}'.format(
            iteration, time.time() - t_start_iteration))
    print('Total runtime was {}'.format(time.time() - t_init))


def sample_so(rows_per_query):
    """
    Sample Stack Overflow Answers
    Args:
        rows_per_query - number rows that will be retrieved per BQ call
    Returns:
        None
    """
    col_objects = [
        {
            'bq_name': SO_ANSWERS_TABLE + '.body',
            'dja_name': 'body',
            'processing': give_truncator(30000),
        },
        {
            'bq_name': SO_ANSWERS_TABLE + '.id',
            'dja_name': 'uid',
        },
        {
            'bq_name': SO_ANSWERS_TABLE + '.score',
            'dja_name': 'score',
        },
        {
            'bq_name': SO_ANSWERS_TABLE + '.creation_date',
            'dja_name': 'timestamp',
        },
        {
            'bq_name': SO_ANSWERS_TABLE + '.comment_count',
            'dja_name': 'num_comments',
        },
        {
            'bq_name': SO_USERS_TABLE + '.reputation',
            'dja_name': 'user_reputation',
            'processing': default_to_zero,
        },
        {
            'bq_name': SO_USERS_TABLE + '.creation_date as user_created_utc',
            'dja_name': 'user_created_utc',
        },
        {
            'bq_name': SO_QUESTIONS_TABLE + '.view_count',
            'dja_name': 'num_pageviews',
        },
        {
            'bq_name': SO_QUESTIONS_TABLE + '.tags',
            'dja_name': 'tags_string',
        },
    ]
    table = ("""{answers}
            LEFT JOIN {users} ON {answers}.owner_user_id = {users}.id
            LEFT JOIN {questions} ON {answers}.parent_id = {questions}.id
            """
    ).format(
        **{
            'answers': SO_ANSWERS_TABLE, 'users': SO_USERS_TABLE,
            'questions': SO_QUESTIONS_TABLE,
        },
    )
    tables = [table, ]
    queries = []
    for table in tables:
        query_kwargs = {
            'columns': ', '.join([x['bq_name'] for x in col_objects]),
            'table': table,
            'limit': ROWS_PER_QUERY,
        }
        query = QUERY_TEMPLATE.format(**query_kwargs)
        queries.append(query)
    sample_from_bq(col_objects, queries, SampledStackOverflowPost, rows_per_query)
    


def sample_reddit(rows_per_query):
    """Sample Reddit Threads"""
    # reddit = praw.Reddit(
    #     client_id=os.environ["CLIENT_ID"], 
    #     client_secret=os.environ["CLIENT_SECRET"], user_agent=os.environ["UA"])

    col_objects = [
        {
            'bq_name': 'selftext',
            'dja_name': 'body',
            'processing': give_truncator(10000)
        },
        {
            'bq_name': 'id',
            'dja_name': 'uid',
        },
        {
            'bq_name': 'score',
            'dja_name': 'score',
        },
        {
            'bq_name': 'author',
            'dja_name': 'author',
        },
        {
            'bq_name': 'created_utc',
            'dja_name': 'timestamp',
            'processing': utcstamp_to_utcdatetime,
        },
        {
            'bq_name': 'url',
            'dja_name': 'url', # db handles maximum possible length
            'processing': give_truncator(2083)
        },
        {
            'bq_name': 'subreddit',
            'dja_name': 'context',
        },
        {
            'bq_name': 'num_comments',
            'dja_name': 'num_comments',
        },
        {
            'bq_name': 'title',
            'dja_name': 'title',
            'processing': give_truncator(500)
        }
    ]
    tables = get_reddit_tables()
    queries = []
    for table in tables:
        query_kwargs = {
            'columns': ', '.join([x['bq_name'] for x in col_objects]),
            'table': table,
            'limit': ROWS_PER_QUERY,
        }
        query = QUERY_TEMPLATE.format(**query_kwargs)
        queries.append(query)
    sample_from_bq(col_objects, queries, SampledRedditThread, rows_per_query)


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db.utils import IntegrityError
    django.setup()
    from portal.models import (
        ErrorLog, ThreadLog, SampledRedditThread,
        SampledStackOverflowPost,
    )
    print('Ready to begin "populate_db" script')
    # sample_reddit(ROWS_PER_QUERY)
    sample_so(ROWS_PER_QUERY)