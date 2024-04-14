import argparse
import local_settings
from database_manager import DatabaseManager
import models
from scraper_handler import ScraperHandler
from report_generator import ReportGenerator
from constants import (
    BASE_URL, SEARCH_URL, AUTHOR_URL_WITH_ID, SEARCH_PAGE_COUNT, POST_URL_WITH_SLUG,
    CATEGORY_URL_WITH_ID, TAG_URL_WITH_ID, ALL_POSTS_URL
)


def parse_arguments():
    """
    Parse command-line arguments for the Scraping Tool.

    Returns:
        argparse.Namespace: An object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(description='Scraping Tool')
    parser.add_argument('-a', '--fetch-all', action='store_true', help='Fetch all pages of posts')
    parser.add_argument('-k', '--keyword', type=str, help='Perform keyword search')
    parser.add_argument('-p', '--page-count', type=int, default=SEARCH_PAGE_COUNT,
                        help='Number of pages to search for keyword')
    parser.add_argument('-g', '--generate-report', action='store_true', help='Generate report')
    parser.add_argument('-r', '--report-type', choices=['category', 'tag', 'author'],
                        help='Type of report to generate')
    parser.add_argument('-m', '--report-method', choices=['all', 'database', 'current'],
                        help='Method for generating report')
    parser.add_argument('-f', '--file-format', choices=['xls', 'json', 'csv'],
                        help='File format for saving the data')

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

    try:
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

        # Initialize the ReportGenerator
        report_generator = ReportGenerator(database_manager)

        argkeyword = args.keyword
        method = args.report_method
        parsed_items = None
        report_content = ""
        report = ""

        if args.fetch_all:
            print("you can intrupt the progress by pressing control+c the website has over 2 million posts")
            # Fetch all pages
            scraper_handler.fetch_all_pages()

        elif args.keyword:
            # Perform keyword search
            keyword_title = args.keyword
            keyword, _ = models.Keyword.get_or_create(title=keyword_title)
            page_count = args.page_count

            search_by_keyword = models.SearchByKeyword.create(keyword=keyword, page_count=page_count)
            search_items, parsed_items = scraper_handler.search_by_keyword(
                search_by_keyword_instance=search_by_keyword
            )

            if args.generate_report:
                # After performing keyword search, generate reports if requested
                if args.report_type == 'category':
                    report_content, data = report_generator.count_post_per_category(
                        method=args.report_method,
                        keyword_used=args.keyword,
                        parsed_items=parsed_items
                    )
                    report_generator.export_report(report_content, data, keyword, parsed_items, args.file_format)
                elif args.report_type == 'tag':
                    report_content, data = report_generator.count_post_per_tag(
                        method=args.report_method,
                        keyword_used=args.keyword,
                        parsed_items=parsed_items
                    )
                    report_generator.export_report(
                        report_content=report_content,
                        keyword=keyword,
                        parsed_items=parsed_items,
                        file_format=args.file_format
                    )
                elif args.report_type == 'author':
                    report_content, data = report_generator.count_post_per_author(
                        method=args.report_method,
                        keyword_used=args.keyword,
                        parsed_items=parsed_items
                    )
                    report_generator.export_report(
                        report_content=report_content,
                        keyword=keyword,
                        parsed_items=parsed_items,
                        file_format=args.file_format
                    )
                else:
                    print("Error: Please specify a valid report type.")

            elif args.report_type == 'category':
                if args.report_method == 'all' or args.report_method == 'database' or args.report_method is None:
                    report, data = report_generator.count_post_per_category(
                        keyword_used=argkeyword,
                        method=method,
                        parsed_items=parsed_items
                    )
                    print(report)
                    report_generator.draw_chart(data)
                elif args.report_method == 'current':
                    report, data = report_generator.count_post_per_category(
                        keyword_used=argkeyword,
                        method=method,
                        parsed_items=parsed_items
                    )
                    print(report)
                    report_generator.draw_chart(data)
            elif args.report_type == 'tag':
                if args.report_method == 'all' or args.report_method == 'database' or args.report_method is None:
                    report, data = report_generator.count_post_per_tag(
                        keyword_used=keyword.id,  # Pass keyword ID instead of title
                        method=method,
                        parsed_items=parsed_items
                    )
                    print(report)
                    report_generator.draw_chart(data)
                elif args.report_method == 'current':
                    report, data = report_generator.count_post_per_tag(
                        keyword_used=keyword.id,
                        method=method,
                        parsed_items=parsed_items
                    )
                    print(report)
                    report_generator.draw_chart(data)
            elif args.report_type == 'author':
                if args.report_method == 'database':
                    report, data = report_generator.count_post_per_author(
                        keyword_used=argkeyword,
                        method=method,
                        parsed_items=parsed_items
                    )
                    print(report)
                    report_generator.draw_chart(data)
                elif args.report_method == 'current':
                    report, data = report_generator.count_post_per_author(
                        keyword_used=argkeyword,
                        method=method,
                        parsed_items=parsed_items
                    )
                    print(report)
                    report_generator.draw_chart(data)
                elif args.report_method == 'all':
                    print('report countof author in the techcrunch is not implemented')

            else:
                for idx, parsed_item in enumerate(parsed_items):
                    print(f'post {idx}: ', parsed_item)

        elif args.report_type == 'category':
            if args.report_method == 'all' or args.report_method == 'database' or args.report_method is None:
                report, data = report_generator.count_post_per_category(
                    keyword_used=argkeyword,
                    method=method,
                    parsed_items=parsed_items

                )
                print(report)
                report_generator.draw_chart(data)
            elif args.report_method == 'current':
                report, data = report_generator.count_post_per_category(
                    keyword_used=argkeyword,
                    method=method,
                    parsed_items=parsed_items
                )
                print(report)
                report_generator.draw_chart(data)
        elif args.report_type == 'tag':
            if args.report_method == 'all' or args.report_method == 'database' or args.report_method is None:
                report, data = report_generator.count_post_per_tag(
                    keyword_used=keyword.id,  # Pass keyword ID instead of title
                    method=method,
                    parsed_items=parsed_items
                )
                print(report)
                report_generator.draw_chart(data)
            elif args.report_method == 'current':
                report, data = report_generator.count_post_per_tag(
                    keyword_used=keyword.id,  # Pass keyword ID instead of title
                    method=method,
                    parsed_items=parsed_items
                )
                print(report)
                report_generator.draw_chart(data)
        elif args.report_type == 'author':
            if args.report_method == 'database':
                report, data = report_generator.count_post_per_author(
                    keyword_used=argkeyword,
                    method=method,
                    parsed_items=parsed_items
                )
                print(report)
                report_generator.draw_chart(data)
            elif args.report_method == 'current':
                report, data = report_generator.count_post_per_author(
                    keyword_used=argkeyword,
                    method=method,
                    parsed_items=parsed_items
                )
                print(report)
                report_generator.draw_chart(data)
            elif args.report_method == 'all':
                print('report countof author in the techcrunch is not implemented')
        else:
            print("Error: Please specify a valid option.")

    except KeyboardInterrupt:
        print("KeyboardInterrupt: Program terminated.")

    finally:
        # Close database connection
        database_manager.close_connection()
        print('Database connection closed.')
