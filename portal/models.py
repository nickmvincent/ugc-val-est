"""
These models are used to define the tables in the Postgresql database for
doing data analysis
"""
from django.db import models
from django.utils import timezone

class Post(models.Model):
    """
    Abstract model representing any type of post
    Can be reddit or stack Overflow
    Can be root post or comment
        SO - root=question and comment=answer
        Reddit - root=thread and comment=comment
    """
    uid = models.CharField(max_length=100, primary_key=True)
    body = models.CharField(max_length=10000)
    score = models.IntegerField()
    is_root = models.BooleanField(default=False)
    context = models.CharField(max_length=50, null=True, blank=True)
    timestamp = models.DateTimeField()
    wiki_links = models.ManyToManyField('WikiLink')
    post_specific_wiki_links = models.ManyToManyField('PostSpecificWikiLink')
    wiki_content_analyzed = models.BooleanField(default=False)

    class Meta:
        abstract = True


class RedditPost(Post):
    """A reddit specific post"""
    user_comment_karma = models.IntegerField(default=0)
    user_link_karma = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(null=True, blank=True)
    user_is_mod = models.BooleanField(default=False)
    user_is_suspended = models.BooleanField(default=False)
    user_is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class AnnotatedRedditPost(RedditPost):
    """An annotated reddit post - annotation indicates category of discourse"""
    discourse_type = models.CharField(max_length=20)


class SampledRedditThread(RedditPost):
    """A sampled reddit THREAD using SQL Rand() function"""
    url = models.CharField(max_length=500)


class SampledStackOverflowPost(Post):
    """
    Each row corresponds to one Stack Overflow post (question or answer)
    """
    user_reputation = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(null=True, blank=True)


class PostSpecificWikiLink(models.Model):
    """
    Each row corresponding timestamped Wikipedia link that was posted
    This table mainly exists for convenience when doing analysis
    But if we decide to use other metrics than day prior, day of, week after
    We will need to use the normal WikiLink table instead
    """
    day_prior = models.ForeignKey('RevisionScore', related_name='day_prior')
    day_of = models.ForeignKey('RevisionScore', related_name='day_of')
    week_after = models.ForeignKey('RevisionScore', related_name='week_after')


class WikiLink(models.Model):
    """
    Each row corresponds to a Wikipedia article link that appeared on
    reddit or Stack Overflow

    A WikiLink object is JUST a url that links to a Wikipedi article.
    Infinitely mainly RevisionScores may be associated with one WikiLink via
    ForeignKeys (on the RevisionScore table)
    """
    url = models.CharField(max_length=500)


class RevisionScore(models.Model):
    """
    Each row is the ORES score for a given revision.
    Main purpose of this table to reduce repeat calls to Wikimedia API
    and ORES api

    ORES Score map
    Stub - 0
    Start - 1
    C - 2
    B - 3
    GA - 4
    FA - 5
    """
    timestamp = models.DateTimeField(default=timezone.now)
    wiki_link = models.ForeignKey(WikiLink)
    rev_id = models.CharField(max_length=50, primary_key=True)
    score = models.IntegerField(default=0)


class ErrorLog(models.Model):
    """Each row corresponds to a post that couldn't be loaded due to some error"""
    uid = models.CharField(max_length=100, primary_key=True)
    msg = models.CharField(max_length=255)


class ThreadLog(models.Model):
    """Each row corresponds to a full thread that has been analyzed.
    Meant for time saving purposes, in case script execution is interrupted.
    """
    uid = models.CharField(max_length=100, primary_key=True)
    complete = models.BooleanField(default=False)
