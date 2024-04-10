import time
import requests
from bs4 import BeautifulSoup
from peewee import DoesNotExist, OperationalError, IntegrityError

import models


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
                        'primary_category_id': post.primary_category_id,
                        'author': author,
                        'categories': categories,
                        'tags': tags,
                    }

                    print(idx+1, data)

            except Exception as e:
                self.database_manager.db.rollback()  # Rollback transaction if an exception occurs
                print(f"Error occurred: {str(e)}")
            else:
                self.database_manager.db.commit()  # Commit transaction if no exceptions occur

        return search_items

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
        item_url = search_result_item.find('a')['href']
        item_slug = item_url.split('/')[-2]

        search_item, _ = models.PostSearchByKeywordItem.get_or_create(
            search_by_keyword=search_by_keyword,
            title=search_result_item.text,
            url=item_url,
            slug=item_slug
        )

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
                return all_posts
        except OperationalError:
            print("Error occurred while fetching all pages.")
            return []

    def parse_all_posts(self, json_response):
        # Method to parse all posts from JSON response
        all_posts_in_page = []
        authors = []
        all_categories = []
        all_tags = []

        for post_data in json_response:
            post_id = int(post_data['id'])

            # Check if post already exists in the database
            try:
                post = models.Post.get(models.Post.post_id == post_id)
            except DoesNotExist:
                # Post doesn't exist, create a new one
                post = models.Post()

            # Update or create post attributes
            post.created_date = post_data['date']
            post.modified_date = post_data['modified']
            post.slug = post_data['slug']
            post.status = self.clean_view(post_data['status'])
            post.post_type = self.clean_view(post_data['type'])
            post.link = post_data['link']
            post.title = self.clean_view(post_data['title']['rendered'])
            post.content = self.clean_view(post_data['content']['rendered'])
            post.excerpt = self.clean_view(post_data['excerpt']['rendered'])
            post.author_id = int(post_data['author'])
            post.featured_media_link = post_data['jetpack_featured_media_url']
            post.post_format = post_data['format']
            post.primary_category_id = int(post_data['primary_category']['term_id'])

            # Save or update the post
            try:
                post.save()
            except IntegrityError:
                # Handle integrity error silently
                pass

            # Parse author, categories, and tags
            author = self.parse_author(post.author_id)
            categories = self.parse_categories(category_ids=post_data['categories'])
            tags = self.parse_tags(tag_ids=post_data['tags'])

            for category in categories:
                try:
                    models.PostCategory.get_or_create(post=post, category=category)
                except IntegrityError:
                    # Handle the case where the association already exists
                    pass

            # After parsing categories and tags for each post
            # Create associations with the post
            for tag in tags:
                try:
                    models.PostTag.get_or_create(post=post, tag=tag)
                except IntegrityError:
                    # Handle the case where the association already exists
                    pass

            # Append to lists
            all_posts_in_page.append(post)
            authors.append(author)
            all_categories.extend(categories)
            all_tags.extend(tags)

        return all_posts_in_page, authors, all_categories, all_tags

    def parse_post_detail(self, slug):
        # Method to parse post details
        post_response = self.request_to_target_url(self.posturl.format(slug=slug))
        json_response = post_response.json()

        # Check if post already exists in the database
        try:
            post_id = int(json_response[0]['id'])
            post = models.Post.get(models.Post.post_id == post_id)
        except DoesNotExist:
            # Post doesn't exist, create a new one
            post = models.Post()

        # Update or create post attributes
        post.post_id = int(json_response[0]['id'])
        post.created_date = json_response[0]['date']
        post.modified_date = json_response[0]['modified']
        post.slug = json_response[0]['slug']
        post.status = self.clean_view(json_response[0]['status'])
        post.post_type = self.clean_view(json_response[0]['type'])
        post.link = json_response[0]['link']
        post.title = self.clean_view(json_response[0]['title']['rendered'])
        post.content = self.clean_view(json_response[0]['content']['rendered'])
        post.excerpt = self.clean_view(json_response[0]['excerpt']['rendered'])
        post.author_id = int(json_response[0]['author'])
        post.featured_media_link = json_response[0]['jetpack_featured_media_url']
        post.post_format = json_response[0]['format']
        post.primary_category_id = int(json_response[0]['primary_category']['term_id'])

        # Save or update the post
        post.save()

        # Parse author, categories, and tags
        author = self.parse_author(post.author_id)
        categories = self.parse_categories(category_ids=json_response[0]['categories'])
        tags = self.parse_tags(tag_ids=json_response[0]['tags'])

        # After parsing categories and tags for each post
        # Create associations with the post
        for category in categories:
            try:
                models.PostCategory.get_or_create(post=post, category=category)
            except IntegrityError:
                # Handle the case where the association already exists
                pass

        for tag in tags:
            try:
                models.PostTag.get_or_create(post=post, tag=tag)
            except IntegrityError:
                # Handle the case where the association already exists
                pass

        return post, author, categories, tags

    def parse_author(self, author_id):
        # Method to parse author details
        author = None  # Initialize author variable
        try:
            # Attempt to retrieve the author from the database
            author = models.Author.get(models.Author.author_id == author_id)
        except DoesNotExist:
            # If author doesn't exist, fetch author details from URL
            response = self.request_to_target_url(self.authorsurl.format(id=author_id))
            try:
                json_response = response.json()
                # Extract author details from JSON response
                name = self.clean_view(json_response['name'])
                description = self.clean_view(json_response['cbDescription'])
                link = json_response['link']
                position = self.clean_view(json_response['position'])

                # Create or get author instance
                try:
                    author, _ = models.Author.get_or_create(
                        author_id=author_id,
                        name=name,
                        description=description,
                        link=link,
                        position=position
                    )
                except IntegrityError:
                    # Handle the case where the author already exists silently
                    pass
            except Exception as e:
                # Log or handle any exceptions that occur during the process
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
                except IntegrityError:
                    # Handle the case where the item already exists
                    pass
        return items
