# A Story of Self-Replication
## This document documents my attempt to quickly replicate my experiments from scratch with a completly fresh database and sample, in light of potential dataset issues.

Warning: this document is written in a very "note-self" manner, may includes grammatical errors and annoying mannerisms.

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

OK - I'm successfully loading Reddit data from JSON sampling new SO data from the BigQuery dataset I already downloaded.
Started the SO data sample at 11:30pm and the Reddit data load at 12:10am.
Here's another replication hiccup - I didn't the record the time that these steps should take, so current me has no idea!

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
At the time, I believed this was a BigQuery Error, and I decided this would not cause substantial bias, and so did not investigate the problem immensely.
As a quick exercise, I took a look at average Score, CommentCount, and dates of the 1.5% missing to estimate the effect of our analysis (which uses sampling and looks at aggregates, such that a small amount of missing posts would minimally affect results).
avg_score 2.7023899848254933
avg_comment_count 1.31398583712696



Here's the timing results of loading two (2016-01 and 2016-02) of the pushshift reddit files into a new DB:
processing took 16329.738641023636
open took 0.0016736984252929688
processing took 16775.153500556946
^ 4.6 hourrs
