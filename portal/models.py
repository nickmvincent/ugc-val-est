"""
These models are used to define the tables in the Postgresql database for
doing data analysis
"""
# pylint:disable=C0103

import datetime
from django.db import models
from django.utils import timezone
from url_helpers import extract_urls

from textstat.textstat import textstat


def trimmed(val, floor, ceil):
    """floors and ceils a val"""
    floored = max(val, floor)
    ceiled = min(floored, ceil)
    return ceiled


def get_closest_to(qs, target):
    """Returns the closest object in time"""
    closest_greater_qs = qs.filter(timestamp__gt=target).order_by('timestamp')
    closest_less_qs = qs.filter(timestamp__lt=target).order_by('-timestamp')
    try:
        closest_greater = closest_greater_qs[0]
    except IndexError:
        return closest_less_qs[0]
    try:
        closest_less = closest_less_qs[0]
    except IndexError:
        return closest_greater_qs[0]

    if closest_greater.timestamp - target > target - closest_less.timestamp:
        return closest_less
    return closest_greater


class Post(models.Model):
    """
    Abstract model representing any type of post
    Can be reddit or stack Overflow
    Can be root post or comment
        SO - root=question and comment=answer
        Reddit - root=thread and comment=comment
    """
    uid = models.CharField(max_length=100, primary_key=True)

    body = models.CharField(max_length=74185)
    # textual metrics for the body field
    body_length = models.IntegerField(default=0)
    body_lexicon_count = models.IntegerField(default=0)
    body_sentence_count = models.IntegerField(default=0)
    body_num_links = models.IntegerField(default=0)
    body_percent_uppercase = models.IntegerField(default=0)
    body_percent_spaces = models.IntegerField(default=0)
    body_percent_punctuation = models.IntegerField(default=0)
    body_starts_capitalized = models.BooleanField(default=False)
    body_coleman_liau_index = models.IntegerField(default=0)

    # textual metrics for the title field
    title = models.CharField(max_length=1182, default="")
    title_length = models.IntegerField(default=0)
    title_lexicon_count = models.IntegerField(default=0)
    title_sentence_count = models.IntegerField(default=0)
    title_percent_uppercase = models.IntegerField(default=0)
    title_percent_spaces = models.IntegerField(default=0)
    title_percent_punctuation = models.IntegerField(default=0)
    title_starts_capitalized = models.BooleanField(default=False)
    title_coleman_liau_index = models.IntegerField(default=0)

    score = models.IntegerField()
    num_comments = models.IntegerField(default=0)

    is_root = models.BooleanField(default=False)
    context = models.CharField(max_length=115, null=True, blank=True)
    author = models.CharField(max_length=36)
    timestamp = models.DateTimeField()

    wiki_links = models.ManyToManyField('WikiLink')
    has_wiki_link = models.BooleanField(default=False, db_index=True)
    has_good_wiki_link = models.BooleanField(default=False, db_index=True)
    num_wiki_links = models.IntegerField(default=0)

    # poor naming choices... the following refer to ORES score...
    day_of_avg_score = models.IntegerField(blank=True, null=True)
    week_after_avg_score = models.IntegerField(blank=True, null=True)

    all_revisions_pulled = models.BooleanField(default=False)
    wiki_content_error = models.IntegerField(default=False)

    # this field is nullable because it will be set in the overloaded save method
    day_of_week = models.IntegerField(blank=True, null=True)
    day_of_month = models.IntegerField(blank=True, null=True)
    hour = models.IntegerField(blank=True, null=True)

    # this field is nullable because it will be set when retrieving reddit author info
    user_created_utc = models.DateTimeField(null=True, blank=True)
    # this field is nullable because it will be set upon save method call
    seconds_since_user_creation = models.IntegerField(null=True, blank=True)

    num_edits = models.IntegerField(default=0)
    num_new_editors = models.IntegerField(default=0)
    num_new_editors_retained = models.IntegerField(default=0)
    num_new_edits = models.IntegerField(default=0)
    num_old_edits = models.IntegerField(default=0)
    num_inactive_edits = models.IntegerField(default=0)
    num_active_edits = models.IntegerField(default=0)
    num_minor_edits = models.IntegerField(default=0)
    num_major_edits = models.IntegerField(default=0)
    
    num_edits_prev_week = models.IntegerField(default=0)
    num_new_editors_prev_week = models.IntegerField(default=0)
    num_new_editors_retained_prev_week = models.IntegerField(default=0)
    num_new_edits_prev_week = models.IntegerField(default=0)
    num_old_edits_prev_week = models.IntegerField(default=0)
    num_inactive_edits_prev_week = models.IntegerField(default=0)
    num_active_edits_prev_week = models.IntegerField(default=0)
    num_minor_edits_prev_week = models.IntegerField(default=0)
    num_major_edits_prev_week = models.IntegerField(default=0)
    num_edits_preceding_post = models.IntegerField(default=0)

    num_wiki_pageviews = models.IntegerField(blank=True, null=True)
    num_wiki_pageviews_prev_week = models.IntegerField(blank=True, null=True)

    sample_num = models.IntegerField(default=0, db_index=True)

    def reset_edit_metrics(self):
        for metric in [
            'num_edits',
            'num_edits_prev_week',

            'num_new_editors', 'num_new_editors_retained',
            'num_new_editors_prev_week', 'num_new_editors_retained_prev_week',
            
            'num_new_edits', 'num_old_edits', 
            'num_new_edits_prev_week', 'num_old_edits_prev_week', 

            'num_inactive_edits', 'num_active_edits', 'num_minor_edits', 
            'num_inactive_edits_prev_week', 'num_active_edits_prev_week', 'num_minor_edits_prev_week',
            'num_major_edits',
            'num_major_edits_prev_week', 'num_edits_preceding_post',
        ]:
            setattr(self, metric, 0)


    def norm_change_edits(self):
        total = float(self.num_edits + self.num_edits_prev_week)
        return (
            self.num_edits - self.num_edits_prev_week) / total if total else None

    def percent_of_revs_preceding_post(self):
        denom = (self.num_edits + self.num_edits_prev_week)
        return self.num_edits_preceding_post / denom * 100.0 if denom else None

    def percent_new_editors(self):
        if self.num_edits:
            return self.num_new_edits / self.num_edits * 100.0
        else:
            return None
    def percent_active_editors(self):
        if self.num_edits:
            return self.num_active_edits / self.num_edits * 100.0
        else:
            return None
    def percent_inactive_editors(self):
        if self.num_edits:
            return self.num_inactive_edits / self.num_edits * 100.0
        else:
            return None

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """overload save method"""
        if self.day_of_week is None:
            self.day_of_week = self.timestamp.weekday()
        if self.day_of_month is None:
            self.day_of_month = self.timestamp.day
        if self.hour is None:
            self.hour = self.timestamp.hour
        if self.body_length == 0:
            self.body_length = len(self.body)
        if self.body_num_links == 0:
            self.body_num_links = len(extract_urls(self.body))
        if self.user_created_utc:
            delta = self.timestamp - self.user_created_utc
            self.seconds_since_user_creation = delta.total_seconds()
        else:
            self.seconds_since_user_creation = 0
        if self.body_length != 0:
            if self.body_lexicon_count == 0:
                self.body_lexicon_count = textstat.lexicon_count(self.body)
            if self.body_sentence_count == 0:
                self.body_sentence_count = textstat.sentence_count(self.body)
            if self.body_percent_uppercase == 0:
                num_uppers = sum(1 for c in self.body if c.isupper())
                self.body_percent_uppercase = round(
                    num_uppers / self.body_length * 100)
            if self.body_percent_spaces == 0:
                num_spaces = sum(1 for c in self.body if c == ' ')
                self.body_percent_spaces = round(
                    num_spaces / self.body_length * 100)
            if self.body_percent_punctuation == 0:
                num_punctuation = sum(1 for c in self.body if c in ['.', ','])
                self.body_percent_punctuation = round(
                    num_punctuation / self.body_length * 100)
            if self.body_starts_capitalized is False:
                if self.body[0] == '<':
                    first_char_index = self.body.find('>') + 1
                    self.body_starts_capitalized = self.body[first_char_index].isupper(
                    )
                else:
                    self.body_starts_capitalized = self.body[0].isupper()
            if self.body_lexicon_count != 0:
                try:
                    self.body_coleman_liau_index = round(trimmed(
                        textstat.coleman_liau_index(self.body), 0, 16
                    ))
                except TypeError:
                    self.body_coleman_liau_index = 0
        # calculate average scores if needed
        if self.title_length == 0:
            self.title_length = len(self.title)
        if self.title_length != 0:
            if self.title_lexicon_count == 0:
                self.title_lexicon_count = textstat.lexicon_count(self.body)
            if self.title_sentence_count == 0:
                self.title_sentence_count = textstat.sentence_count(self.body)
            if self.title_percent_uppercase == 0:
                num_uppers = sum(1 for c in self.title if c.isupper())
                self.title_percent_uppercase = round(
                    num_uppers / self.title_length * 100)
            if self.title_percent_spaces == 0:
                num_spaces = sum(1 for c in self.title if c == ' ')
                self.title_percent_spaces = round(
                    num_spaces / self.title_length * 100)
            if self.title_percent_punctuation == 0:
                num_punctuation = sum(1 for c in self.title if c in ['.', ','])
                self.title_percent_punctuation = round(
                    num_punctuation / self.title_length * 100)
            if self.title_starts_capitalized is False:
                self.title_starts_capitalized = self.title[0].isupper()
            if self.title_lexicon_count != 0:
                try:
                    self.title_coleman_liau_index = round(trimmed(
                        textstat.coleman_liau_index(self.title), 0, 16
                    ))
                except TypeError:
                    self.title_coleman_liau_index = 0

        if self.has_wiki_link and self.wiki_content_error == 0:
            self.reset_edit_metrics()
            field_to_dt = {
                'day_of': self.timestamp,
                'week_after': self.timestamp + datetime.timedelta(days=7),
            }
            num_links = 0
            field_to_score = {field: 0 for field in field_to_dt}
            missing_necessary_ores = False
            for link_obj in self.wiki_links.all():
                num_links += 1
                revisions = Revision.objects.filter(wiki_link=link_obj)
                if revisions.exists():
                    for field, dt in field_to_dt.items():
                        ores_score = get_closest_to(
                            revisions, dt).score
                        if ores_score == -1:
                            missing_necessary_ores = True
                        else:
                            field_to_score[field] += ores_score
                    for revision in revisions:
                        users_seen = {}
                        starttime = self.timestamp - datetime.timedelta(days=7)
                        if revision.timestamp > self.timestamp:
                            self.num_edits += 1
                            if revision.registration and revision.registration > self.timestamp:
                                self.num_new_edits += 1
                                if users_seen.get(revision.user) is None:
                                    self.num_new_editors += 1
                                    users_seen[revision.user] = True
                                    if revision.user_retained:
                                        self.num_new_editors_retained += 1
                            else:
                                self.num_old_edits += 1
                            if revision.editcount <= 5:
                                self.num_inactive_edits += 1
                            else:
                                self.num_active_edits += 1
                            if revision.flags:
                                self.num_minor_edits += 1
                            else:
                                self.num_major_edits += 1
                        elif revision.timestamp > starttime:
                            self.num_edits_prev_week += 1
                            if revision.registration and revision.registration > starttime:
                                self.num_new_edits_prev_week += 1
                                if users_seen.get(revision.user) is None:
                                    self.num_new_editors_prev_week += 1
                                    users_seen[revision.user] = True
                                    if revision.user_retained:
                                        self.num_new_editors_retained_prev_week += 1
                            else:
                                self.num_old_edits_prev_week += 1

                            if self.timestamp - revision.timestamp < datetime.timedelta(hours=3):
                                self.num_edits_preceding_post += 1
                            if revision.editcount <= 5:
                                self.num_inactive_edits_prev_week += 1
                            else:
                                self.num_active_edits_prev_week += 1
                            if revision.flags:
                                self.num_minor_edits_prev_week += 1
                            else:
                                self.num_major_edits_prev_week += 1
            if num_links:
                output_field_to_val = {
                    field + '_avg_score': val / num_links for field, val in field_to_score.items()}
                for output_field, val in output_field_to_val.items():
                    if missing_necessary_ores:
                        setattr(self, output_field, None)
                    else:
                        setattr(self, output_field, val)
                if self.day_of_avg_score and self.day_of_avg_score >= 4:
                    self.has_good_wiki_link = True
        super(Post, self).save(*args, **kwargs)



class SampledRedditThread(Post):
    """
    A sampled reddit THREAD using SQL Rand() function
    Columns are used as regression features - no NULLs allowed
    """
    user_info_processed = models.BooleanField(default=False)
    user_comment_karma = models.IntegerField(default=0)
    user_link_karma = models.IntegerField(default=0)
    user_is_mod = models.BooleanField(default=False)
    user_is_suspended = models.BooleanField(default=False)
    user_is_deleted = models.BooleanField(default=False)
    url = models.CharField(max_length=2083)


class SampledStackOverflowPost(Post):
    """
    Each row corresponds to one Stack Overflow post (question or answer)
    """
    user_reputation = models.IntegerField(default=0)
    question_asked_utc = models.DateTimeField(null=True, blank=True)
    num_pageviews = models.IntegerField(default=0)
    tags_string = models.CharField(max_length=115, blank=True, null=True)
    num_tags = models.IntegerField(default=0)
    num_other_answers = models.IntegerField(default=0)
    question_score = models.IntegerField(default=0)
    num_question_comments = models.IntegerField(default=0)
    response_time = models.IntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """overload save method"""
        if self.question_asked_utc:
            delta = self.timestamp - self.question_asked_utc
            self.response_time = delta.seconds
        if not self.tags_string:
            self.num_tags = 0
        elif self.num_tags == 0:
            self.num_tags = len(self.tags_string.split('|'))
        super(SampledStackOverflowPost, self).save(*args, **kwargs)


WIKI_PATTERN = 'wikipedia.org/wiki/'


class WikiLink(models.Model):
    """
    Each row corresponds to a Wikipedia article link that appeared on
    reddit or Stack Overflow

    A WikiLink object is JUST a url that links to a Wikipedia article.
    Infinitely mainly Revision may be associated with one WikiLink via
    ForeignKeys (on the Revision table)
    """
    url = models.CharField(max_length=300)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    title = models.CharField(max_length=300, blank=True, null=True)
    err_code = models.IntegerField(default=0)

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


class Revision(models.Model):
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
    lastrev_date = models.DateTimeField(blank=True, null=True)
    user_retained = models.BooleanField(blank=True, null=True)
    score = models.IntegerField(blank=True, null=True)
    user = models.CharField(max_length=100)
<<<<<<< Updated upstream
    editcount = models.IntegerField(default=0)
=======
    editcount = models.IntegerField(blank=True, null=True)
>>>>>>> Stashed changes
    registration = models.DateTimeField(blank=True, null=True)
    # whether the edit was minor edit
    flags = models.BooleanField(default=True)
    err_code = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        """overload save method"""
        if self.lastrev_date and self.timestamp:
            if self.lastrev_date - self.timestamp > datetime.timedelta(days=30):
                self.user_retained = True
        super(Revision, self).save(*args, **kwargs)

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
    accepted_answer_id = models.IntegerField(blank=True, null=True, db_index=True)
    answer_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    community_owned_date = models.DateTimeField(blank=True, null=True)
    creation_date = models.DateTimeField()
    favorite_count = models.IntegerField(default=0)
    last_activity_date = models.DateTimeField()
    last_edit_date = models.DateTimeField(blank=True, null=True)
    last_editor_display_name = models.CharField(
        max_length=30, blank=True, null=True)
    last_editor_user_id = models.IntegerField(blank=True, null=True)
    owner_display_name = models.CharField(max_length=30)
    owner_user_id = models.IntegerField(db_index=True)
    post_type_id = models.IntegerField()
    score = models.IntegerField(default=0)
    tags = models.CharField(max_length=115)
    view_count = models.IntegerField(default=0)


class StackOverflowAnswer(models.Model):
    """
    Each row corresponds to a StackOverflow answers.
    Matches BigQuery almost exactly.
    """
    id = models.IntegerField(primary_key=True)
    body = models.CharField(max_length=58431)
    comment_count = models.IntegerField(default=0)
    community_owned_date = models.DateTimeField(blank=True, null=True)
    creation_date = models.DateTimeField()
    last_activity_date = models.DateTimeField()
    last_edit_date = models.DateTimeField(blank=True, null=True)
    last_editor_display_name = models.CharField(
        max_length=30, blank=True, null=True)
    last_editor_user_id = models.IntegerField(blank=True, null=True)
    owner_display_name = models.CharField(max_length=30)
    owner_user_id = models.IntegerField(blank=True, null=True, db_index=True)
    parent_id = models.IntegerField(db_index=True)
    post_type_id = models.IntegerField()
    score = models.IntegerField(default=0)
    tags = models.CharField(max_length=115)


class StackOverflowUser(models.Model):
    """
    Each row corresponds to a SO user from BigQuery table
    """
    id = models.IntegerField(primary_key=True)
    display_name = models.CharField(max_length=36)
    about_me = models.CharField(max_length=5999, blank=True, null=True)
    age = models.CharField(max_length=4, blank=True, null=True)
    creation_date = models.DateTimeField()
    last_access_date = models.DateTimeField()
    location = models.CharField(max_length=100, blank=True, null=True)
    reputation = models.IntegerField(default=0)
    up_votes = models.IntegerField(default=0)
    down_votes = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    profile_image_url = models.CharField(max_length=105, blank=True, null=True)
    website_url = models.CharField(max_length=200, blank=True, null=True)


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
    created_utc = models.IntegerField()
    subreddit = models.CharField(max_length=24, blank=True, null=True)
    subreddit_id = models.CharField(max_length=8, blank=True, null=True)
    author = models.CharField(max_length=20)
    domain = models.CharField(max_length=275)
    url = models.CharField(max_length=31215)
    num_comments = models.IntegerField()
    score = models.IntegerField()
    title = models.CharField(max_length=1182)
    selftext = models.CharField(max_length=74185)
    saved = models.BooleanField()
    id = models.CharField(primary_key=True, max_length=10)
    gilded = models.IntegerField()
    stickied = models.BooleanField()
    retrieved_on = models.IntegerField()
    over_18 = models.BooleanField()
    thumbnail = models.CharField(max_length=80, blank=True, null=True)
    hide_score = models.BooleanField()
    link_flair_css_class = models.CharField(
        max_length=102, blank=True, null=True)
    author_flair_css_class = models.CharField(
        max_length=95, blank=True, null=True)
    archived = models.BooleanField()
    is_self = models.BooleanField()
    permalink = models.CharField(max_length=131)
    name = models.CharField(max_length=9)
    author_flair_text = models.CharField(max_length=256, blank=True, null=True)
    quarantine = models.BooleanField()
    link_flair_text = models.CharField(max_length=128, blank=True, null=True)
    distinguished = models.CharField(max_length=9, blank=True, null=True)
