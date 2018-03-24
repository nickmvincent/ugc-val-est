# A Story of Self-Replication
## This document documents my attempt to quickly replicate my experiments from scratch with a completly fresh database and sample, in light of potential dataset issues.

Warning: this document is written in a very "note-to-self" manner, may includes grammatical errors and annoying mannerisms.

Step 1: Download updated data files from pushshift.io (we used big query last time to download json)
Why? Data up to Feb. 2016 has been patched. Want to practice running through a full setup.
`wget https://files.pushshift.io/reddit/submissions/RS_2016-02.bz2`

Shall we re-download Stack Overflow data? I decided to try, just to see how much a hassle it would be.
First, let's see if we can get the Stack Exchange Data Explorer...

Trying to get 40k likely WP posts (if this doesn't work, I don't think the 1M sample will work!):
`select top 40000 * from Posts where PostTypeId = 2 and CreationDate > '07/31/2008' and CreationDate < '06/11/2017' and Lower(body) like '%wikipedia.org/wiki/%' order by newid()`
... server timeout
We do see that there's 22M posts, which matches our Big Query DB.

Dang. Looks like we may need to just use Big Query.


`SELECT *, rand() as rand FROM [bigquery-public-data:stackoverflow.posts_answers] where creation_date > '2008-07-31 00:00:00' and creation_date < '2017-06-11 00:00:00' ORDER BY rand LIMIT 1000000;`

`SELECT *, rand() as rand FROM [bigquery-public-data:stackoverflow.posts_answers] where Lower(body) like '%wikipedia.org/wiki/%' and creation_date > '2008-07-31 00:00:00' and creation_date < '2017-06-11 00:00:00' ORDER BY rand LIMIT 40000;`

## Code update: let's "do the right thing" and use `LOWER(body) like`. It doesn't matter for this analysis (see ...) but it's the "Right Thing to Do".



Step 2: Create a fresh new database!
`sudo -u postgres psql postgres`
`CREATE DATABASE ugc_val_est_repli1 OWNER <user>;`
Set environment variables to point to this DB...
`python manage.py migrate`

Step 3: Run the scripts to get this json data into the fresh new database!
Problem #1 encountered! Looks like my original code only supported reading data from Google Cloud Storage Buckets - there's no support for loading data from local files! Looks like an upgrade will be required (or we'd have to upload the new patched data to GCS, which seems unnecssary and could cost money).
Forcing researchers who might want to use my code to use GCS seems like a bad call.
Edit: actually, looks like it's pretty simple to replace my GCS code w/ code that hits the local filesystem.

Problem #2: Oh boy! Looks like I had was switching between SO and Reddit by commenting/uncomments code. That would be a challenge for someone... let's fix it...


## Loading full Reddit JSON to my DB:
OK - I'm successfully loading Reddit data from JSON sampling new SO data from the BigQuery dataset I already downloaded.
Started the SO data sample at 11:30pm and the Reddit data load at 12:10am.
Here's another replication hiccup - I didn't the record the time that these steps should take, so current me has no idea!

## Loading full SO JSON to my DB:
Here's the results of my 1,000,000 sample of SO posts:
{'posts_attempted': 1000000, 'already_in_db': 0, 'already_in_errors': 0, 'rows_added': 984184, 'errors_added': 15816}
Runtime for iteration 0 was 15516.642497777939
Total runtime was 15516.642553329468
^ 4.3 hours

Why did some of the rows have errors again? Popped into the shell to check out one of the errors (using the ErrorLog table)
Turns out the parent_id points to a question that doesn't exist in my data dump!
Let's check it out in the Stack Exchange Data Explorer to compare.
Look's like the post should exist... so my copy of SO database is missing some questions, which is causing 1.5% of my row imports to fail.
Looking into my notes, looks like here's the reason: there was a JsonDecodeError on one of the SO json files.
Edit: I actually fixed this JsonDecodeError at the time (was able to find logs stored in email - glad I used that...)
Edit #2: I finally found the original reason. The original sampling did not include questions with a null user_id. Thus answers to these questions were not included in the sample. This makes up about 1.38% of all questions. The descriptive stats of the missing answers are extremely close to the full sample.
avg_score 2.7023899848254933
avg_comment_count 1.31398583712696

However, for the sake of the exercise and future convenience, I decided to re-download the full SO database.

stackoverflow_2018_03_17
Questions: 15483376
Answers: 24071488 (24071488)

Another Problem: didn't configure my email settings so it threw an error. This would be frustrating to anyone trying to use my code...


Here's the timing results of loading two (2016-01 and 2016-02) of the pushshift reddit files into a new DB:
processing took 16329.738641023636
open took 0.0016736984252929688
processing took 16775.153500556946
^ 4.6 hourrs


### Loading Reddit posts:
First load 1000000 random posts.
`python populate_db.py --platform r --sample 0`

Does this:
`SELECT selftext, id, score, author, created_utc, url, subreddit, num_comments, title, random() as rand FROM portal_redditpost ORDER BY rand LIMIT 1000000;`

{'posts_attempted': 1000000, 'already_in_db': 0, 'already_in_errors': 0, 'rows_added': 1000000, 'errors_added': 0}
Runtime for iteration 0 was 9805.322369098663
Total runtime was 9805.322427272797

Next load up to 40,000 WP posts.
`python populate_db.py --platform r --sample 1 --links_only --rows_to_sample 40000 --rows_per_query 40000`
Does this:
`SELECT selftext, id, score, author, created_utc, url, subreddit, num_comments, title, random() as rand FROM portal_redditpost  WHERE LOWER(portal_redditpost.url) like '%wikipedia.org/wiki/%' ORDER BY rand LIMIT 40000;`

{'posts_attempted': 20452, 'already_in_db': 1386, 'already_in_errors': 0, 'rows_added': 19066, 'errors_added': 0}
Runtime for iteration 0 was 411.9969594478607
Total runtime was 411.9970290660858

Great! All reddit posts are loaded. Now let's get all that reddit author info!
`python reddit_author_info.py all`
This code is not user friendly either - you must read the code to understand that adding an additional argument decides if you process all users or just the unprocessed ones. Not a huge deal though.



## Getting Reddit user info from the Reddit API
`python reddit_author_info.py all`
Wow! It ran with no problems. This is the first step so far that went off without a hitch.
Worth noting that I needed to make sure I had set three environment variables to use the Reddit API:
`reddit = praw.Reddit(
        client_id=os.environ["CLIENT_ID"], 
        client_secret=os.environ["CLIENT_SECRET"], user_agent=os.environ["UA"])`


## Getting WP info for Reddit posts
While I hit the Reddit API, I can also get the WP info!
Let's review how to do that...
`python check_wikipedia_content.py --platform r --mode full`
Ran into an issue because I forgot that I needed to include a start and end index (which I added to allow for "screen parallelization")
`python check_wikipedia_content.py --platform r --mode full --start 0 --end 40000`


## Running causal models for Reddit














Misc
stackoverflow_2018_03_17=> SELECT count(*), avg(portal_stackoverflowanswer.score) FROM portal_stackoverflowanswer LEFT JOIN portal_stackoverflowquestion ON portal_stackoverflowanswer.parent_id=portal_stackoverflowquestion.id WHERE portal_stackoverflowanswer.body LIKE '%wikipedia.org/wiki%' AND portal_stackoverflowquestion.owner_user_id is NULL
stackoverflow_2018_03_17-> ;
 count |        avg
-------+--------------------
  6673 | 6.1201858234677057
(1 row)

stackoverflow_2018_03_17=> SELECT count(*), avg(portal_stackoverflowanswer.score) FROM portal_stackoverflowanswer LEFT JOIN portal_stackoverflowquestion ON portal_stackoverflowanswer.parent_id=portal_stackoverflowquestion.id WHERE portal_stackoverflowanswer.body LIKE '%wikipedia.org/wiki%' AND portal_stackoverflowquestion.owner_user_id is not NULL
;
 count  |        avg
--------+--------------------
 292297 | 5.9702973345603958
(1 row)

6673 / (292297+6673) * 100
2.28%
40000 * 0.028
1120

stackoverflow_2018_03_17=> SELECT count(*), avg(portal_stackoverflowanswer.score) FROM portal_stackoverflowanswer LEFT JOIN portal_stackoverflowquestion ON portal_stackoverflowanswer.parent_id=portal_stackoverflowquestion.id WHERE portal_stackoverflowanswer.body NOT LIKE '%wikipedia.org/wiki%' AND portal_stackoverflowquestion.owner_user_id is NULL
;
 count  |        avg
--------+--------------------
 411300 | 2.8802358375881352
(1 row)

1.62%


stackoverflow_2018_03_17=> SELECT count(*), avg(portal_stackoverflowanswer.score) FROM portal_stackoverflowanswer LEFT JOIN portal_stackoverflowquestion ON portal_stackoverflowanswer.parent_id=portal_stackoverflowquestion.id WHERE portal_stackoverflowquestion.owner_user_id is not NULL                             ;
  count   |        avg
----------+--------------------
 23653515 | 2.6779522620633762

stackoverflow_2018_03_17=> SELECT count(*), avg(portal_stackoverflowanswer.score) FROM portal_stackoverflowanswer LEFT JOIN portal_stackoverflowquestion ON portal_stackoverflowanswer.parent_id=portal_stackoverflowquestion.id WHERE portal_stackoverflowanswer.body NOT LIKE '%wikipedia.org/wiki%' AND portal_stackoverflowquestion.owner_user_id is NULL
;
 count  |        avg
--------+--------------------
 411300 | 2.8802358375881352



## Simulating 
`python populate_db.py --rows_to_sample 15797 --rows_per_query 15797 --owner_null --platform s --sample_num 3`
To sample 15797 rows, will use 1 iterations with 15797 rows per iteration

    SELECT portal_stackoverflowanswer.body, portal_stackoverflowanswer.id, portal_stackoverflowanswer.score, portal_stackoverflowanswer.creation_date, portal_stackoverflowanswer.comment_count, portal_stackoverflowuser.reputation, portal_stackoverflowuser.creation_date as user_created_utc, portal_stackoverflowquestion.view_count, portal_stackoverflowquestion.answer_count, portal_stackoverflowquestion.title, portal_stackoverflowquestion.comment_count, portal_stackoverflowquestion.score, portal_stackoverflowquestion.creation_date as question_asked_utc, portal_stackoverflowquestion.tags, random() as rand
    FROM portal_stackoverflowanswer
            LEFT JOIN portal_stackoverflowuser ON portal_stackoverflowanswer.owner_user_id = portal_stackoverflowuser.id
            LEFT JOIN portal_stackoverflowquestion ON portal_stackoverflowanswer.parent_id = portal_stackoverflowquestion.id
              WHERE portal_stackoverflowquestion.owner_user_id is NULL and portal_stackoverflowanswer.creation_date < '2017-06-11 00:00:00' ORDER BY rand LIMIT 15797;

[(24071488,)]
{'posts_attempted': 15797, 'already_in_db': 101, 'already_in_errors': 0, 'rows_added': 15696, 'errors_added': 0}
Runtime for iteration 0 was 438.0836570262909
Total runtime was 438.0837275981903


`python populate_db.py --rows_to_sample 1120 --rows_per_query 1120 --owner_null --platform s --sample_num 4 --links_only`
To sample 1120 rows, will use 1 iterations with 1120 rows per iteration

    SELECT portal_stackoverflowanswer.body, portal_stackoverflowanswer.id, portal_stackoverflowanswer.score, portal_stackoverflowanswer.creation_date, portal_stackoverflowanswer.comment_count, portal_stackoverflowuser.reputation, portal_stackoverflowuser.creation_date as user_created_utc, portal_stackoverflowquestion.view_count, portal_stackoverflowquestion.answer_count, portal_stackoverflowquestion.title, portal_stackoverflowquestion.comment_count, portal_stackoverflowquestion.score, portal_stackoverflowquestion.creation_date as question_asked_utc, portal_stackoverflowquestion.tags, random() as rand
    FROM portal_stackoverflowanswer
            LEFT JOIN portal_stackoverflowuser ON portal_stackoverflowanswer.owner_user_id = portal_stackoverflowuser.id
            LEFT JOIN portal_stackoverflowquestion ON portal_stackoverflowanswer.parent_id = portal_stackoverflowquestion.id
              WHERE portal_stackoverflowquestion.owner_user_id is NULL and Lower(portal_stackoverflowanswer.body) like '%wikipedia.org/wiki/%' and portal_stackoverflowanswer.creation_date < '2017-06-11 00:00:00' ORDER BY rand LIMIT 1120;

[(24071488,)]
{'posts_attempted': 1120, 'already_in_db': 59, 'already_in_errors': 0, 'rows_added': 1061, 'errors_added': 0}
Runtime for iteration 0 was 262.6569736003876
Total runtime was 262.65703415870667

