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
The corresponding outputs can be found here: https://github.com/nickmvincent/ugc-val-est/tree/15082729f0286e3964eb4aed718934984fa89266


Therefore, you have the choice to reproduce this experiment with your own sample or replicate the reported results exactly.
Or make your own modifications as you see fit!

Notes about this 2GB data dump:
* To produce the Stack Overflow overly conservative pageview estimates (argument --rq 13 and --rq 14 in stats.py, argument --is-top for prediction.py) you will need to full SO Questions database (to look up the other answers associated w/ a given question). This is is the only output that cannot be run using only the ~1.04M post samples. See "Study One" in the paper for more details.
* Non-English Wikipedia links are not fully supported (as there are very few non-English Wikipedia links in our aggregate analysis). See "implementation_details.md" for more details.
* WP article pageviews are calculated with daily pageviews