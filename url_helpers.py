"""
Helper functions related to the usage of URL
"""
import re

def normalize_url(url):
    pass


def extract_urls(base_url, text):
    """
    Extract all urls matching base_url from `text`
    Returns a list of strings
    """
    return [x for x in re.findall('<a href="?\'?([^"\'>]*)', text) if base_url in x]

def test_extract_urls():
    """Test func"""
    w = 'wikipedia.org/wiki/'
    test_so = """
    asd <a href="https://en.wikipedia.org/wiki/Imbolc"> asd <a href="https://en.wikipedia.org/wiki/Imbolc"
    asd asd aasd
    ahref=asdasd
    <a href="https://www.google.com">
    <a href="https://www.wikipedia.org/wiki/">
    """

    
    print(extract_urls(w, test_so))