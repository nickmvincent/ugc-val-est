"""native imports"""
import os
import time
import argparse

from google.cloud import bigquery
from bq_explore import get_reddit_tables
from queryset_helpers import utcstamp_to_utcdatetime

QUERY_TEMPLATE = """
    SELECT {columns}, random() as rand
    FROM {table} ORDER BY rand LIMIT {limit};
    """

def give_truncator(lim):
    """
    Gives a truncator function
    Use closure
    """

    def truncator(val):
        """this closure based function truncates a string (val)
        to a max limit of lim"""
        return val[:lim]
    return truncator


def default_to_zero(val):
    """Return zero if val is None"""
    return 0 if val is None else val


def query_django_tables(query):
    """This function executes raw SQL to query tables created by django"""
    
    print(query)
    with connections['secondary'].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) from portal_stackoverflowanswer")
        rows = cursor.fetchall()
        print(rows)    
        cursor.execute(query)
        rows = cursor.fetchall()
    return rows


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



def sample_from_data_source(
        data_source, col_objects, queries, model, rows_to_sample, rows_per_query):
    """
    Populate DB with random samples of SO answers from BigQuery
    """
    if data_source == 'bq':
        client = bigquery.Client()

    t_init = time.time()
    rows_per_iteration = rows_per_query * len(queries)
    iterations_needed = int(rows_to_sample / rows_per_iteration)
    print('To sample {} rows, will use {} iterations with {} rows per iteration'.format(
        rows_to_sample, iterations_needed, rows_per_iteration
    ))
    for iteration in range(0, iterations_needed):
        t_start_iteration = time.time()
        for query in queries:
            lines = []
            if data_source == 'bq':
                query_results = client.run_sync_query(query)
                query_results.use_legacy_sql = False
                query_results.run()
                row_iter = query_results.fetch_data()
            elif data_source == 'db':
                row_iter = query_django_tables(query)
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


def sample_so(data_source, rows_to_sample, rows_per_query):
    """
    Sample Stack Overflow Answers
    Args:
        rows_per_query - number rows that will be retrieved per BQ call
    Returns:
        None
    """
    if data_source == 'bq':
        answers_table = '`bigquery-public-data.stackoverflow.posts_answers`'
        questions_table = '`bigquery-public-data.stackoverflow.posts_questions`'
        users_table = '`bigquery-public-data.stackoverflow.users`'
    elif data_source == 'db':
        answers_table = 'portal_stackoverflowanswer'
        questions_table = 'portal_stackoverflowquestion'
        users_table = 'portal_stackoverflowuser'

    col_objects = [
        {
            'bq_name': answers_table + '.body',
            'dja_name': 'body',
            'processing': give_truncator(30000),
        },
        {
            'bq_name': answers_table + '.id',
            'dja_name': 'uid',
        },
        {
            'bq_name': answers_table + '.score',
            'dja_name': 'score',
        },
        {
            'bq_name': answers_table + '.creation_date',
            'dja_name': 'timestamp',
        },
        {
            'bq_name': answers_table + '.comment_count',
            'dja_name': 'num_comments',
        },
        {
            'bq_name': users_table + '.reputation',
            'dja_name': 'user_reputation',
            'processing': default_to_zero,
        },
        {
            'bq_name': users_table + '.creation_date as user_created_utc',
            'dja_name': 'user_created_utc',
        },
        {
            'bq_name': questions_table + '.view_count',
            'dja_name': 'num_pageviews',
        },
        {
            'bq_name': questions_table + '.answer_count',
            'dja_name': 'num_other_answers',
        },
        {
            'bq_name': questions_table + '.answer_count',
            'dja_name': 'question_score',
        },
        {
            'bq_name': questions_table + '.creation_date as question_asked_utc',
            'dja_name': 'question_asked_utc',
        },
        {
            'bq_name': questions_table + '.tags',
            'dja_name': 'tags_string',
        },
    ]
    table = ("""{answers}
            LEFT JOIN {users} AS ownertable ON {answers}.owner_user_id = {users}.id
            LEFT JOIN {questions} ON {answers}.parent_id = {questions}.id
            """
            ).format(
                **{
                    'answers': answers_table, 'users': users_table,
                    'questions': questions_table,
                },
            )
    tables = [table, ]
    queries = []
    for table in tables:
        query_kwargs = {
            'columns': ', '.join([x['bq_name'] for x in col_objects]),
            'table': table,
            'limit': rows_per_query,
        }
        query = QUERY_TEMPLATE.format(**query_kwargs)
        queries.append(query)
    sample_from_data_source(
        data_source, col_objects, queries, SampledStackOverflowPost, rows_to_sample, rows_per_query)



def sample_reddit(data_source, rows_to_sample, rows_per_query):
    """Sample Reddit Threads"""
    col_objects = [
        {
            'bq_name': 'selftext',
            'dja_name': 'body',
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
        }
    ]
    if data_source == 'bq':
        tables = get_reddit_tables()
    elif data_source == 'db':
        tables = ['portal_redditpost']
    queries = []
    for table in tables:
        query_kwargs = {
            'columns': ', '.join([x['bq_name'] for x in col_objects]),
            'table': table,
            'limit': rows_per_query,
        }
        query = QUERY_TEMPLATE.format(**query_kwargs)
        queries.append(query)
    sample_from_data_source(
        data_source, col_objects, queries, SampledRedditThread, rows_to_sample, rows_per_query)

def sample_using_django_api():
    pass



def parse():
    """
    Parse args and do the appropriate analysis
    """
    parser = argparse.ArgumentParser(
        description='Populates db')
    parser.add_argument(
        '--data_source', help='the data source to use. "bq" for bigquery and "db" for db')
    parser.add_argument(
        '--rows_to_sample', type=int, help="the total number of rows to sample")
    parser.add_argument(
        '--rows_per_query', type=int, help="the number of rows to sample in each query")
    args = parser.parse_args()
    oargs = args.data_source, args.rows_to_sample, args.rows_per_query
    sample_so(*oargs)
    sample_reddit(*oargs)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dja.settings")
    import django
    from django.db.utils import IntegrityError
    django.setup()
    from django.db import connections
    from portal.models import (
        ErrorLog, SampledRedditThread,
        SampledStackOverflowPost,
    )
    parse()
