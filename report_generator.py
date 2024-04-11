from collections import defaultdict

import models


class ReportGenerator:
    def __init__(self, database_manager):
        self.database_manager = database_manager

    def count_post_per_category(self, method='all', keyword_used=False):
        """
        Generate a report on the number of saved posts in each category.

        Args:
            method (str): The method used to count the posts.
                'all': Count based on all categories.
                'database': Count based on categories stored in the database.
                'current': Count based on categories in the current command.
            keyword_used (bool): Indicates whether the --keyword option was used.

        Returns:
            str: The category report.
        """
        # Initialize a defaultdict to store the count of posts in each category
        category_counts = defaultdict(int)

        if method == 'all':
            # Count based on all categories
            for category in models.Category.select():
                category_counts[category.name] = category.count

        elif method == 'database':
            # Count based on categories stored in the database
            for post_category in models.PostCategory.select():
                category_counts[post_category.category.name] += 1

        elif method == 'current':
            if keyword_used:
                # Count based on categories in the current command
                for post_category in models.PostCategory.raw(
                        'SELECT category_id, COUNT(*) AS count FROM postcategory GROUP BY category_id'
                ):
                    category = models.Category.get_by_id(post_category.category_id)
                    category_counts[category.name] = post_category.count
            else:
                # Handle the case when --keyword option is not used
                print("Error: Please use --keyword option to generate a report based on the current command.")

        # Format the results into a report string
        report = "Category Report:\n"
        for category, count in category_counts.items():
            report += f"{category}: {count} posts\n"

        return report

    def count_post_per_tag(self, method='all', keyword_used=False):
        """
        Generate a report on the number of saved posts associated with each tag.

        Args:
            method (str): The method used to count the posts.
                'all': Count based on all tags.
                'database': Count based on tags stored in the database.
                'current': Count based on tags in the current command.
            keyword_used (bool): Indicates whether the --keyword option was used.

        Returns:
            str: The tag report.
        """
        # Initialize a defaultdict to store the count of posts for each tag
        tag_counts = defaultdict(int)

        if method == 'all':
            # Count based on all tags
            for tag in models.Tag.select():
                tag_counts[tag.name] = tag.count

        elif method == 'database':
            # Count based on tags stored in the database
            for post_tag in models.PostTag.select():
                tag_counts[post_tag.tag.name] += 1

        elif method == 'current':
            if keyword_used:
                # Count based on tags in the current command
                for post_tag in models.PostTag.raw(
                        'SELECT tag_id, COUNT(*) AS count FROM posttag GROUP BY tag_id'
                ):
                    tag = models.Tag.get_by_id(post_tag.tag_id)
                    tag_counts[tag.name] = post_tag.count
            else:
                # Handle the case when --keyword option is not used
                print("Error: Please use --keyword option to generate a report based on the current command.")

        # Format the results into a report string
        report = "Tag Report:\n"
        for tag, count in tag_counts.items():
            report += f"{tag}: {count} posts\n"

        return report

    def count_post_per_author(self, method='database', keyword_used=False):
        """
        Generate a report on the number of saved posts authored by each author.

        Args:
            method (str): The method used to count the posts.
                'database': Count based on authors stored in the database.
                'current': Count based on authors in the current command.
            keyword_used (bool): Indicates whether the --keyword option was used.

        Returns:
            str: The author report.
        """
        # Initialize a defaultdict to store the count of posts for each author
        author_counts = defaultdict(int)

        if method == 'database':
            # Count based on authors stored in the database
            for post in models.Post.select():
                author_counts[post.author.name] += 1

        elif method == 'current':
            if keyword_used:
                # Count based on authors in the current command
                for post in models.Post.raw(
                        'SELECT author_id, COUNT(*) AS count FROM post WHERE keyword_id = (SELECT id FROM keyword WHERE title = %s) GROUP BY author_id',
                        args.keyword
                ):
                    author = models.Author.get_by_id(post.author_id)
                    author_counts[author.name] = post.count
            else:
                # Handle the case when --keyword option is not used
                print("Error: Please use --keyword option to generate a report based on the current command.")

        # Format the results into a report string
        report = "Author Report:\n"
        for author, count in author_counts.items():
            report += f"{author}: {count} posts\n"

        return report

    def generate_report(self):
        # Function to generate a comprehensive report
        pass

    def export_report(self, format='html'):
        # Function to handle the export process
        pass
