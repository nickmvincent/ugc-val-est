#!/usr/bin/env python

# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Simple application that performs a query with BigQuery."""
from pprint import pprint

# from fingerprint import Fingerprint
from google.cloud import bigquery


def query_so_answers():
    """Run a LEFT JOIN query on SO answers on BQ"""
    client = bigquery.Client()
    query_results = client.run_sync_query("""
        SELECT
            `bigquery-public-data.stackoverflow.posts_answers`.body, `bigquery-public-data.stackoverflow.posts_answers`.owner_user_id,
            `bigquery-public-data.stackoverflow.users`.reputation, `bigquery-public-data.stackoverflow.users`.creation_date
            FROM `bigquery-public-data.stackoverflow.posts_answers`
            LEFT JOIN `bigquery-public-data.stackoverflow.users`
            ON
            `bigquery-public-data.stackoverflow.posts_answers`.owner_user_id = `bigquery-public-data.stackoverflow.users`.id
            LIMIT 100;
        """)

    query_results.use_legacy_sql = False
    query_results.run()

    # Drain the query results by requesting a page at a time.
    page_token = None

    resp = query_results.fetch_data(
        max_results=100,
        page_token=page_token)
    print(resp)
    for iterable in resp:
        print(iterable)
        # print('Show another?')
        # _ = input()
        # text = html2text.html2text(iterable[0])
        # print(iterable[0])
        # print(text)
        # base = 'https://en.wikipedia.org/w/api.php?'
        # config = 'action=query&list=search&format=json&'
        # search_params = 'srsearch={}&srwhat=text'.format(text)
        # wiki_resp = requests.get('{}{}{}'.format(
        #     base, config, search_params
        # ))
        # print(wiki_resp.json())
        # _ = input()


def make_select(
        fields_to_select, table_name, where_clause=None,
        group_by_cols=None, order_by_cols=None):
    """Returns a syntactically correct SELECT statement"""
    components = []
    components.append("SELECT {}".format(fields_to_select))
    components.append("FROM {}".format(table_name))
    if where_clause:
        components.append(where_clause)
    if group_by_cols:
        components.append('GROUP BY {}'.format(group_by_cols))
    if order_by_cols:
        components.append('ORDER BY {}'.format(order_by_cols))
    return ' '.join(components) + ';'


def get_reddit_tables():
    """Returns 12 reddit tables corresponding to 2016"""
    reddit_2016_tables = []
    temp = '`fh-bigquery.reddit_posts.2016_{}`'
    for i in range(1, 10):
        reddit_2016_tables.append(temp.format('0' + str(i)))
    for i in range(10, 13):
        reddit_2016_tables.append(temp.format(str(i)))
    return reddit_2016_tables

def analyze():
    """Analyze SO content"""
    client = bigquery.Client()
    so_table = '`bigquery-public-data.stackoverflow.posts_answers`'

    reddit_2016_tables = get_reddit_tables()
    basic = 'count(*), sum(score)'

    patterns = {
        'link': '<a%_href=',
        'wiki_link': '<a%_href=%wikipedia.org/wiki/'
    }

    basic_so_queries = {
        'all': make_select(basic, so_table),
        'has_link': make_select(
            basic, so_table, "WHERE body LIKE '%{link}%'".format(**patterns)
        ),
        'has_wiki_link': make_select(
            basic, so_table, "WHERE body LIKE '%{wiki_link}%'".format(
                **patterns)
        ),
        'has_nonwiki_link': make_select(
            basic, so_table,
            "WHERE body LIKE '%{link}%' AND body NOT LIKE '%{wiki_link}%'".format(
                **patterns)
        ),
        'no_wiki_link': make_select(
            basic, so_table,
            "WHERE body NOT LIKE '%{wiki_link}%'".format(**patterns)
        ),
    }
    basic_reddit_queries = []
    for table in reddit_2016_tables:
        basic_reddit_queries.append({
            'all': make_select(basic, table),
            'has_wiki_link': make_select(
                basic, table,
                "WHERE url LIKE '%wikipedia.org/wiki/%'",
            ),
            'no_wiki_link': make_select(
                basic, table,
                "WHERE url NOT LIKE '%wikipedia.org/wiki/%'",
            ),
        })

    raw_reddit_queries = {}
    for table in reddit_2016_tables:
        raw_reddit_queries[table] = make_select(
            "COUNT(*) as subcount, subreddit", table,
            where_clause="WHERE url LIKE '%wikipedia.org/wiki/%'",
            group_by_cols='subreddit',
            order_by_cols='subcount DESC',
        )

    summed_resp_dict = {}
    for queries in basic_reddit_queries:
        resp_dict = run_basic_analysis(client, queries)
        for key0, value0 in resp_dict.items():
            if key0 not in summed_resp_dict:
                summed_resp_dict[key0] = {}
            for key1, value1 in value0.items():
                if key1 not in summed_resp_dict[key0]:
                    summed_resp_dict[key0][key1] = 0
                summed_resp_dict[key0][key1] += value1

    summed_resp_dict['has_wiki_link']['mean'] /= len(basic_reddit_queries)
    summed_resp_dict['has_wiki_link']['percentage'] /= len(
        basic_reddit_queries)

    pprint(summed_resp_dict)
    run_basic_analysis(client, basic_so_queries)
    # print_query_output(client, raw_reddit_queries)


def run_basic_analysis(client, queries):
    """Run a dictionary of queries and print the results"""
    resp_dict = {}
    for key, val in queries.items():
        query_obj = client.run_sync_query(val)
        query_obj.use_legacy_sql = False
        query_obj.run()
        vals = {}
        for row in query_obj.fetch_data():
            try:
                vals['count'], vals['sum'] = row
                vals['mean'] = vals['sum'] / vals['count']
            except TypeError:
                vals['mean'] = 'error'
        resp_dict[key] = vals
    total = resp_dict['has_wiki_link']['count'] + \
        resp_dict['no_wiki_link']['count']
    for key, val in resp_dict.items():
        resp_dict[key]['percentage'] = resp_dict[key]['count'] / total * 100
    pprint(resp_dict)
    return resp_dict


def print_query_output(client, queries):
    """For each query in 'queries', print the exact output"""
    for key, query in queries.items():
        query_obj = client.run_sync_query(query)
        query_obj.use_legacy_sql = False
        query_obj.run()
        with open(key + '.txt', 'w') as outfile:
            for row in query_obj.fetch_data():
                casted_row = [str(x) for x in row]
                line = ','.join(casted_row) + '\n'
                outfile.write(line)


# def test_fingerprint():
#     """To test winnowing algo
#     a fingerprint is of the form hashval, index
#     """
#     f = Fingerprint(kgram_len=4, window_len=5, base=10, modulo=1000)
#     answers = ['.\\test_answers1.txt']
#     answer_prints_list = []
#     wiki_pages = ['.\\test_wiki1.txt']
#     wiki_prints_list = []
#     for answer_path in answers:
#         answer_prints = f.generate(fpath=answer_path)
#         print(answer_prints)
#         answer_prints_list.append([x[0] for x in answer_prints])
#     for wiki_path in wiki_pages:
#         wiki_prints = f.generate(fpath=wiki_path)
#         print(wiki_prints)
#         wiki_prints_list.append([x[0] for x in wiki_prints])
#     for answer_prints in answer_prints_list:
#         score = 0
#         total = len(answer_prints)
#         for wiki_prints in wiki_prints_list:
#             for answer_print in answer_prints:
#                 if answer_print in wiki_prints:
#                     score += 1
#         print(score / total)


if __name__ == '__main__':
    analyze()
    # query_so_answers()
    # test_fingerprint()
