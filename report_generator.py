from collections import defaultdict

import models  # Assuming this is where your models are defined


class ReportGenerator:
    def __init__(self, database_manager):
        self.database_manager = database_manager

    def count_posts_by_category_or_tag(self, model, keyword_used, method, parsed_items):
        counts = defaultdict(int)
        print("Method:", method)  # Debug print to check the method

        if method == 'all' or method is None:
            for item in model.select():
                if model == models.Category:
                    counts[item.name] = models.PostCategory.select().where(
                        models.PostCategory.category == item
                    ).count()
                elif model == models.Tag:
                    counts[item.name] = models.PostTag.select().where(
                        models.PostTag.tag == item
                    ).count()

        elif method == 'database':
            if model == models.Category:
                for post_category in models.PostCategory.select():
                    counts[post_category.category.name] += 1
            elif model == models.Tag:
                for post_tag in models.PostTag.select():
                    counts[post_tag.tag.name] += 1

        elif method == 'current':
            if bool(keyword_used):
                print()
                counts = defaultdict(int)
                for parsed_item in parsed_items:
                    if model == models.Category:
                        for category in parsed_item['categories']:
                            print(category)
                            counts[category.name] += 1
                    elif model == models.Tag:
                        for tag in parsed_item['tags']:
                            print(tag)
                            counts[tag.name] += 1
        else:
            raise ValueError("Please use --keyword option to generate a report based on the current command.")

        return counts

    def count_post_per_category(self, method='all', keyword_used=None, parsed_items=None):
        """
        Generate a report on the number of saved posts in each category.

        Args:
            method (str): The method used to count the posts.
                'all': Count based on all categories.
                'database': Count based on categories stored in the database.
                'current': Count based on categories in the current command.
            keyword_used (str): The keyword used for filtering posts, or None if not used.
            parsed_items (list): List of parsed items containing post details.

        Returns:
            str: The category report.
        """
        category_counts = self.count_posts_by_category_or_tag(models.Category, keyword_used, method, parsed_items)
        report = "Category Report:\n"
        for category, count in category_counts.items():
            report += f"{category}: {count} posts\n"
        return report

    def count_post_per_tag(self, method='all', keyword_used=None, parsed_items=None):
        """
        Generate a report on the number of saved posts in each tag.

        Args:
            method (str): The method used to count the posts.
                'all': Count based on all tags.
                'database': Count based on tags stored in the database.
                'current': Count based on tags in the current command.
            keyword_used (str): The keyword used for filtering posts, or None if not used.
            parsed_items (list): List of parsed items containing post details.

        Returns:
            str: The tag report.
        """
        tag_counts = self.count_posts_by_category_or_tag(models.Tag, keyword_used, method, parsed_items)
        report = "Tag Report:\n"
        for tag, count in tag_counts.items():
            report += f"{tag}: {count} posts\n"
        return report

    def count_post_per_author(self, method='database', keyword_used=None, parsed_items=None):
        """
        Generate a report on the number of saved posts authored by each author.

        Args:
            method (str): The method used to count the posts.
                'database': Count based on authors stored in the database.
                'current': Count based on authors in the current command.
            keyword_used (str): The keyword used for filtering posts, or None if not used.
            parsed_items (list): List of parsed items containing post details.

        Returns:
            str: The author report.
        """
        if parsed_items is None:
            return "Error: parsed_items is required."

        author_counts = defaultdict(int)
        print("Method:", method)  # Debug print to check the method

        if method == 'database':
            for post in models.Post.select():
                author_counts[post.author.name] += 1

        elif method == 'current':
            if bool(keyword_used):
                author_counts = defaultdict(int)
                for parsed_item in parsed_items:
                    if parsed_item['author'] is not None:
                        author_counts[parsed_item['author'].name] += 1
            else:
                raise ValueError("Please use --keyword option to generate a report based on the current command.")

        report = "Author Report:\n"
        for author, count in author_counts.items():
            report += f"{author}: {count} posts\n"
        return report
