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
from requests.exceptions import ChunkedEncodingError

import models
import scraper_handler


class ReportGenerator:
    def __init__(self, database_manager):
        self.database_manager = database_manager

    def count_posts_by_category_or_tag(self, model, keyword_used, method, parsed_items):
        counts = defaultdict(int)
        # print("Method:", method)  # Debug print to check the method

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
                counts = defaultdict(int)
                for parsed_item in parsed_items:
                    if model == models.Category:
                        for category in parsed_item['categories']:
                            # print(category)
                            counts[category.name] += 1
                    elif model == models.Tag:
                        for tag in parsed_item['tags']:
                            # print(tag)
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
        # print("Method:", method)  # Debug print to check the method

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

    def draw_chart(self, report, keyword=None, save_path=None):
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
        if bool(save_path):
            chart_path = os.path.join(save_path, f"report_{keyword}_chart.png")
            plt.savefig(chart_path)
            print(f"Chart saved as {chart_path}")

        # Show the chart if save_path is not provided (bool(save_path) will be False)
        if not bool(save_path):
            plt.show()
        else:
            plt.close()  # Close the plot if save_path is provided

    def download_images_and_save_models(self, parsed_items, save_path, file_format='xls'):

        print("Downloading images and saving models...")

        # Create a directory to save the downloaded images
        html_dir = os.path.join(save_path, 'html')
        image_dir = os.path.join(save_path, 'images')
        json_dir = os.path.join(save_path, 'json')
        csv_dir = os.path.join(save_path, 'csv')
        exel_dir = os.path.join(save_path, 'exel')
        os.makedirs(image_dir, exist_ok=True)
        os.makedirs(html_dir, exist_ok=True)

        # Download images from the featured_media_link field and HTML content from the link field
        for item in parsed_items:
            image_url = item.get('featured_media_link')
            if image_url:
                image_name = os.path.basename(image_url)
                image_path = os.path.join(image_dir, image_name)
                try:
                    response = requests.get(image_url)
                    response.raise_for_status()  # Raise an error for HTTP errors
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                except ChunkedEncodingError as e:
                    print(f"ChunkedEncodingError occurred for {image_url}: {e}")
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading {image_url}: {e}")

            link_url = item.get('link')
            if link_url:
                html_name = f"{self.sanitize_filename(item['title'])}.html"
                html_path = os.path.join(html_dir, html_name)
                try:
                    response = requests.get(link_url)
                    response.raise_for_status()  # Raise an error for HTTP errors
                    with open(html_path, 'wb') as f:
                        f.write(response.content)
                except ChunkedEncodingError as e:
                    print(f"ChunkedEncodingError occurred for {link_url}: {e}")
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading {link_url}: {e}")
        print("Images downloaded and HTML content saved.")

        # Convert datetime objects to strings
        for item in parsed_items:
            item['created_date'] = item['created_date'].strftime('%Y-%m-%d %H:%M:%S')
            item['modified_date'] = item['modified_date'].strftime('%Y-%m-%d %H:%M:%S')

        # print("Datetime objects converted to strings.")

        # Save models in the specified format
        for item in parsed_items:

            # Save data in the specified format
            if file_format == "csv":
                os.makedirs(csv_dir, exist_ok=True)
                slug = self.save_as_csv(item, csv_dir)
                print(f"CSV file saved: {os.path.join(csv_dir, slug)}.csv")

            elif file_format == "xls":
                os.makedirs(exel_dir, exist_ok=True)
                slug = self.save_as_xls(item, exel_dir)
                print(f"XLS file saved: {os.path.join(exel_dir, slug)}.xls")

            elif file_format == 'json':
                os.makedirs(json_dir, exist_ok=True)
                slug = self.save_as_json(item, json_dir)
                print(f"JSON file saved: {os.path.join(json_dir, slug)}.json")

        print("All data saved successfully.")

    def save_as_csv(self, item, save_path):
        # Create a folder for each post
        post = item['post']
        slug = post.slug
        post_dir = os.path.join(save_path, post.slug)
        os.makedirs(post_dir, exist_ok=True)

        # Save post data to a CSV file
        post_data = {
            'post_id': post.post_id,
            'title': post.title,
            'created_date': item['created_date'],
            'modified_date': item['modified_date'],
            'slug': post.slug,
            'status': post.status,
            'post_type': post.post_type,
            'link': post.link,
            'content': post.content,
            'excerpt': post.excerpt
        }
        self.save_csv_file(post_data, post_dir, 'post.csv')

        # Save author data to a CSV file
        author_data = {
            'author_id': item['author'].author_id,
            'name': item['author'].name,
            'description': item['author'].description,
            'link': item['author'].link,
            'position': item['author'].position
        }
        self.save_csv_file(author_data, post_dir, 'author.csv')

        # Save categories data to a CSV file
        categories_data = [{'name': category.name,
                            'description': category.description,
                            'link': category.link,
                            'slug': category.slug} for category in item['categories']]
        self.save_csv_file_list(categories_data, post_dir, 'categories.csv')

        # Save tags data to a CSV file
        tags_data = [{'name': tag.name,
                      'description': tag.description,
                      'link': tag.link,
                      'slug': tag.slug} for tag in item['tags']]
        self.save_csv_file_list(tags_data, post_dir, 'tags.csv')

        return slug

    def save_csv_file(self, data, save_path, filename):
        csv_file_path = os.path.join(save_path, filename)
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)

    def save_csv_file_list(self, data_list, save_path, filename):
        if not data_list:
            print(f"No data to save in {filename}")
            return

        csv_file_path = os.path.join(save_path, filename)
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=data_list[0].keys())
            writer.writeheader()
            writer.writerows(data_list)

    def save_as_xls(self, item, save_path):
        # Create a folder for each post
        post = item['post']
        slug = post.slug
        post_dir = os.path.join(save_path, post.slug)
        os.makedirs(post_dir, exist_ok=True)

        # Save post data
        post_data = {
            'post_id': post.post_id,
            'title': post.title,
            'created_date': item['created_date'],
            'modified_date': item['modified_date'],
            'slug': post.slug,
            'status': post.status,
            'post_type': post.post_type,
            'link': post.link,
            'content': post.content,
            'excerpt': post.excerpt
        }
        self.save_excel_file(post_data, post_dir, 'post.xls')

        # Save author data
        author_data = {
            'author_id': item['author'].author_id,
            'name': item['author'].name,
            'description': item['author'].description,
            'link': item['author'].link,
            'position': item['author'].position
        }
        self.save_excel_file(author_data, post_dir, 'author.xls')

        # Save categories data
        categories_data = [{'name': category.name,
                            'description': category.description,
                            'link': category.link,
                            'slug': category.slug} for category in item['categories']]
        self.save_excel_file_list(categories_data, post_dir, 'categories.xls')

        # Save tags data
        tags_data = [{'name': tag.name,
                      'description': tag.description,
                      'link': tag.link,
                      'slug': tag.slug} for tag in item['tags']]
        self.save_excel_file_list(tags_data, post_dir, 'tags.xls')

        return slug

    def save_excel_file(self, data, save_path, filename):
        xls_file_path = os.path.join(save_path, filename)
        wb = Workbook()
        ws = wb.active
        for key, value in data.items():
            ws.append([key, value])
        wb.save(xls_file_path)
        print(f"{filename} saved: {xls_file_path}")

    def save_excel_file_list(self, data_list, save_path, filename):
        xls_file_path = os.path.join(save_path, filename)
        wb = Workbook()
        ws = wb.active
        for data in data_list:
            for key, value in data.items():
                ws.append([key, value])
        wb.save(xls_file_path)
        print(f"{filename} saved: {xls_file_path}")

    def save_as_json(self, item, save_path):

        post = item['post']
        author = item['author']
        categories = [{
            'category_id': category.category_id,
            'count': category.count,
            'name': category.name,
            'description': category.description,
            'link': category.link,
            'slug': category.slug
        } for category in item['categories']]

        tags = [{
            'tag_id': tag.tag_id,
            'count': tag.count,
            'name': tag.name,
            'description': tag.description,
            'link': tag.link,
            'slug': tag.slug
        } for tag in item['tags']]

        # Create a dictionary for the post data
        post_data = {
            'post_id': post.post_id,
            'title': post.title,
            'created_date': item['created_date'],
            'modified_date': item['modified_date'],
            'slug': post.slug,
            'status': post.status,
            'post_type': post.post_type,
            'link': post.link,
            'content': post.content,
            'excerpt': post.excerpt,
            'author': {
                'author_id': author.author_id,
                'name': author.name,
                'description': author.description,
                'link': author.link,
                'position': author.position
            },
            'categories': categories,
            'tags': tags,
        }

        print(f"Saving data for post: {post.title}")

        json_file_path = os.path.join(save_path, f"{post_data['slug']}.json")
        with open(json_file_path, 'w') as json_file:
            json.dump(post_data, json_file, indent=4)

        return post.slug

    def export_report(self, report_content, data, keyword, parsed_items, file_format):
        # Create a new folder with keyword and current date
        folder_name = f"{keyword}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        folder_path = os.path.join("output", folder_name)
        os.makedirs(folder_path)

        # Write report content to HTML file
        report_file_path = os.path.join(folder_path, "report.txt")
        with open(report_file_path, "w") as report_file:
            report_file.write(report_content)

        # save chart
        self.draw_chart(report=data, keyword=keyword, save_path=folder_path)

        # Copy related images (if any) to the folder
        self.download_images_and_save_models(parsed_items, folder_path, file_format)

        # Zip the folder
        zip_file_path = shutil.make_archive(folder_path, 'zip', folder_path)

        # Print the address of the zipped folder
        print("Report exported to:", zip_file_path)

    def sanitize_filename(self, filename):
        # Remove characters that are not suitable for file names
        return re.sub(r'[\\/:*?"<>|]', '_', filename)
