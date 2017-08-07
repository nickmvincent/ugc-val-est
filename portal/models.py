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
    body = models.CharField(max_length=30000)
    score = models.IntegerField()
    num_comments = models.IntegerField(default=0)
    is_root = models.BooleanField(default=False)
    context = models.CharField(max_length=115, null=True, blank=True)
    author = models.CharField(max_length=50)
    timestamp = models.DateTimeField()

    wiki_links = models.ManyToManyField('WikiLink')
    has_wiki_link = models.BooleanField(default=False)
    num_wiki_links = models.IntegerField(default=0)

    post_specific_wiki_links = models.ManyToManyField('PostSpecificWikiScores')
    wiki_content_analyzed = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def day_of_week(self):
        """Returns a number corresponding to the day of posting"""
        return self.timestamp.weekday()

    def day(self):
        """Returns a number corresponding to the day of posting"""
        return self.timestamp.day

    def hour(self):
        """Returns a number corresponding to the day of posting"""
        return self.timestamp.hour


class RedditPost(Post):
    """A reddit specific post"""
    user_info_processed = models.BooleanField(default=False)
    user_comment_karma = models.IntegerField(default=0)
    user_link_karma = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(null=True, blank=True)
    user_is_mod = models.BooleanField(default=False)
    user_is_suspended = models.BooleanField(default=False)
    user_is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


# class AnnotatedRedditPost(RedditPost):
#     """An annotated reddit post - annotation indicates category of discourse"""
#     discourse_type = models.CharField(max_length=20)


class SampledRedditThread(RedditPost):
    """A sampled reddit THREAD using SQL Rand() function"""
    url = models.CharField(max_length=2083)
    title = models.CharField(max_length=500)
    
    def title_length(self):
        """Returns the length of the title in the title field"""
        return len(self.title)


class SampledStackOverflowPost(Post):
    """
    Each row corresponds to one Stack Overflow post (question or answer)
    """
    user_reputation = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(null=True, blank=True)
    num_pageviews = models.IntegerField(default=0)
    tags_string = models.CharField(max_length=115, blank=True, null=True)


class PostSpecificWikiScores(models.Model):
    """
    Each row corresponding timestamped Wikipedia link that was posted
    This table mainly exists for convenience when doing analysis
    But if we decide to use other metrics than day prior, day of, week after
    We will need to use the normal WikiLink table instead
    """
    day_prior = models.ForeignKey('RevisionScore', related_name='day_prior')
    day_of = models.ForeignKey('RevisionScore', related_name='day_of')
    week_after = models.ForeignKey('RevisionScore', related_name='week_after')

WIKI_PATTERN = 'wikipedia.org/wiki/'

class WikiLink(models.Model):
    """
    Each row corresponds to a Wikipedia article link that appeared on
    reddit or Stack Overflow

    A WikiLink object is JUST a url that links to a Wikipedi article.
    Infinitely mainly RevisionScores may be associated with one WikiLink via
    ForeignKeys (on the RevisionScore table)
    """
    url = models.CharField(max_length=300)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    title = models.CharField(max_length=300, blank=True, null=True)

    def save(self, *args, **kwargs):
        """overload save method"""
        url = self.url.replace('.m.', '.')
        url = url.replace('www.', '')
        prefix_start = url.find('//') + 2
        prefix_end = url.find('.wiki')
        if prefix_end == -1:
            code = 'en'
        else:
            code = url[prefix_start:prefix_end]
        self.language_code = code
        i = url.find(WIKI_PATTERN) + len(WIKI_PATTERN)
        url_query_params = url.find('?')
        if url_query_params != -1:
            self.title = url[i:url_query_params]
        else:
            self.title = url[i:]
        super(WikiLink, self).save(*args, **kwargs)


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
    revid = models.CharField(max_length=50, primary_key=True)
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


class StackOverflowQuestion(models.Model):
    """
    Each row corresponds to a StackOverflow question.
    Matches BigQuery almost exactly.
    """
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=192)
    body = models.CharField(max_length=58431)
    accepted_answer_id = models.IntegerField()
    answer_count = models.IntegerField()
    comment_count = models.IntegerField()
    community_owned_date = models.DateTimeField()
    creation_date = models.DateTimeField()
    favorite_count = models.IntegerField()
    last_activity_date = models.DateTimeField()
    last_edit_date = models.DateTimeField()
    last_editor_display_name = models.CharField(max_length=30)
    last_editor_user_id = models.IntegerField()
    owner_display_name = models.CharField(max_length=30)
    owner_user_id = models.IntegerField()
    post_type_id = models.IntegerField()
    score = models.IntegerField()
    tags = models.CharField(max_length=115)
    view_count = models.IntegerField()


class StackOverflowAnswer(models.Model):
    """
    Each row corresponds to a StackOverflow answers.
    Matches BigQuery almost exactly.
    """
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=192)
    body = models.CharField(max_length=58431)
    accepted_answer_id = models.IntegerField()
    answer_count = models.IntegerField()
    comment_count = models.IntegerField()
    community_owned_date = models.DateTimeField()
    creation_date = models.DateTimeField()
    favorite_count = models.IntegerField()
    last_activity_date = models.DateTimeField()
    last_edit_date = models.DateTimeField()
    last_editor_display_name = models.CharField(max_length=30)
    last_editor_user_id = models.IntegerField()
    owner_display_name = models.CharField(max_length=30)
    owner_user_id = models.IntegerField()
    post_type_id = models.IntegerField()
    score = models.IntegerField()
    tags = models.CharField(max_length=115)
    view_count = models.IntegerField()
