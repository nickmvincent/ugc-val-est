This research code uses
the django library, traditionally used for web applications, as its ORM (access to DB)
The database is set up to use postgres, but can be changed
The django docs (https://www.djangoproject.com/) can answer almost all django-specific issues


To configure DB (password, etc, refer to `settings.py`)
You may wish to use environment variables to set DB name, DB password etc
One you can connect to DB (try `python manage.py shell`)
To make all the appropriate DB tables etc
python manage.py migrate

Now you can 