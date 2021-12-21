# README

This fetches full text from Library of Congress OCR files for LOC items. It
returns the text, when found, and `None` otherwise.

## Usage
It can take as input either a result item from a [JSON API response](https://libraryofcongress.github.io/data-exploration/responses.html)
or the URL of an item:

```
from locr import Fetcher

# From item or resource URL
Fetcher.full_text_from_url('https://www.loc.gov/resource/mss85943.001811/')

# From search result
# See https://libraryofcongress.github.io/data-exploration/requests.html
url = 'https://www.loc.gov/search/?fo=json&fa=subject:cats'
response = requests.get(url)
Fetcher(response['results'][0]).full_text()
```

Note that the above example is not guaranteed to work. In particular, not all
objects have online text available.

Fetcher may raise the following exceptions:
- `ObjectNotOnline`: when the object does not have any online formats.
- `AmbiguousText`: when multiple fulltext options are found.

If you encounter these exceptions, kindly file an issue or open a PR about the
newly discovered edge case. Thanks.

## Why LOCR?

The Library of Congress has put OCRed full text online for many of its items.
However:
- the API does not in general return the URLs to these items
- OCRed text exists on different servers, with different URL formats; there is
  not one single way to construct the relevant URL for an item

While full text is easy to retrieve via the web site for a single item, perhaps
you, like me, would like to fetch it programmatically.

## Development

This package has a humiliating lack of tests, and I have done nothing to verify
appropriate versions for dependencies. It really can use your help. PRs welcome.
