import tldextract


def get_base(url):
    """Return the base of a given url"""
    aliases = {
        'youtu.be': 'youtube.com',
        'i.reddituploads.com': 'reddit.com',
        'i.redd.it': 'reddit.com',
        'np.reddit.com': 'reddit.com',
        'redd.it': 'reddit.com',
        'i.sli.mg': 'imgur.com',
        'i.imgur.com': 'imgur.com',
    }
    double_slash = url.find('//')
    if double_slash == -1:
        double_slash = -2
    single_slash = url.find('/', double_slash + 2)
    if single_slash == -1:
        base = url[double_slash + 2:]
    else:
        base = url[double_slash + 2:single_slash]
    base = base.replace('www.', '')
    base = base.replace('.m.', '.')
    if base[0:2] == 'm.':
        base = base.replace('m.', '')
    if 'wikipedia.org' in base:
        return 'wikipedia.org'
    for alias_domain, actual_domain in aliases.items():
        if base == alias_domain:
            return actual_domain
    return base


for test in [
    'https://i.m.www.github.com/123',
    'https://www.github.com',
    'https://www.github.com/',
    'www.github.com/123',
    'github.com',
    'github.com/123'
]:
    print(tldextract.extract(test))