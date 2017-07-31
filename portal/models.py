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
    context = models.CharField(max_length=50) # TODO
    timestamp = models.DateTimeField()
    wiki_links = models.ManyToManyField('WikiLink')
    wiki_content_analyzed = models.BooleanField(default=False)

    class Meta:
        abstract = True


class RedditPost(Post):
    """A reddit specific post"""
    user_comment_karma = models.IntegerField(default=0)
    user_link_karma = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(default=timezone.now)
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
    url = models.CharField(max_length=255)


class StackOverflowPost(Post):
    """
    Each row corresponds to one Stack Overflow post (question or answer)
    """
    user_reputation = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(default=timezone.now)



class WikiLink(models.Model):
    """
    Each row corresponds to a Wikipedia article link that appeared on
    reddit or Stack Overflow
    """
    url = models.CharField(max_length=255)
    day_prior = models.ForeignKey('RevisionScore', related_name='day_prior')
    day_of = models.ForeignKey('RevisionScore', related_name='day_of')
    week_after = models.ForeignKey('RevisionScore', related_name='week_after')


class RevisionScore(models.Model):
    """
    Each row is the ORES score for a given revision.
    Main purpose of this table to reduce repeat calls to Wikimedia API
    and ORES api
    """
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