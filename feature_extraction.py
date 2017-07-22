"""Feature extraction for Wiki/Reddit/SO project"""

# textual metrics
# inspiration comes fromIMPROVING_LOW_QUAL
IMPROVING_LOW_QUAL = 'http://ieeexplore.ieee.org/document/6976134/'
READING_INDEX = 'Senter, R.J.; Smith, E.A. (November 1967). "Automated Readability Index.". Wright-Patterson Air Force Base: iii. AMRL-TR-6620. Retrieved 2012-03-18.'
COLEMAN_LIAO = 'Coleman, Meri; and Liau, T. L. (1975); A computer readability formula designed for machine scoring, Journal of Applied Psychology, Vol. 60, pp. 283–284'

textual_features = [
    {
        'key_name': 'body_len',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Body Length',
    },
    {
        'key_name': 'lowercase_percent',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Body Length',
    },
    {
        'key_name': 'space_count',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Body Length',
    },
    {
        'key_name': 'text_speak_count',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Body Length',
    },
    {
        'key_name': 'capitalization_percent',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Percent of expected capitalization',
    },
    {
        'key_name': 'uppercase_percent',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Percent of alphabetical characters that are capitalized',
    },
    {
        'key_name': 'urls_counts',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Number of urls appearing in the body',
    },
    {
        'key_name': 'loc_count',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Lines of Code count',
    },
]

def calc_ari(num_chars, num_words, num_sentences):
    """Calculate Automated Reading Index"""
    return 4.71 * (num_chars / num_words) + 0.5 * (num_words /num_sentences) - 21.43


def calc_coleman_liau_index(avg_letters_per_hundred_words, avg_sentences_per_hundred_words):
    """Calculate Coleman Liau Index"""
    return 0.0588 * avg_letters_per_hundred_words - 0.29 * avg_sentences_per_hundred_words - 15.8


readability_features = [
    {
        'key_name': 'ari',
        'source': READING_INDEX,
        'pretty_name': 'Automated Reading Index',
        'func': calc_ari,
    },
    {
        'key_name': 'ari',
        'source': READING_INDEX,
        'pretty_name': 'Automated Reading Index',
        'notes': '4.71 * (num_chars / num_words) + 0.5 * (num_words / num_sentences) - 21.43'
    },
    {
        'key_name': 'word_count',
        'source': IMPROVING_LOW_QUAL,
        'pretty_name': 'Word Count',
    },
]


so_social_capital = [
    {
        'key_name': 'key',
        'source': 'source',
        'pretty_name': '',
    },
]

reddit_social_capital = [
    {
        'key_name': 'post_karma',
        'source': 'reddit',
        'pretty_name': 'Karma earned from making posts',
    },
    {
        'key_name': 'comment_karma',
        'source': 'reddit',
        'pretty_name': 'Karma earned from making comments',
    },
    {
        'key_name': 'account_age',
        'source': 'reddit',
        'pretty_name': 'How long the account has been active',
    },
    {
        'key_name': 'trophy_count',
        'source': 'reddit',
        'pretty_name': 'Number of trophies this user has earned',
    },
]


class TextualMetric():
    """A single textual metric. Has an actual data field, a source of inpsiration"""

    def __init__(self, key_name, source, pretty_name):
        self.key_name = key_name
        self.source = source
        self.pretty_name = pretty_name


class TextualMetricsHolder():
    """Holds a set of textual metrics corresponding to one piece of content"""

    def __init__(self, features):
        textual_metrics = []
        for metric in features:
            textual_metrics.append(TextualMetric(**metric))
