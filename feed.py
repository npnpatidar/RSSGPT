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
def insert_article_data(feed_title, entry, cursor):

  if validate_entry(entry):
    table_name = feed_title.replace(' ', '_')
    cursor.execute(
        f'''
            INSERT OR IGNORE INTO {table_name} (feed_unique_id, entry_title, entry_url, entry_summary,entry_article_text, entry_date, entry_written)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (entry.id, entry.title, entry.link, "NO SUMMARY", "",
              entry.published, False))


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
def summarise(article_text):
  max_attempts = 10
  summary = ""
  # Define your conversation with the model
  conversation = [
      {
          "role":
          "system",
          "content":
          "You are a helpful assistant that summarizes articles.Now summarize this article:"
          + article_text
      },
  ]

  for _ in range(max_attempts):
    try:
      response = g4f.ChatCompletion.create(
          model="gpt-3.5-turbo",
          messages=conversation,
          max_tokens=500,
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
      print(f"Error while summarizing article: {str(e)}")

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

def fetch_and_update_article_text(db_file, table_name, entry_id, entry_url):
    article_text = fetch_article_text(entry_url)
    print("article fetched")
    if article_text:
        with sqlite3.connect(db_file) as connection:
            cursor = connection.cursor()
            cursor.execute(f'''
                UPDATE {table_name}
                SET entry_article_text = ?
                WHERE entry_id = ?
            ''', (article_text, entry_id))


# Function to update summary for all tables
def update_summary_for_all_tables(cursor):

  # Get a list of all table names in the database
  cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
  table_names = cursor.fetchall()

  for table_name in table_names:
    table_name = table_name[0]  # Extract the table name from the result

    # Select entries with "NO Summary" in each table
    cursor.execute(f'''
            SELECT entry_id, entry_url, entry_article_text, entry_title
            FROM {table_name}
            WHERE entry_summary = "NO SUMMARY"
        ''')

    entries_with_no_summary = cursor.fetchall()

    for entry_id, entry_url, entry_article_text, entry_title in entries_with_no_summary:
      # Fetch the article text from the article URL (You may need to use a library like requests to fetch the text)

      print("summarising", entry_title)
      summary = summarise(
          entry_article_text)  # Implement fetch_article_text function

      if summary != "NO SUMMARY":
        cursor.execute(
            f'''
                    UPDATE {table_name}
                    SET entry_summary = ?
                    WHERE entry_id = ?
                ''', (summary, entry_id))
        print(f"Updated summary")
        cursor.connection.commit()


# Function to update article text for all tables
def update_article_text_for_all_tables(db_file):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        with sqlite3.connect(db_file) as connection:
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
                    executor.submit(fetch_and_update_article_text, db_file, table_name, entry_id, entry_url)
