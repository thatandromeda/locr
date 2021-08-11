"""
Handlers know where to retrieve, and how to parse, full text for Library of
Congress items.
locr.Fetcher.handlers lists all known handlers. Additional handlers should
be added there.
handlers must implement the following public interface:
class method valid_for(cls, result):
  takes a LoC API result
  returns boolean
instance method full_text(self, response):
  takes an http response
  returns full text (or None)
"""
import re
from time import sleep
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

from constants import TIMEOUT


class XmlParser(object):
    """docstring for XmlParser."""

    def _parse_text(self, response):
        # Even though it's an xml document, we'll get better results if we use the
        # html parser; the xml parser will add "body" and "html" tags above the top
        # level of the xml document, and then get confused about the "body" tags
        # which will exist at different, nested levels of the document.
        soup = BeautifulSoup(response.text, 'html.parser')
        # Any child tags of 'p' will be rendered as None by tag.string, so we remove
        # them with the if condition. There are frequent subtags, like 'pageinfo'
        # (page metadata), which we do not want because they do not contain the
        # actual text.
        text = "\n".join([str(tag.string)
                          for tag in soup.body.find_all('p')
                          if tag.string])

        # Smart quotes, and UnicodeDammit doesn't know how to detwingle them.
        text = text.replace('â\x80\x9c', '"')
        text = text.replace('â\x80\x9d', '"')

        return text


class SearchResultToText(object):
    def __init__(self, result):
        self.result = result
        self.url_characters_no_period = r"-_~!*'();:@&=+$,?%#A-z0-9"
        self.url_characters = self.url_characters_no_period + '.'
        self.url_characters_with_slash = self.url_characters + '/'
        self.not_found = rf'The requested URL {self.url_characters_with_slash}.xml was not found on this server.'


    def _http(self):
        # Get around intermittent 500s or whatever.
        retry = requests.packages.urllib3.util.retry.Retry(
            status=3, status_forcelist=[429, 500, 503]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        http = requests.Session()
        http.mount("https://", adapter)
        http.mount("http://", adapter)

        return http


    def _segment_path(self, image_url):
        raise NotImplementedError


    def _request_url(self, image_path):
        raise NotImplementedError


    def _parse_text(self, response):
        raise NotImplementedError


    def _extract_image_path(self, image_url):
        return self._segment_path(image_url)


    def _is_valid(self, response):
        return all([
            bool(response.text),
            not isinstance(response.text, list),
            not '"error":"[Errno 2] No such file or directory:' in response.text,
            not re.compile(self.not_found).match(response.text),
            response.status_code == 200
        ])


    def _get_text(self, image_path):
        sleep(0.3)  # avoid rate-limiting
        return self._http().get(self._request_url(image_path), timeout=TIMEOUT)


    def full_text(self):
        text = None
        for image_url in self.result['image_url']:
            print(f'trying {image_url}')
            image_path = self._extract_image_path(image_url)
            response = self._get_text(image_path)
            import pdb; pdb.set_trace()
            if self._is_valid(response):
                text = self._parse_text(response)
                break

        return text


class ResourceLinkToText(XmlParser, SearchResultToText):
    """docstring for ResourceLinkToText."""
    @classmethod
    def valid_for(cls, result):
        return result.get('resources') and any([
            x.get('fulltext_file') for x in result['resources']
        ])


    def __init__(self, result):
        super(ResourceLinkToText, self).__init__(result)
        self.result = result


    def _request_url(self, image_path):
        return image_path


    def full_text(self):
        text = None
        for resource in self.result['resources']:
            url = resource['fulltext_file']
            response = self._get_text(url)

            if self._is_valid(response):
                text = self._parse_text(response)
                break

        return text


class LcwebSearchResultToText(XmlParser, SearchResultToText):
    """Extract fulltext of items whose images are hosted on lcweb2."""
    endpoint = 'https://lcweb2.loc.gov/'

    @classmethod
    def valid_for(cls, result):
        return any([urlparse(url).netloc == 'lcweb2.loc.gov'in url
                    for url in result['image_url']
        ])


    def _segment_path(self, url):
        path = urlparse(url).path
        base_path = os.path.splitext(path)[0]   # Remove file extension.
        return f'{base_path}.xml'


    def _request_url(self, image_path):
        return f'{self.endpoint}{self._segment_path(image_path)}'


class TileSearchResultToText(SearchResultToText):
    """Includes the features common to fetching fulltext whose images are stored
    on the tile.loc.gov server. Not intended to be used as-is."""

    def __init__(self, result):
        super(TileSearchResultToText, self).__init__(result)
        self.endpoint = 'https://tile.loc.gov/text-services/word-coordinates-service'


    def _segment_path(self, image_url):
        image_path = urlparse(image_url).path
        try:
            return re.compile(self.lc_service_url).match(image_path).group('identifier')
        except AttributeError:
            raise UnknownIdentifier


    def _request_url(self, image_path):
        return f'{self.endpoint}?full_text=1&format=alto_xml&segment=/{self._encoded_segment(image_path)}.xml'


    def _parse_text(self, response):
        # Seems like almost a no-op, but allows for full_text to live in
        # the superclass by hooking into different text parsing methods in
        # subclasses.
        # The and condition means this will return None if the response is
        # empty.
        return response and response.text


class IiifSearchResultToText(TileSearchResultToText):
    """Extract fulltext of items whose images are hosted on tile (the IIIF
    server) under image services."""
    @classmethod
    def valid_for(cls, result):
        return any([
            (urlparse(url).netloc == 'tile.loc.gov' and 'image-services' in url)
            for url in result['image_url']
        ])


    def __init__(self, result):
        super(IiifSearchResultToText, self).__init__(result)
        self.lc_service_prefix = r'image[\-_]services/iiif'
        self.lc_service_url = rf'/{self.lc_service_prefix}/'\
                              rf'(?P<identifier>[{self.url_characters}]+)/' \
                              rf'(?P<region>[{self.url_characters}]+)/' \
                              rf'(?P<size>[{self.url_characters}]+)/' \
                              rf'(?P<rotation>[{self.url_characters}]+)/' \
                              rf'(?P<quality>[{self.url_characters_no_period}]+)' \
                              rf'.(?P<format>[{self.url_characters}]+)'


    def _encoded_segment(self, image_path):
        return image_path.replace(':', '/')


class StorageSearchResultToText(TileSearchResultToText):
    """Extract fulltext of items whose images are hosted on tile (the IIIF
    server) under storage services."""
    @classmethod
    def valid_for(cls, result):
        return any([
            result.get('online_format') == 'audio',
            *[
                (urlparse(url).netloc == 'tile.loc.gov' and
                 'storage-services' in url)
                for url in result['image_url']
            ]
        ])


    def __init__(self, result):
        super(StorageSearchResultToText, self).__init__(result)
        self.lc_service_prefix = r'storage[\-_]services'
        self.lc_service_url = rf'/{self.lc_service_prefix}/'\
                           rf'(?P<identifier>[{self.url_characters_with_slash}]+)/' \
                           rf'.(?P<format>[{self.url_characters_with_slash}]+)'


    def _encoded_segment(self, image_path):
        return f"{image_path.replace(':', '/')}.alto"


    def _alternate_urls(self, image_path):
        final_id = image_path.split('/')[-1]
        return [
            f'https://tile.loc.gov/storage-services/{image_path}.alto.xml',
            f'https://tile.loc.gov/storage-services/{image_path}/{final_id}.xml',
        ]


    def _get_text(self, image_path):
        urls = [self._request_url(image_path)] + self._alternate_urls(image_path)

        for url in urls:
            response = self._http().get(url, timeout=TIMEOUT)
            if response:
                return response
            else:
                sleep(0.3)  # avoid rate-limiting

        return None
