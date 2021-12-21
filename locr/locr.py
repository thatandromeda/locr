import os
import re
from time import sleep
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup
import requests

from .constants import TIMEOUT
from .exceptions import ObjectNotOnline, AmbiguousText, UnknownFormat

# TODO do I want to fetch blogs? I've filtered them out of slurp, but a
# general-purpose thing might need to catch it.
# TODO deal with responses like {url: {'full_text': 'blah'}}
# TODO audio still not working; see e.g. http://www.loc.gov/item/afc1941016_afs05499a/


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

        response = requests.get(url)
        sleep(0.3)  # rate limiting

        soup = BeautifulSoup(response.text, 'html.parser')
        download_options = soup.find_all(attrs={"data-file-download": re.compile('text', re.IGNORECASE)})

        if len(download_options) == 0:
            return None
        elif len(download_options) == 1:
            return cls._parse_download(download_options[0])
        else:
            return cls._multiple_options_handler(download_options)


    @classmethod
    def _parse_xml(cls, xml_response):
        # Sometimes this doesn't handle utf-8 properly (e.g we get â\x80\x94
        # instead of a hyphen). Not clear why -- requests and bs4 know they're
        # looking at utf-8.
        return ' '.join([
            x.get_text().strip() for x in soup.find('body').find_all('p')
        ])

    @classmethod
    def _parse_download(cls, download_option):
        download_url = download_option['value']
        response = requests.get(download_url)

        if download_url.endswith('xml'):
            return cls._parse_xml(response)
        elif download_url.endswith('txt'):
            return response.text
        else:
            raise UnknownFormat


    @classmethod
    def _multiple_options_handler(cls, download_options):
        all_pages = [x for x in download_options if 'all pages' in x.text]
        if len(all_pages) == 0:
            return None
        elif len(all_pages) == 1:
            return cls._parse_download(all_pages[0])
        else:
            raise AmbiguousText


    def __init__(self, result):
        self.result = result


    def full_text(self):
        """
        Find the item URL within the JSON representation of the item, and
        delegate to full_text_from_url.
        """

        try:
            format = self.result['online_format']
        except KeyError:
            raise ObjectNotOnline(f'{self.result["id"]} does not have an online_format key.')

        # This is liberal in what it accepts; people are supposed to have passed
        # in just the item key of the API JSON, but if they passed in the entire
        # JSON response, it will find the url within the item. It will raise an
        # AttributeError if neither option works.
        url = self.result.get('url') or self.result.get('item').get('url')

        return self.full_text_from_url(url)
