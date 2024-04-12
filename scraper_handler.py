import time
import datetime
import requests
import warnings
from bs4 import BeautifulSoup
from peewee import DoesNotExist, OperationalError, IntegrityError

import models

# Suppress BeautifulSoup warnings
warnings.filterwarnings(
    "ignore",
    message="The input looks more like a filename than markup. You may want to "
            "open this file and pass the filehandle into Beautiful Soup.",
    category=UserWarning
)


class ScraperHandler:
    def __init__(self, database_manager, baseurl, searchurl, posturl, authorsurl, categoryurl, tagurl, allpostsurl):
        self.database_manager = database_manager
        self.baseurl = baseurl
        self.searchurl = searchurl
        self.posturl = posturl
        self.authorsurl = authorsurl
        self.categoryurl = categoryurl
        self.tagurl = tagurl
        self.allpostsurl = allpostsurl

    def request_to_target_url(self, url, retries=3, backoff_factor=0.5):
        # Method to make HTTP requests with retries
        for attempt in range(retries):
            try:
                response = requests.get(url)
                # print(response.url)
                # print(response.status_code)
                response.raise_for_status()  # Raise HTTPError for bad status codes
                return response
            except (requests.RequestException, IOError) as e:
                if attempt < retries - 1:
                    # Exponential backoff before retrying
                    sleep_duration = backoff_factor * (2 ** attempt)
                    time.sleep(sleep_duration)
                    continue
                else:
                    # Raise the last encountered exception
                    raise e

    def clean_view(self, text):
        # Method to clean HTML text using BeautifulSoup
        soup = BeautifulSoup(text, 'html.parser')
        return " ".join(soup.strings)

    def are_all_tables_empty(self):
        # Method to check if all database tables are empty
        try:
            with self.database_manager.db.atomic():  # Ensure transaction for locking tables
                table_classes = [
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
                for table_class in table_classes:
                    if table_class.select().exists():
                        return False
                return True
        except OperationalError:
            print("Error occurred while locking tables.")
            return True

    def table_has_data(self, table_class):
        # Method to check if a specific table has data
        try:
            return table_class.select().exists()
        except DoesNotExist:
            return False

    def search_by_keyword(self, search_by_keyword_instance):
        # Method to perform search by keyword
        search_items = list()
        parsed_items = list()

        for i in range(search_by_keyword_instance.page_count):
            # Iterate through search result pages
            response = self.request_to_target_url(
                self.searchurl.format(
                    query=search_by_keyword_instance.keyword,
                    page=i
                )
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                search_items.extend(
                    self.extract_search_items(
                        search_by_keyword=search_by_keyword_instance,
                        soup=soup
                    )
                )

        with self.database_manager.db.atomic():  # Transaction begins here
            try:
                for idx, search_item in enumerate(search_items):
                    # Iterate through search items
                    post, author, categories, tags = self.parse_post_detail(slug=search_item.slug)
                    data = {
                        'post_id': post.post_id,
                        'created_date': post.created_date,
                        'modified_date': post.modified_date,
                        'slug': post.slug,
                        'status': post.status,
                        'post_type': post.post_type,
                        'link': post.link,
                        'title': post.title,
                        'content': post.content,
                        'excerpt': post.excerpt,
                        'author_id': post.author_id,
                        'featured_media_link': post.featured_media_link,
                        'post_format': post.post_format,
                        'author': author,
                        'categories': categories,
                        'tags': tags,
                    }

                    parsed_items.append(data)

                    # print(idx + 1, data)

            except Exception as e:
                self.database_manager.db.rollback()  # Rollback transaction if an exception occurs
                print(f"Error occurred: {str(e)}")
            else:
                self.database_manager.db.commit()  # Commit transaction if no exceptions occur

        return search_items, parsed_items

    def extract_search_items(self, search_by_keyword, soup):
        # Method to extract search items from search result page
        search_items = list()

        search_result_items = soup.findAll('h4', attrs={'class': 'pb-10'})

        for search_result_item in search_result_items:

            parsed_item = self.parse_search_item(
                search_by_keyword=search_by_keyword,
                search_result_item=search_result_item
            )
            if parsed_item:
                search_items.append(parsed_item)

        return search_items

    def parse_search_item(self, search_by_keyword, search_result_item):
        # Method to parse individual search item
        item_url = search_result_item.find('a')['href']  # Extract the URL of the search result item
        item_slug = item_url.split('/')[-2]  # Extract the slug from the URL
        post_id = self.parse_post_detail(slug=item_slug)[0].post_id  # Get the post ID from the parsed post detail
        # print(post_id)

        try:
            # Create a new search item
            search_item = models.PostSearchByKeywordItem.create(
                search_by_keyword=search_by_keyword,
                title=search_result_item.text,
                url=item_url,
                slug=item_slug,
                post=post_id,
                created_at=datetime.datetime.now()
            )
        except IntegrityError as e:
            # Handle the case where the item already exists
            print("IntegrityError:", e)

        return search_item

    def fetch_all_pages(self):
        # Method to fetch all pages of posts
        try:
            with self.database_manager.db.atomic():
                all_posts = []
                page = 1
                while True:
                    # for page in range(1, 5):
                    response = self.request_to_target_url(self.allpostsurl.format(page=page))
                    json_response = response.json()

                    all_posts_in_page = self.parse_all_posts(json_response)

                    if 'code' in json_response and json_response['code'] == 'rest_post_invalid_page_number':
                        break
                    all_posts.extend(all_posts_in_page)
                    page += 1
                    time.sleep(10)
                    print('page:', page - 1)
                return all_posts
        except OperationalError:
            print("Error occurred while fetching all pages.")
            return []

    def parse_all_posts(self, json_response):
        all_posts_in_page = []
        authors = []
        all_categories = []
        all_tags = []

        for post_data in json_response:
            post, author, categories, tags = self.parse_post_detail_from_data(post_data)

            all_posts_in_page.append(post)
            authors.append(author)
            all_categories.extend(categories)
            all_tags.extend(tags)

        return all_posts_in_page, authors, all_categories, all_tags

    def parse_post_detail(self, slug):
        post_response = self.request_to_target_url(self.posturl.format(slug=slug))
        json_response = post_response.json()

        return self.parse_post_detail_from_data(json_response[0])

    def parse_post_detail_from_data(self, post_data):
        post_id = int(post_data['id'])

        author = self.parse_author(int(post_data['author']))
        categories = self.parse_categories(category_ids=post_data['categories'])
        tags = self.parse_tags(tag_ids=post_data['tags'])

        try:
            post = models.Post.get(models.Post.post_id == post_id)
        except DoesNotExist:
            try:
                post = models.Post.create(
                    post_id=post_id,
                    created_date=post_data['date'],
                    modified_date=post_data['modified'],
                    slug=post_data['slug'],
                    status=self.clean_view(post_data['status']),
                    post_type=self.clean_view(post_data['type']),
                    link=post_data['link'],
                    title=self.clean_view(post_data['title']['rendered']),
                    content=self.clean_view(post_data['content']['rendered']),
                    excerpt=self.clean_view(post_data['excerpt']['rendered']),
                    author_id=int(post_data['author']),
                    featured_media_link=post_data['jetpack_featured_media_url'],
                    post_format=post_data['format'],
                )
            except IntegrityError as e:
                print("IntegrityError:", e)

        for category in categories:
            try:
                models.PostCategory.get_or_create(post=post, category=category)
            except IntegrityError as e:
                print("IntegrityError:", e)

        for tag in tags:
            try:
                models.PostTag.get_or_create(post=post, tag=tag)
            except IntegrityError as e:
                print("IntegrityError:", e)

        return post, author, categories, tags

    def parse_author(self, author_id):
        author = None

        try:
            # Attempt to retrieve the author from the database
            author = models.Author.get(models.Author.author_id == author_id)
        except DoesNotExist:
            try:
                # Fetch author details from URL
                response = self.request_to_target_url(self.authorsurl.format(id=author_id))
                response.raise_for_status()  # Raise HTTPError for bad status codes
                json_response = response.json()

                if not json_response:
                    # If json_response is empty, create a null author entry in the database
                    author, _ = models.Author.get_or_create(
                        author_id=author_id,
                        name="Not Found",
                        description="Author not found",
                        link="",
                        position=""
                    )
                    print("Null Author created:", author_id)
                else:
                    # Extract author details from JSON response
                    name = self.clean_view(json_response['name'])
                    description = self.clean_view(json_response.get('cbDescription', 'No description available'))
                    link = json_response.get('link', '')
                    position = self.clean_view(json_response.get('position', ''))

                    # Create or get author instance
                    author, _ = models.Author.get_or_create(
                        author_id=author_id,
                        name=name,
                        description=description,
                        link=link,
                        position=position
                    )
            except requests.exceptions.HTTPError as http_err:
                if http_err.response.status_code == 404:
                    # Handle 404 error: Author not found, create a null author entry
                    author, _ = models.Author.get_or_create(
                        author_id=author_id,
                        name="Not Found",
                        description="Author not found",
                        link="",
                        position=""
                    )
                    print("Null Author created:", author_id)
                elif http_err.response.status_code == 401:
                    # Handle 401 error: Unauthorized, create a null author entry
                    author, _ = models.Author.get_or_create(
                        author_id=author_id,
                        name="Not Authorized",
                        description="Access unauthorized",
                        link="",
                        position=""
                    )
                    print("Not Authorized Author created:", author_id)
                else:
                    # Handle other HTTP errors
                    print(f"HTTPError occurred while fetching author details: {http_err}")
            except Exception as e:
                # Log or handle any other exceptions that occur during the process
                print(f"Error occurred while parsing author details: {e}")

        return author

    def parse_data(self, url_format, obj_id):
        # Method to parse generic data
        response = self.request_to_target_url(url_format.format(id=obj_id))
        json_response = response.json()
        count = json_response['count']
        name = self.clean_view(json_response['name'])
        description = self.clean_view(json_response['description'])
        link = json_response['link']
        slug = json_response['slug']

        return count, name, description, link, slug

    def parse_categories(self, category_ids):
        # Method to parse categories
        return self.parse_items(category_ids, models.Category, models.Category.category_id, self.categoryurl)

    def parse_tags(self, tag_ids):
        # Method to parse tags
        return self.parse_items(tag_ids, models.Tag, models.Tag.tag_id, self.tagurl)

    def parse_items(self, ids, model, id_attr, url_format):
        # Method to parse items (categories or tags)
        items = []
        for item_id in ids:
            try:
                item = model.get(id_attr == item_id)
                items.append(item)
            except DoesNotExist:
                count, name, description, link, slug = self.parse_data(url_format, item_id)
                try:
                    item = model.create(
                        **{id_attr.name: int(item_id)},
                        count=count,
                        name=name,
                        description=description,
                        link=link,
                        slug=slug,
                    )
                    items.append(item)
                except IntegrityError as e:
                    # Handle the case where the item already exists
                    print("IntegrityError:", e)
        return items
