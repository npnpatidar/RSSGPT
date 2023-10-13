import requests
import feedparser
import json
from bs4 import BeautifulSoup
import os
from datetime import datetime
from collections import defaultdict
import re
import g4f
import zipfile
import sqlite3
import concurrent.futures


# Function to fetch feed data
def fetch_feed_data(feed_url):
  response = requests.get(feed_url)
  if response.status_code == 200:
    return feedparser.parse(response.text).entries
  return []


# Function to validate entry
def validate_entry(entry):
  return hasattr(entry, 'id') and hasattr(entry, 'title') and hasattr(
      entry, 'summary') and hasattr(entry, 'published') and hasattr(
          entry, 'link')


# Function to insert article data
def insert_article_data(feed_title, entry, pool):
  connection = pool.get_connection()
  cursor = connection.cursor()
  if validate_entry(entry):
    table_name = feed_title.replace(' ', '_')
    cursor.execute(
        f'''
            INSERT OR IGNORE INTO {table_name} (feed_unique_id, entry_title, entry_url, entry_summary,entry_article_text, entry_date, entry_written)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (entry.id, entry.title, entry.link, "NO SUMMARY", "",
              entry.published, False))
    cursor.connection.commit()
  pool.release_connection(connection)



# Function to parse OPML file and extract feed URLs
def parse_opml(opml_file):
  feeds = []
  with open(opml_file, 'r') as file:
    soup = BeautifulSoup(file, 'xml')
    outlines = soup.find_all('outline')
    for outline in outlines:
      if 'xmlUrl' in outline.attrs:
        feed_title = outline['title']
        feed_url = outline['xmlUrl']
        feeds.append({'title': feed_title, 'url': feed_url})
  return feeds


# Function to summarise article
def summarise(g4f, article_text):
    max_attempts = 10
    summary = ""
    # Define your conversation with the model
    conversation = [
        {
            "role":
            "system",
            "content":
            "You are a helpful assistant that summarizes articles. Now summarize this article:" + article_text
        },
    ]

    for _ in range(max_attempts):
        try:
            response = g4f.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation,
                max_tokens=1000,
                stream=False,
            )

            for message in response:
                summary += message

            # Split the response into words and check if it has more than 5 words
            words = summary.split()
            if len(words) > 5:
                return summary

        except Exception as e:
            # Log the error (you can use a logging library for this)
            print(f"Error while summarizing article")

    # If after 10 attempts there's no valid response, return an error message or handle as needed
    return "NO SUMMARY"

# Function to retrieve full article text from a URL
def fetch_article_text(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Customize this part based on the specific structure of the webpage
        article_text = ''
        # Example: Extracting text from <p> tags
        paragraphs = soup.find_all('p')
        for paragraph in paragraphs:
            article_text += paragraph.get_text() + '\n'
        return article_text
    except Exception as e:
        print(f"Error fetching content from {url}: {str(e)}")
        return None

def fetch_and_update_article_text(pool, table_name, entry_id, entry_url):
    # Get a connection from the pool
    connection = pool.get_connection()
    cursor = connection.cursor()

    try:
        # Fetch the article text from the article URL (You may need to use a library like requests to fetch the text)
        article_text = fetch_article_text(entry_url)

        cursor.execute(
            f'''
            UPDATE {table_name}
            SET entry_article_text = ?
            WHERE entry_id = ?
            ''', (article_text, entry_id))
        connection.commit()  # Commit immediately after updating

    except Exception as e:
        print(f"Error fetching or updating content for entry {entry_id}: {str(e)}")

    finally:
        # Release the connection back to the pool
        pool.release_connection(connection)



# Function to update summary for all tables
def update_summary_for_all_tables(pool, g4f):
    with concurrent.futures.ThreadPoolExecutor() as executor:
            # Get a connection from the pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = cursor.fetchall()

        for table_name in table_names:
            table_name = table_name[0]

            cursor.execute(f'''
                SELECT entry_id, entry_url, entry_article_text, entry_title, entry_date
                FROM {table_name}
                WHERE entry_summary = "NO SUMMARY"
            ''')

            entries_with_no_summary = cursor.fetchall()
            entries_with_no_summary = sorted(entries_with_no_summary, key=lambda x: datetime.strptime(x[4], '%a, %d %b %Y %H:%M:%S %z'), reverse=True)

            for entry_id, entry_url, entry_article_text, entry_title, entry_date in entries_with_no_summary:
                executor.submit(summarize_and_update,pool, g4f, table_name, entry_id, entry_article_text, entry_title)
        pool.release_connection(connection)


def summarize_and_update(pool, g4f, table_name, entry_id, entry_article_text, entry_title):
    try:
        connection = pool.get_connection()
        cursor = connection.cursor()
       
        summary = summarise(g4f, entry_article_text)

        if summary != "NO SUMMARY":
            cursor.execute(
                f'''
                UPDATE {table_name}
                SET entry_summary = ?
                WHERE entry_id = ?
                ''', (summary, entry_id))
            connection.commit()  # Commit immediately after updating
            print(f"Updated summary for {entry_title}")

        # Close the cursor and connection
        pool.release_connection(connection)

    except Exception as e:
        print(f"Error updating summary for {entry_title}: {str(e)}")
        pool.release_connection(connection)
    
    

# Function to update article text for all tables
def update_article_text_for_all_tables(pool):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Get a connection from the pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = cursor.fetchall()

        for table_name in table_names:
            table_name = table_name[0]

            cursor.execute(f'''
                SELECT entry_id, entry_url
                FROM {table_name}
                WHERE entry_article_text = ""
            ''')

            entries_with_no_article_text = cursor.fetchall()

            for entry_id, entry_url in entries_with_no_article_text:
                executor.submit(fetch_and_update_article_text, pool, table_name, entry_id, entry_url)

        # Release the connection back to the pool
        pool.release_connection(connection)
