from django.db import models

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


    class Meta:
        abstract = True


class RedditPost(Post):
    """A reddit specific post"""
    user_comment_karma = models.IntegerField()
    user_link_karma = models.IntegerField()
    user_created_utc = models.DateTimeField()
    user_is_mod = models.BooleanField()

    class Meta:
        abstract = True


class AnnotatedRedditPost(RedditPost):
    """An annotated reddit post - annotation indicates category of discourse"""
    discourse_type = models.CharField(max_length=20)



class WikiLink(models.Model):
    """
    Each row corresponds to a Wikipedia article link that appeared on
    reddit or Stack Overflow
    """
    url = models.CharField(max_length=255)
    
class WikiScore(models.Model):
    """
    Each row correspnds to a set of scores for a WikiLink for a given date
    """
    link = models.ForeignKey(WikiLink)
    timestamp = models.DateTimeField()
    day_prior_rev_id = models.CharField(max_length=50)
    day_prior_ores_score = models.IntegerField()
    day_of_rev_id = models.CharField(max_length=50)
    day_of_ores_score = models.IntegerField()


class ErrorLog(models.Model):
    """Each row corresponds to a post that couldn't be loaded due to some error"""
    uid = models.CharField(max_length=100, primary_key=True)
    msg = models.CharField(max_length=255)