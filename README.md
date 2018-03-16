# About
This is the code for the 2018 CHI paper "Examining Wikipedia with a Broader Lens: Quantifying the Value of Wikipedia's Relationships with Other Large-Scale Online Communities. ACM Conference on Human Factors in Computing Systems 2018".
It consists of data collection, data processing, and data analysis.

This code is still in the "research state", and not guaranteed to be suitable for re-purposing.
The purpose in sharing it is to give insight into the exact methods (such as feature calculation, analysis choices, etc).
If you are interested in using parts of this research code for other projects and are running into issues, do feel free to reach out.
Likewise, if you have any questions about the analysis or have any suggestions for improvement, please don't hesitate to reach out.
www.nickmvincent.com

Preprint paper is here: http://www.brenthecht.com/publications/chi2018_wikipediavaluetoonlinecommunities.pdf
ACM DL link is forthcoming.

Example citation:
Vincent, N., Johnson, I., and Hecht, B. Examining Wikipedia with a Broader Lens: Quantifying the Value of Wikipedia's Relationships with Other Large-Scale Online Communities. ACM Conference on Human Factors in Computing Systems 2018

# Installation
This code uses the "Anaconda" distribution of Python, which includes numpy, scipy, etc
A full copy of requirements from "pip freeze" is available in full_req.txt
The output of "conda env export -n ugc-val-est > environment.yml" is in environment.yml

This research code uses the python "Django" library, traditionally used for web applications.
In this code, Django's ORM is used to interface with the postgresql database.
The database is set up to use postgres, but can be changed.
The django docs (https://www.djangoproject.com/) can answer almost all django-specific issues

To configure DB (password, etc, refer to `settings.py`)
You may wish to use environment variables to set DB name, DB password etc
One you can connect to DB (try `python manage.py shell`)
To make all the appropriate DB tables etc
python manage.py migrate



# Code Roadmap
To help navigate, here is a roadmap of the code
Quick roadmap:
Code that controls all settings:
dja/settings.py

Code related to calculating descriptive stats (with numpy):
stats.py

Code related to Causal Analysis (uses numpy, causalinference libraries)
High-level: prediction.py
Low-level: causalinference (this is a slightly modified copy of the BSD 3-clause licensed library, from here: https://github.com/laurencium/Causalinference)

Code related to database managements (this is where most features are calculated)
portal/models.py

Code related to get information from Wikipedia API
check_wikipedia_content.py

Code that gets info from Reddit API
reddit_author_info.py

Code used to populate DB from a json file (we downloaded json from BigQuery)
json2db.py

Code used to explore BigQuery (e.g. compute descriptive stats)
bq_explore.py

# Dataset
To clarify, this repo includes the code to collect your own random sample of posts/answers.
Alternatively, if you want to inspect or play with the exact sample and processed data used in our study, that dataset is linked below.

Annotated dataset download (has ~1.04M Reddit posts, ~1.04M Stack Overflow answers, all necessary features pre-calculated, and all revelant Wikipedia information populated). Format is a single .sql file produced by postgres pg_dump command line utility. Total size is ~2GB.
https://drive.google.com/file/d/1rJvaEeYbMlXNqDFUVoGqKQkaqG0Hnfoi/view?usp=sharing
This .sql file is contains the exact state of data that was used to produced results reported in the table.
Therefore, you have the choice to reproduce this experiment with your own sample or replicate the reported results exactly.
Or make your own modifications as you see fit!

Notes about this 2GB data dump:
* To produce the Stack Overflow overly conservative pageview estimates (argument --rq 13 and --rq 14 in stats.py, argument --is-top for prediction.py) you will need to full SO Questions database (to look up the other answers associated w/ a given question). This is is the only output that cannot be run using only the ~1.04M post samples. See "Study One" in the paper for more details.
* Non-English Wikipedia links are not properly supported. See below for more details.

# A note on some design choices

What to do with broken links?
People often post broken links (e.g. they typed out a Wikipedia article name and mispelled it, the article doesn't exist, etc)
We chose the following pattern:
If the Wikimedia API returns a "missing" error message when trying to get information about the article, mark it as NOT a valid Wikipedia link.
The full list of such urls (only 300 Wikipedia links from 48k SO posts and 36k Reddit posts) is in "url_list.csv" in this folder and that csv file is regenerated when running the full analysis batch in "batch.sh".

If we didn't get a "missing" error from the Wikimedia API, but we also couldn't actually get ANY revisions (in the 2 week period around the post, or before), mark that post so we can see how many meet that criteria. Only ~50 met that criteria.

For non-English Wikipedia links, don't try to hit the APIs.
We didn't add explicit handling for non-English Wikipedia links becuase posts with non-English Wikipedia posts make up less than 2% of our Reddit posts and less than 1% of SO posts.

Known issues related to non-English articles:
* By default non-English posts are treated as "stub" articles and don't contribute to pageviews/edits. 
This has no effect on the analysis of WP links vs non-WP links. However, it's possible this could affect our quality analysis, or our Reddit/SO effects on WP analysis. Therefore, we re-ran the analyses with and without these posts included to make sure this wasn't affecting results in any way - it wasn't.
* Links to Wikipedia articles that are not English Wikipedia, but share a title with an English wikipedia article, may be erroneously associated with the ORES score for that Wikipedia article.
This bug affects only 44 (0.1%) Reddit posts and 99 (0.2%) SO posts.
Example: https://de.wikipedia.org/wiki/File_Transfer_Protocol

Much more careful consideration of non-English Wikipedia posts would be very important for follow-up work that focuses on specific communities (especially sub-reddits that do not use English) or any work that wants to examine effects across different language communities. That being said, the current state of this code is not capable of properly analyzing subcommunities with many links to non-Englosh Wikipedia.

Use of Pageview API: we used the mediawiki pageview API, which (1) returns daily page views and (2) does not return results for dates before Oct. 2015. Therefore, links from before Oct. 2015 are not included in the page view analysis.