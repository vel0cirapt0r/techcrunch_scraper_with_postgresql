BASE_URL = "https://techcrunch.com"

SEARCH_URL = 'https://search.techcrunch.com/search?p={query}&fr=tech&b={page}1'

ALL_POSTS_URL = BASE_URL + '/wp-json/wp/v2/posts?page={page}'

POST_URL_WITH_SLUG = BASE_URL + '/wp-json/wp/v2/posts?slug={slug}'
AUTHOR_URL_WITH_ID = BASE_URL + '/wp-json/tc/v1/users/{id}'
MEDIA_URL_WITH_ID = BASE_URL + '/wp-json/wp/v2/media/{id}'
CATEGORY_URL_WITH_ID = BASE_URL + '/wp-json/wp/v2/categories/{id}'
TAG_URL_WITH_ID = BASE_URL + '/wp-json/wp/v2/tags/{id}'

SEARCH_PAGE_COUNT = 5

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0',
    "Accept-Language": "en-US,en;q=0.9",
    "referer": BASE_URL,
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
}

URL_PATTERN = r'RU=(.*?)(?:/|$)'
