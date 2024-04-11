import peewee

import constants
import main


class BaseModel(peewee.Model):
    class Meta:
        database = main.database_manager.db


class Author(BaseModel):
    author_id = peewee.PrimaryKeyField()
    name = peewee.CharField(max_length=250)
    description = peewee.TextField()
    link = peewee.CharField(max_length=250)
    position = peewee.CharField(max_length=250)

    def __str__(self):
        return self.name


class BaseCategoryTag(BaseModel):
    count = peewee.IntegerField()
    name = peewee.CharField(max_length=250)
    description = peewee.TextField()
    link = peewee.CharField(max_length=250)
    slug = peewee.CharField(max_length=250)


class Category(BaseCategoryTag):
    category_id = peewee.PrimaryKeyField()

    def __str__(self):
        return self.name


class Tag(BaseCategoryTag):
    tag_id = peewee.PrimaryKeyField()

    def __str__(self):
        return self.name


class Post(BaseModel):
    post_id = peewee.PrimaryKeyField()
    created_date = peewee.DateTimeField()
    modified_date = peewee.DateTimeField()
    slug = peewee.CharField(max_length=250)
    status = peewee.CharField(max_length=50)
    post_type = peewee.CharField(max_length=50)
    link = peewee.CharField(max_length=250)
    title = peewee.CharField(max_length=250)
    content = peewee.TextField()
    excerpt = peewee.TextField()
    author = peewee.ForeignKeyField(Author, backref='posts')
    featured_media_link = peewee.CharField(max_length=250)
    post_format = peewee.CharField(max_length=50)

    def __str__(self):
        return self.title


class PostCategory(BaseModel):
    post = peewee.ForeignKeyField(Post, backref='post_categories', on_delete='CASCADE')
    category = peewee.ForeignKeyField(Category, backref='post_categories', on_delete='CASCADE')

    def __str__(self):
        return f'{self.post.title}({self.category.name})'


class PostTag(BaseModel):
    post = peewee.ForeignKeyField(Post, backref='post_tags', on_delete='CASCADE')
    tag = peewee.ForeignKeyField(Tag, backref='post_tags', on_delete='CASCADE')

    def __str__(self):
        return f'{self.post.title}({self.tag.name})'


class Keyword(BaseModel):
    title = peewee.CharField(max_length=250, unique=True)

    def __str__(self):
        return self.title


class SearchByKeyword(BaseModel):
    keyword = peewee.ForeignKeyField(Keyword, backref='searches')
    page_count = peewee.IntegerField(default=constants.SEARCH_PAGE_COUNT)

    def __str__(self):
        return self.keyword.title


class PostSearchByKeywordItem(BaseModel):
    search_by_keyword = peewee.ForeignKeyField(SearchByKeyword, backref='items', on_delete='CASCADE')
    title = peewee.CharField(max_length=250)
    url = peewee.CharField(max_length=250)
    slug = peewee.CharField(max_length=250)
    post = peewee.ForeignKeyField(Post, backref='search_items', null=True, on_delete='CASCADE')
    created_at = peewee.DateTimeField()

    def __str__(self):
        return f'{self.title}({self.search_by_keyword.keyword.title})'
