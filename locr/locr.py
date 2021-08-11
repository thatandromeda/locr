import os
from urllib.parse import urlparse, urlunparse

import requests

from .constants import TIMEOUT
from .handlers import (IiifSearchResultToText, StorageSearchResultToText,
                       LcwebSearchResultToText, ResourceLinkToText)

# TODO do I want to fetch blogs? I've filtered them out of slurp, but a
# general-purpose thing might need to catch it.
# TODO inheritance uncomfortably deep
# TODO deal with responses like {url: {'full_text': 'blah'}}
# TODO audio still not working; see e.g. http://www.loc.gov/item/afc1941016_afs05499a/

class UnknownIdentifier(Exception):
    pass


class UnknownHandler(Exception):
    pass


class ObjectNotOnline(Exception):
    pass


class Fetcher(object):
    """
    Fetch full text for Library of Congress items. Return None if full text is
    not found.

    Fetcher.full_text_from_url:
        Given the URL of an item, find its full text.

    Fetcher(result).full_text():
        Given the JSON representation of a single item, find its full text.

    OCRed text is stored on different servers with different URL formats, and
    the full text URL is not usually part of the search result, so there is no
    one single pattern for finding the OCR URL. Fetcher is actually responsible
    for identifying which of several handlers is most likely to succeed for this
    item, and delegating to its full_text() method.

    There are no guarantees about OCR quality; some texts may be unsuitable for
    some purposes. The caller is responsible for assessing quality.

    While Fetcher makes a good-faith attempt to respect rate limiting,
    intermittent server failures mean that text will not always be fetched even
    if it exists.
    """
    @classmethod
    def full_text_from_url(cls, url):
        """Given a URL of an item at LOC, fetches the fulltext of that item."""
        parsed_url = urlparse(url)
        base_url = urlunparse(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', 'fo=json', '')
        )
        result = requests.get(base_url).json()['item']
        return Fetcher(result).full_text()

    def __init__(self, result):
        self.result = result
        self.handlers = [
            ResourceLinkToText,  # this is easiest and should be first
            IiifSearchResultToText,
            StorageSearchResultToText,
            LcwebSearchResultToText
        ]
        self.handler_used = None


    def full_text(self):
        """
        Initialize a handler that knows how to fetch fulltext for images hosted
        on the given server, and delegate to its full_text method.

        Returns None if text not found.
        """

        try:
            format = self.result['online_format']
        except KeyError:
            raise ObjectNotOnline(f'{self.result["id"]} does not have an online_format key')

        text = None

        for handler in self.handlers:
            if handler.valid_for(self.result):
                text = handler(self.result).full_text()

            if text:
                self.handler_used = handler  # For help with debugging
                break

        return text
