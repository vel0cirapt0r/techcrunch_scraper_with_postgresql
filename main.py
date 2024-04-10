from constants import (BASE_URL, SEARCH_URL, AUTHOR_URL_WITH_ID, SEARCH_PAGE_COUNT, POST_URL_WITH_SLUG,
                       CATEGORY_URL_WITH_ID, TAG_URL_WITH_ID, ALL_POSTS_URL)
import scraper_handler
import local_settings
from database_manager import DatabaseManager
import models

database_manager = DatabaseManager(
    database_name=local_settings.DATABASE['name'],
    user=local_settings.DATABASE['user'],
    password=local_settings.DATABASE['password'],
    host=local_settings.DATABASE['host'],
    port=local_settings.DATABASE['port'],
)


if __name__ == '__main__':
    database_manager.create_tables(
        models=[
            models.Author,
            models.Category,
            models.Tag,
            models.Post,
            models.PostCategory,
            models.PostTag,
            models.Keyword,
            models.SearchByKeyword,
            models.PostSearchByKeywordItem,
        ]
    )

    scraper_handler = scraper_handler.ScraperHandler(
        database_manager=database_manager,
        baseurl=BASE_URL,
        searchurl=SEARCH_URL,
        posturl=POST_URL_WITH_SLUG,
        authorsurl=AUTHOR_URL_WITH_ID,
        categoryurl=CATEGORY_URL_WITH_ID,
        tagurl=TAG_URL_WITH_ID,
        allpostsurl=ALL_POSTS_URL,
    )

    if scraper_handler.are_all_tables_empty():
        scraper_handler.fetch_all_pages()

    elif not scraper_handler.are_all_tables_empty():

        keyword, _ = models.Keyword.get_or_create(title=input("Enter keyword: "))
        page_count = int(input("Enter page count(default 5): ") or SEARCH_PAGE_COUNT)

        search_by_keyword = models.SearchByKeyword.create(keyword=keyword, page_count=page_count)

        search_result_items = scraper_handler.search_by_keyword(search_by_keyword_instance=search_by_keyword)

        database_manager.close_connection()
