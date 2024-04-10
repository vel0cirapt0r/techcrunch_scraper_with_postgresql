import time
import requests
from bs4 import BeautifulSoup
from peewee import DoesNotExist, OperationalError

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

    def request_to_target_url(self, url):
        # print(url)
        response = requests.get(url)
        # print(response.url)
        # print(response.status_code)
        return response

    def clean_view(self, text):
        soup = BeautifulSoup(text, 'html.parser')
        return " ".join(soup.strings)

    def are_all_tables_empty(self):
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
        try:
            return table_class.select().exists()
        except DoesNotExist:
            return False

    def search_by_keyword(self, search_by_keyword_instance):
        search_items = list()

        for i in range(search_by_keyword_instance.page_count):
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

        with self.database_manager.database.atomic():  # Transaction begins here
            try:
                for search_item in search_items:
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

                    print(data)

            except Exception as e:
                self.database_manager.rollback()  # Rollback transaction if an exception occurs
                print(f"Error occurred: {str(e)}")
            else:
                self.database_manager.commit()  # Commit transaction if no exceptions occur

        return search_items

    def extract_search_items(self, search_by_keyword, soup):
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
        # pattern = URL_PATTERN
        # print(search_result_item.find('a')['href'])
        item_url = search_result_item.find('a')['href']
        # match = re.search(pattern, search_result_item.find('a')['href'])
        # print(match)
        # item_url = unquote(match.group(1))
        item_slug = item_url.split('/')[-2]

        search_item, _ = models.PostSearchByKeywordItem.get_or_create(
            search_by_keyword=search_by_keyword,
            title=search_result_item.text,
            url=item_url,
            slug=item_slug
        )

        return search_item

    def fetch_all_pages(self):
        try:
            with self.database_manager.db.atomic():
                all_posts = []
                page = 1
                while True:
                    response = self.request_to_target_url(self.allpostsurl.format(page=page))
                    json_response = response.json()

                    all_posts_in_page = self.parse_all_posts(json_response)

                    if 'code' in json_response and json_response['code'] == 'rest_post_invalid_page_number':
                        break
                    all_posts.extend(all_posts_in_page)
                    page += 1
                    time.sleep(60)
                return all_posts
        except OperationalError:
            print("Error occurred while fetching all pages.")
            return []

    def parse_all_posts(self, json_response):
        all_posts_in_page = list()
        authors = list
        all_categories = list()
        all_tags = list()
        for i in range(len(json_response)):
            post_id = int(json_response[i]['id'])
            created_date = json_response[i]['date']
            modified_date = json_response[i]['modified']
            slug = json_response[i]['slug']
            status = self.clean_view(json_response[i]['status'])
            post_type = self.clean_view(json_response[i]['type'])
            link = json_response[i]['link']
            title = self.clean_view(json_response[i]['title']['rendered'])
            content = self.clean_view(json_response[i]['content']['rendered'])
            excerpt = self.clean_view(json_response[i]['excerpt']['rendered'])
            author_id = int(json_response[i]['author'])
            featured_media_link = json_response[i]['jetpack_featured_media_url']
            post_format = json_response[i]['format']
            primary_category_id = int(json_response[i]['primary_category']['term_id'])

            self.parse_author(author_id)

            category_ids = json_response[i]['categories']
            categories = self.parse_categories(category_ids=category_ids)

            tag_ids = json_response[i]['tags']
            tags = self.parse_tags(tag_ids=tag_ids)

            post, _ = models.Post.get_or_create(
                post_id=post_id,
                created_date=created_date,
                modified_date=modified_date,
                slug=slug,
                status=status,
                post_type=post_type,
                link=link,
                title=title,
                content=content,
                excerpt=excerpt,
                author_id=author_id,
                featured_media_link=featured_media_link,
                post_format=post_format,
                primary_category_id=primary_category_id,
            )

            for category in categories:
                postcategory, _ = models.PostCategory.get_or_create(post=post.post_id, category=category.category_id)

            for tag in tags:
                posttag, _ = models.PostTag.get_or_create(post=post.post_id, tag=tag.tag_id)

            all_posts_in_page.append(post)

        return all_posts_in_page, authors, all_categories, all_tags

    def parse_post_detail(self, slug):
        post_response = self.request_to_target_url(self.posturl.format(slug=slug))
        json_response = post_response.json()
        post_id = int(json_response[0]['id'])
        created_date = json_response[0]['date']
        modified_date = json_response[0]['modified']
        slug = json_response[0]['slug']
        status = self.clean_view(json_response[0]['status'])
        post_type = self.clean_view(json_response[0]['type'])
        link = json_response[0]['link']
        title = self.clean_view(json_response[0]['title']['rendered'])
        content = self.clean_view(json_response[0]['content']['rendered'])
        excerpt = self.clean_view(json_response[0]['excerpt']['rendered'])
        author_id = int(json_response[0]['author'])
        featured_media_link = json_response[0]['jetpack_featured_media_url']
        post_format = json_response[0]['format']
        primary_category_id = int(json_response[0]['primary_category']['term_id'])

        author = self.parse_author(author_id)

        category_ids = json_response[0]['categories']
        categories = self.parse_categories(category_ids=category_ids)

        tag_ids = json_response[0]['tags']
        tags = self.parse_tags(tag_ids=tag_ids)

        post, _ = models.Post.get_or_create(
            post_id=post_id,
            created_date=created_date,
            modified_date=modified_date,
            slug=slug,
            status=status,
            post_type=post_type,
            link=link,
            title=title,
            content=content,
            excerpt=excerpt,
            author_id=author_id,
            featured_media_link=featured_media_link,
            post_format=post_format,
            primary_category_id=primary_category_id,
        )

        for category in categories:
            models.PostCategory.get_or_create(post=post.post_id, category=category)

        for tag in tags:
            models.PostTag.get_or_create(post=post.post_id, tag=tag)

        return post, author, categories, tags

    def parse_author(self, author_id):
        response = self.request_to_target_url(self.authorsurl.format(id=author_id))
        json_response = response.json()
        name = self.clean_view(json_response['name'])
        description = self.clean_view(json_response['cbDescription'])
        link = json_response['link']
        position = self.clean_view(json_response['position'])

        author, _ = models.Author.get_or_create(
            author_id=author_id,
            name=name,
            description=description,
            link=link,
            position=position
        )

        return author

    def parse_data(self, url_format, obj_id):
        response = self.request_to_target_url(url_format.format(id=obj_id))
        json_response = response.json()
        count = json_response['count']
        name = self.clean_view(json_response['name'])
        description = self.clean_view(json_response['description'])
        link = json_response['link']
        slug = json_response['slug']

        return count, name, description, link, slug

    def parse_categories(self, category_ids):
        categories = []
        for category_id in category_ids:
            try:
                category = models.Category.get(models.Category.category_id == category_id)
                categories.append(category)
            except models.Category.DoesNotExist:
                count, name, description, link, slug = self.parse_data(self.categoryurl, category_id)
                category = models.Category.create(
                    category_id=int(category_id),
                    count=count,
                    name=name,
                    description=description,
                    link=link,
                    slug=slug,
                )
                categories.append(category)
        return categories

    def parse_tags(self, tag_ids):
        tags = list()
        for tag_id in tag_ids:
            count, name, description, link, slug = self.parse_data(self.tagurl, tag_id)
            tag, _ = models.Tag.get_or_create(
                tag_id=int(tag_id),
                count=count,
                name=name,
                description=description,
                link=link,
                slug=slug,
            )
            tags.append(tag)
        return tags
