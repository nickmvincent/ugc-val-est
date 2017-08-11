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
    body = models.CharField(max_length=58431)
    body_length = models.IntegerField(default=0)
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
    # poor naming choices... the following refer to ORES score...
    day_prior_avg_score = models.IntegerField(blank=True, null=True)
    day_of_avg_score = models.IntegerField(blank=True, null=True)
    week_after_avg_score = models.IntegerField(blank=True, null=True)

    wiki_content_analyzed = models.BooleanField(default=False)
    wiki_content_error = models.IntegerField(default=False)

    day_of_week = models.IntegerField(blank=True, null=True)
    day_of_month = models.IntegerField(blank=True, null=True)
    hour = models.IntegerField(blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """overload save method"""
        self.day_of_week = self.timestamp.weekday()
        self.day_of_month = self.timestamp.day
        self.hour = self.timestamp.hour
        super(Post, self).save(*args, **kwargs)




# class AnnotatedRedditPost(RedditPost):
#     """An annotated reddit post - annotation indicates category of discourse"""
#     discourse_type = models.CharField(max_length=20)


class SampledRedditThread(Post):
    """A sampled reddit THREAD using SQL Rand() function"""
    user_info_processed = models.BooleanField(default=False)
    user_comment_karma = models.IntegerField(default=0)
    user_link_karma = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(null=True, blank=True)
    user_is_mod = models.BooleanField(default=False)
    user_is_suspended = models.BooleanField(default=False)
    user_is_deleted = models.BooleanField(default=False)
    url = models.CharField(max_length=2083)
    title = models.CharField(max_length=500)
    title_length = models.IntegerField(default=0)
    

    def save(self, *args, **kwargs):
        """overload save method"""
        self.title_length = len(self.title)
        super(SampledRedditThread, self).save(*args, **kwargs)

class SampledStackOverflowPost(Post):
    """
    Each row corresponds to one Stack Overflow post (question or answer)
    """
    user_reputation = models.IntegerField(default=0)
    user_created_utc = models.DateTimeField(null=True, blank=True)
    num_pageviews = models.IntegerField(default=0)
    tags_string = models.CharField(max_length=115, blank=True, null=True)

    def user_age_at_post_time(self):
        """Gives the users age at the time of posting this post"""
        delta = self.timestamp - self.user_created_utc
        return delta.total_seconds()

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

    A WikiLink object is JUST a url that links to a Wikipedia article.
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
    msg = models.CharField(max_length=500)


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

class StackOverflowUser(models.Model):
    """
    Each row corresponds to a SO user from BigQuery table
    """
    id = models.IntegerField(primary_key=True)
    display_name = models.CharField(max_length=30)
    about_me = models.CharField(max_length=5999)
    age = models.CharField(max_length=4)
    creation_date = models.DateTimeField()
    last_access_date = models.DateTimeField()
    location = models.CharField(max_length=100)
    reputation = models.IntegerField()
    up_votes = models.IntegerField()
    down_votes = models.IntegerField()
    views = models.IntegerField()
    profile_image_url = models.CharField(max_length=105)
    website_url = models.CharField(max_length=200)


class RedditPost(models.Model):
    """
    Each row corresponds to a reddit post
    
    Omitted misleading fields or non-helpful fields
    
    from_kind - always null
    from - always null
    from_id - always null
    downs - always zero
    ups - always equal to score
    """
    created_utc	= models.IntegerField()
    subreddit = models.CharField(max_length=21)
    author = models.CharField(max_length=20)
    domain = models.CharField(max_length=206)
    url = models.CharField(max_length=6843)
    num_comments = models.IntegerField()
    score = models.IntegerField()
    title = models.CharField(max_length=329)
    selftext = models.CharField(max_length=59994)
    saved = models.BooleanField()
    id = models.CharField(primary_key=True, max_length=10)
    gilded = models.IntegerField()
    stickied = models.BooleanField()
    retrieved_on = models.IntegerField()
    over_18 = models.BooleanField()
    thumbnail = models.CharField(max_length=80)
    subreddit_id = models.CharField(max_length=8)
    hide_score = models.BooleanField()
    link_flair_css_class = models.CharField(max_length=61)
    author_flair_css_class = models.CharField(max_length=92)
    archived = models.BooleanField()
    is_self = models.BooleanField()
    permalink = models.CharField(max_length=125)
    name = models.CharField(max_length=9)
    author_flair_text = models.CharField(max_length=89)
    quarantine = models.BooleanField()
    link_flair_text = models.CharField(max_length=67)
    distinguished = models.CharField(max_length=9)