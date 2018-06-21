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
This code uses the "Anaconda" distribution of Python, which includes numpy, scipy, etc.
A full copy of requirements from "pip freeze" is available in full_req.txt.
The output of "conda env export -n ugc-val-est > environment.yml" is in environment.yml

This research code uses the python "Django" library, traditionally used for web applications.
In this code, Django's ORM is used to interface with the postgresql database.
The database is set up to use postgres, but can be changed.
The django docs (https://www.djangoproject.com/) can answer almost all django-specific issues.

To configure DB (password, etc, refer to `settings.py`), you may wish to use environment variables.
Once you can connect to DB (try `python manage.py shell`) to make all the appropriate DB tables etc
`python manage.py migrate`.


# Code Roadmap
To help navigate, here is a roadmap of the code.


## Code that controls all settings:
dja/settings.py

## Code related to calculating descriptive stats (with numpy):
stats.py
* central tendencies for all covariates
* frequency plots (e.g. what's the top website linked to from Stack Overflow? What are the most common tags on Stack Overflow)
* Differences in covariates
* there's some slightly hacky logic in here. Some fields should be compared directly between treatment and control (i.e. post score), while in some case we actually want to compare TWO fields to each other (e.g. num_edits_prev_week vs. num_edits). This logic is mostly handled by the `rq` parameter, which orginally corresponded to three different research questions. That mapping is no longer accurate, but instead the `rq` parameter is used to just store a bunch of configurations (i.e. what counts as control, what field to compute, etc.)

## Code related to Causal Analysis (uses numpy, causalinference libraries)
### High-level: prediction.py
* can add/remove/transform the covariates used in propensity score matching here
* can change causal analysis choices here. Some through command line args, e.g. should we trim extreme values, should we have interaction terms in the logistic propensity score regression
* can add more causal analyses here
### Low-level: causalinference (this is a slightly modified copy of the BSD 3-clause licensed library, from here: https://github.com/laurencium/Causalinference)
* There's only two additions from the original version.
1. added logic to automatically remove covariates as they become "obsolete" for a strata (e.g. if a field would constant across the strata, such is if every post in that strata has length 10, or because a dummy variable become linearly dependent, such as if all the posts in the strata took place in 3 months)
2. Added a bunch of print statement. Most notable is that we print out the normalized covariates bias at the beginning, after trimming, and after matching, so we can that covariate bias is going down.
* can make low-level edits here, i.e. exactly how is regression calculated, what to print out about the analysis, etc.

## Code related to database management (this is where most features are calculated)
portal/models.py
* the fields for each databases table are computed in the corresponding `save` method.
* i.e. the see how sentiment is computed for Posts, check the `save` method of the `Post` class.
* SO posts and Reddit post both inherit from Post, so most code is re-used.

## Code related to get information from various Wikipedia APIs
check_wikipedia_content.py
* hits revisions API, users API, pageviews api, ORES, etc
* there are some small analyses available in here too, like how often post get reverted.

## Code that gets info from Reddit API
reddit_author_info.py

## Code used to populate DB from a json file
json2db.py
* could download from BigQuery
* can download Reddit data directly from pushshift
* can download SO data from archive.org

## Code used to explore BigQuery (e.g. compute descriptive stats)
bq_explore.py
* very helpful as a "smell check", because we can verify our descriptive stats match the full dataset!
* e.g. are we sure that Reddit posts really have 5x the score, and we didn't make a sampling error? Thanks to BigQuery, we can be very sure!

# Dataset
To clarify, this repo includes the code to collect your own random sample of posts/answers.
Alternatively, if you want to inspect or play with the exact sample and processed data used in our study, that exact dataset is linked below.

Annotated dataset download (has ~1.04M Reddit posts, ~1.04M Stack Overflow answers, all necessary features pre-calculated, and all revelant Wikipedia information populated). Format is a single .sql file produced by postgres pg_dump command line utility. Total size is ~2GB.
https://drive.google.com/file/d/1rJvaEeYbMlXNqDFUVoGqKQkaqG0Hnfoi/view?usp=sharing
This .sql file is contains the exact state of data that was used to produced results reported in the table.
The corresponding outputs can be found here: https://github.com/nickmvincent/ugc-val-est/tree/15082729f0286e3964eb4aed718934984fa89266


Therefore, you have the choice to reproduce this experiment with your own sample or replicate the reported results exactly.
Or make your own modifications as you see fit!

Notes about this 2GB data dump:
* To produce the Stack Overflow overly conservative pageview estimates (argument --rq 13 and --rq 14 in stats.py, argument --is-top for prediction.py) you will need to full SO Questions database (to look up the other answers associated w/ a given question). This is is the only output that cannot be run using only the ~1.04M post samples. See "Study One" in the paper for more details.
* Non-English Wikipedia links are not fully supported (as there are very few non-English Wikipedia links in our aggregate analysis). See "implementation_details.md" for more details.
* WP article pageviews are calculated with daily pageviews

Please note that:
* There's been some slight updates since the paper was published: fixed some edge cases, started adding support for non-English wikipedia, started doing a small bit of code clean-up. So if you want to replicate the paper exactly, you should use the "published results" copy of the code, available under "Releases" in Github.
* The pushshift Reddit dataset had some issues with missing posts.
See this excellent work by Devin Gaffney and J. Nathan Matias for details. https://arxiv.org/abs/1803.05046
We analyzed the missing data to get a sense of whether it should affect our results (based on whether or not there was a substantial amount of Wikipedia posts missing, among other things), and also replicated the study (from scratch) with a patched dataset to verify our conclusions held.

While it didn't affect our particular analysis (which was mainly concerned with platform-wide differences in scores and comments), it might affect other analyses, so for new research it's probably best to collect a new sample of data.
If you're interested in using this code to do so, feel free to check out "self_replication.md", where I document the process of replicating my own study (it was a bit harder than I expected!)