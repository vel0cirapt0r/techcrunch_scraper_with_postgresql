import argparse
import local_settings
from database_manager import DatabaseManager
import models
from scraper_handler import ScraperHandler
from constants import (
    BASE_URL, SEARCH_URL, AUTHOR_URL_WITH_ID, SEARCH_PAGE_COUNT, POST_URL_WITH_SLUG,
    CATEGORY_URL_WITH_ID, TAG_URL_WITH_ID, ALL_POSTS_URL
)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Scraping Tool')
    parser.add_argument('--fetch-all', action='store_true', help='Fetch all pages of posts')
    parser.add_argument('--keyword', type=str, help='Perform keyword search')
    parser.add_argument('--page-count', type=int, default=SEARCH_PAGE_COUNT, help='Number of pages to search for keyword')
    return parser.parse_args()

# Initialize the database manager
database_manager = DatabaseManager(
    database_name=local_settings.DATABASE['name'],
    user=local_settings.DATABASE['user'],
    password=local_settings.DATABASE['password'],
    host=local_settings.DATABASE['host'],
    port=local_settings.DATABASE['port'],
)

if __name__ == "__main__":
    args = parse_arguments()

    # Create database tables if they do not exist
    database_manager.create_tables([
        models.Author,
        models.Category,
        models.Tag,
        models.Post,
        models.PostCategory,
        models.PostTag,
        models.Keyword,
        models.SearchByKeyword,
        models.PostSearchByKeywordItem,
    ])

    # Initialize the ScraperHandler
    scraper_handler = ScraperHandler(
        database_manager=database_manager,
        baseurl=BASE_URL,
        searchurl=SEARCH_URL,
        posturl=POST_URL_WITH_SLUG,
        authorsurl=AUTHOR_URL_WITH_ID,
        categoryurl=CATEGORY_URL_WITH_ID,
        tagurl=TAG_URL_WITH_ID,
        allpostsurl=ALL_POSTS_URL,
    )

    if args.fetch_all:
        # Fetch all pages
        scraper_handler.fetch_all_pages()
    elif args.keyword:
        # Perform keyword search
        keyword_title = args.keyword
        keyword, _ = models.Keyword.get_or_create(title=keyword_title)
        page_count = args.page_count

        search_by_keyword = models.SearchByKeyword.create(keyword=keyword, page_count=page_count)
        scraper_handler.search_by_keyword(search_by_keyword_instance=search_by_keyword)

    # Close database connection
    database_manager.close_connection()
