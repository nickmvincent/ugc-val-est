# A Story of Self-Replication
## This document documents my attempt to quickly replicate my experiments from scratch with a completly fresh database and sample, in light of potential dataset issues.

Step 1: Download updated data files from pushshift.io (we used big query last time to download json)
Why? Data up to Feb. 2016 has been patched. Want to practice running through a full setup.
`wget https://files.pushshift.io/reddit/submissions/RS_2016-02.bz2`

Shall we re-download Stack Overflow data? I decided to try, just to see how much a hassle it would be.
Otherwise, I'd need to get the SO tables back into GCS.
But first, let's see if we can get the Stack Exchange Data Explorer...

Trying to get 40k likely WP posts (if this doesn't work, I don't think the 1M sample will work!):
`select top 40000 *
from Posts
where PostTypeId = 2 and CreationDate > '07/31/2008' and CreationDate < '06/11/2017' and Lower(body) like '%wikipedia.org/wiki/%'
order by newid()`
... server timeout

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