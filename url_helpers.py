"""
Helper functions related to the usage of URL
"""
import re


def extract_urls(text, base_url=None):
    """
    Extract all urls matching base_url from `text`
    Returns a list of strings
    """
    if base_url is not None:
        return [x for x in re.findall('<a href="?\'?([^"\'>]*)', text) if base_url in x]
    else:
        return [x for x in re.findall('<a href="?\'?([^"\'>]*)', text)]


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

    
    print(extract_urls(test_so, w))