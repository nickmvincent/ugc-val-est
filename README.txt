Installation
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

This code is still in the "research state", and not yet ready for widespread distribution or forking.
The purpose in sharing it is to give insight into the exact methods, feature calculation, etc used

To help navigate, here is a roadmap of the code
Quick roadmap:
Code that controls all settings:
dja/settings.py

Code related to calculating descriptive stats (with numpy):
stats.py

Code related to Causal Analysis (uses numpy, causalinference libraries)
High-level: prediction.py
Low-level: causalinference (this is a modified copy of the BSD 3-clause licensed library, from here: https://github.com/laurencium/Causalinference)

Code related to database managements (this is where most features are calculated)
portal/models.py

Code related to get information from Wikipedia API
check_wikipedia_content.py

Code that gets info from Reddit API
reddit_author_info.py

Code used to populate DB from a json file (downloaded from BigQuery)
json2db.py

Code used to explore BigQuery
bq_explore.py