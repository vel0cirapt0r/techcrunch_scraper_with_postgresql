import csv
import json
import os
import shutil
from collections import defaultdict
from datetime import datetime
import re
import matplotlib.pyplot as plt
import requests
from openpyxl import Workbook
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
        return report, category_counts

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
        return report, tag_counts

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
        return report, author_counts

    def draw_chart(self, report, save_path=None):
        # Extract categories and counts from the report
        categories = list(report.keys())
        counts = list(report.values())

        # Create a bar chart
        plt.figure(figsize=(10, 6))
        plt.bar(categories, counts, color='skyblue')

        # Customize the chart
        plt.title('Number of Posts per Category')
        plt.xlabel('Categories')
        plt.ylabel('Number of Posts')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save the chart if save_path is provided
        if save_path:
            plt.savefig(save_path)
            print(f"Chart saved as {save_path}")

        # Show the chart if save_path is not provided (bool(save_path) will be False)
        if not bool(save_path):
            plt.show()
        else:
            plt.close()  # Close the plot if save_path is provided

    def download_images_and_save_models(self, parsed_items, save_path, file_format='xls'):
        # Create a directory to save the downloaded images
        image_dir = os.path.join(save_path, 'images')
        os.makedirs(image_dir, exist_ok=True)

        # Download images from the featured_media_link field
        for item in parsed_items:
            image_url = item.get('featured_media_link')
            if image_url:
                image_name = os.path.basename(image_url)
                image_path = os.path.join(image_dir, image_name)
                with open(image_path, 'wb') as f:
                    response = requests.get(image_url)
                    f.write(response.content)

        # Download HTML content from the link field
        for item in parsed_items:
            link_url = item.get('link')
            if link_url:
                html_name = f"{self.sanitize_filename(item['title'])}.html"
                html_path = os.path.join(save_path, html_name)
                with open(html_path, 'wb') as f:
                    response = requests.get(link_url)
                    f.write(response.content)

        # Save models in the specified format
        if file_format == 'json':
            with open(os.path.join(save_path, f'data.{file_format}'), 'w') as json_file:
                json.dump(parsed_items, json_file, indent=4)
        elif file_format == 'csv':
            with open(os.path.join(save_path, f'data.{file_format}'), 'w', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=parsed_items[0].keys())
                writer.writeheader()
                writer.writerows(parsed_items)
        elif file_format == 'xls':
            wb = Workbook()
            ws = wb.active
            for row, item in enumerate(parsed_items, start=1):
                for col, field_value in enumerate(item.values(), start=1):
                    ws.cell(row=row, column=col, value=field_value)
            wb.save(os.path.join(save_path, f'data.{file_format}'))

    def export_report(self, report_content, keyword, parsed_items, file_format):
        # Create a new folder with keyword and current date
        folder_name = f"{keyword}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        folder_path = os.path.join("output", folder_name)
        os.makedirs(folder_path)

        # Write report content to HTML file
        report_file_path = os.path.join(folder_path, "report.html")
        with open(report_file_path, "w") as report_file:
            report_file.write(report_content)

        # Copy related images (if any) to the folder
        self.download_images_and_save_models(parsed_items, report_file_path, file_format)

        # Zip the folder
        zip_file_path = shutil.make_archive(folder_path, 'zip', folder_path)

        # Print the address of the zipped folder
        print("Report exported to:", zip_file_path)

    def sanitize_filename(self, filename):
        # Remove characters that are not suitable for file names
        return re.sub(r'[\\/:*?"<>|]', '_', filename)