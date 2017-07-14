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
import requests
import os
from pprint import pprint

from fingerprint import Fingerprint
import html2text
from google.cloud import bigquery


def query_so_answers():
    client = bigquery.Client()
    query_results = client.run_sync_query("""
        SELECT
            body FROM `bigquery-public-data.stackoverflow.posts_answers`
            WHERE body NOT LIKE '%wikipedia.org%';
        """)

    query_results.use_legacy_sql = False
    query_results.run()

    # Drain the query results by requesting a page at a time.
    page_token = None
    num_to_print = 2000
    printed = 0

    resp = query_results.fetch_data(
        max_results=10,
        page_token=page_token)
    print(resp)
    for iterable in resp:
        print('Show another?')
        _ = input()
        text = html2text.html2text(iterable[0])
        print(iterable[0])
        print(text)
        base = 'https://en.wikipedia.org/w/api.php?'
        config = 'action=query&list=search&format=json&'
        search_params = 'srsearch={}&srwhat=text'.format(text)
        wiki_resp = requests.get('{}{}{}'.format(
            base, config, search_params
        ))
        print(wiki_resp.json())
        _ = input()


def analyze():
    """Analyze SO content"""
    client = bigquery.Client()
    so_query = """
    SELECT
        count(*), sum(score)
        FROM `bigquery-public-data.stackoverflow.posts_answers` {};"""
    reddit_query = """
    SELECT
        count(*), sum(score)
        FROM `fh-bigquery.reddit_comments.2014` {}; """

    so_queries = {
        'all': so_query.format(""),
        'has_link': so_query.format(
            "WHERE body LIKE '%<a%_href=%'"
        ),
        'has_wiki_link': so_query.format(
            "WHERE body LIKE '%<a%_href=%wikipedia.org/wiki/%'"),
        'has_nonwiki_link': so_query.format(
            "WHERE body LIKE '%<a%_href=%' AND body NOT LIKE '%wikipedia.org/wiki/%'"),
        'no_wiki_link': so_query.format(
            "WHERE body NOT LIKE '%wikipedia.org/wiki/%'"),
    }
    reddit_queries = {
        'all': reddit_query.format(""),
        'has_wiki_link': reddit_query.format(
            "WHERE body LIKE '%wikipedia.org/wiki/%'"
        ),
        'no_wiki_link': reddit_query.format(
            "WHERE body NOT LIKE '%wikipedia.org/wiki/%'"
        )
    }
    #run_queries(client, so_queries)
    run_queries(client, reddit_queries)

def run_queries(client, queries):
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
    total = resp_dict['has_wiki_link']['count'] + resp_dict['no_wiki_link']['count']
    for key, val in resp_dict.items():
        resp_dict[key]['percentage'] = resp_dict[key]['count'] / total * 100
    pprint(resp_dict)


def test_fingerprint():
    """To test winnowing algo
    a fingerprint is of the form hashval, index
    """
    f = Fingerprint(kgram_len=4, window_len=5, base=10, modulo=1000)
    answers = ['.\\test_answers1.txt']
    answer_prints_list = []
    wiki_pages = ['.\\test_wiki1.txt']
    wiki_prints_list = []
    for answer_path in answers:
        answer_prints = f.generate(fpath=answer_path)
        print(answer_prints)
        answer_prints_list.append([x[0] for x in answer_prints])
    for wiki_path in wiki_pages:
        wiki_prints = f.generate(fpath=wiki_path)
        print(wiki_prints)
        wiki_prints_list.append([x[0] for x in wiki_prints])
    for answer_prints in answer_prints_list:
        score = 0
        total = len(answer_prints)
        for wiki_prints in wiki_prints_list:
            for answer_print in answer_prints:
                if answer_print in wiki_prints:
                    score += 1
        print(score/total)
if __name__ == '__main__':
    # set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\nickm\Desktop\research\wikipedia_and_stack_overflow\client_secrets.json
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:\\Users\\nickm\\Desktop\\research\\wikipedia_and_stack_overflow\\client_secrets.json"
    analyze()
    # query_so_answers()
    # test_fingerprint()