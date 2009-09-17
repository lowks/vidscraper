import re
import simplejson
import urllib

import feedparser
from lxml import builder

from vidscraper.decorators import (provide_shortmem, returns_unicode,
                                   returns_struct_time)
from vidscraper import errors, util, miroguide_util


EMaker = builder.ElementMaker()
EMBED = EMaker.embed

EMBED_WIDTH = 425
EMBED_HEIGHT = 344


def parse_feed(scraper_func):
    def new_scraper_func(url, shortmem=None, *args, **kwargs):
        if not shortmem.get('feed_item'):
            file_id = BLIP_REGEX.match(url).groupdict()['file_id']
            rss_url = 'http://blip.tv/file/%s?skin=rss' % file_id
            parsed = feedparser.parse(rss_url)
            if 'entries' not in parsed or not parsed.entries:
                shortmem['feed_item'] = None
            else:
                shortmem['feed_item'] = parsed['entries'][0]
        if shortmem['feed_item'] is None:
            return None
        else:
            return scraper_func(url, shortmem=shortmem, *args, **kwargs)

    return new_scraper_func

def _fp_get(shortmem, key):
    """
    Feedparser sometimes strips off the blip_ prefix in its dictionary.  This
    function helps by checking both for us.
    """
    fp = shortmem['feed_item']
    return fp.get('blip_%s' % key,
                  fp.get(key))

@provide_shortmem
@parse_feed
@returns_unicode
def get_thumbnail_url(url, shortmem=None):
    if _fp_get(shortmem, 'thumbnail_src'):
        return 'http://a.images.blip.tv/%s' % (
            _fp_get(shortmem, 'thumbnail_src'),)
    elif _fp_get(shortmem, 'smallthumbnail'):
        return _fp_get(shortmem, 'smallthumbnail')
    else:
        return _fp_get(shortmem, 'picture')


@provide_shortmem
@parse_feed
@returns_unicode
def get_link(url, shortmem=None):
    return shortmem['feed_item'].link

@provide_shortmem
@parse_feed
@returns_unicode
def scrape_title(url, shortmem=None):
    try:
        return shortmem['feed_item']['title']
    except KeyError:
        raise errors.FieldNotFound('Could not find the title field')


@provide_shortmem
@parse_feed
@returns_unicode
def scrape_description(url, shortmem=None):
    try:
        return util.clean_description_html(
            shortmem['feed_item']['summary_detail']['value'])
    except KeyError:
        raise errors.FieldNotFound('Could not find the description field')


@provide_shortmem
@parse_feed
@returns_unicode
def scrape_file_url(url, shortmem=None):
    try:
        video_enclosure = miroguide_util.get_first_video_enclosure(
            shortmem['feed_item'])
        return video_enclosure.get('href')
    except KeyError:
        raise errors.FieldNotFound('Could not find the feed_item field')


@provide_shortmem
@parse_feed
@returns_struct_time
def scrape_publish_date(url, shortmem=None):
    # sure it's not exactly the publish date, but it's close
    try:
        return shortmem['feed_item'].updated_parsed
    except KeyError:
        raise errors.FieldNotFound('Could not find the publish_date field')

@provide_shortmem
def get_embed(url, shortmem=None, width=EMBED_WIDTH, height=EMBED_HEIGHT):
    file_id = BLIP_REGEX.match(url).groupdict()['file_id']
    oembed_get_dict = {
            'url': 'http://blip.tv/file/%s' % file_id,
            'width': EMBED_WIDTH,
            'height': EMBED_HEIGHT}

    oembed_response = urllib.urlopen(
        'http://blip.tv/oembed/?' + urllib.urlencode(oembed_get_dict)).read()

    oembed_response = oembed_response.replace(r"\'", "'")
    # simplejson doesn't like the \' escape

    try:
        embed_code = simplejson.loads(oembed_response.decode('utf8'))['html']
    except (ValueError, KeyError):
        embed_code = None

    return embed_code


@provide_shortmem
@parse_feed
def get_tags(url, shortmem=None):
    return [tag['term'] for tag in shortmem['feed_item'].tags]

@provide_shortmem
@parse_feed
def get_user(url, shortmem=None):
    return _fp_get(shortmem, 'user')

@provide_shortmem
@parse_feed
def get_user_url(url, shortmem=None):
    url = _fp_get(shortmem, 'showpage')
    if url.startswith('http://') or url.startswith('https://'):
        return url
    else:
        return 'http://%s' % (url,)


BLIP_REGEX = re.compile(
    r'^https?://(?P<subsite>[a-zA-Z]+\.)?blip.tv/file/(?P<file_id>\d+)')
SUITE = {
    'regex': BLIP_REGEX,
    'funcs': {
        'link': get_link,
        'title': scrape_title,
        'description': scrape_description,
        'embed': get_embed,
        'file_url': scrape_file_url,
        'thumbnail_url': get_thumbnail_url,
        'tags': get_tags,
        'publish_date': scrape_publish_date,
        'user': get_user,
        'user_url': get_user_url}}
