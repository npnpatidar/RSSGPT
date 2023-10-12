import sqlite3
import json
from feed import parse_opml, fetch_feed_data, insert_article_data


# Function to initialize the database
def initialize_db():
  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  db_name = config.get("database_name", "default.db")
  conn = sqlite3.connect(db_name)
  cursor = conn.cursor()
  return conn, cursor


# Function to create a table
def create_table(feed_title, cursor):
  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  table_name = feed_title.replace(' ', '_')
  table_schema = config.get("table_schema", {})
  schema_str = ", ".join(f"{col} {type}" for col, type in table_schema.items())

  cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} ({schema_str})
    ''')
  cursor.connection.commit()


# Function to complete the database
def complete_database(cursor, feed_file):
  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  feeds = parse_opml(feed_file)
  for feed in feeds:
    feed_title = feed['title']
    feed_url = feed['url']

    create_table(feed_title, cursor)
    feed_data = fetch_feed_data(feed_url)

    for entry in feed_data:
      insert_article_data(feed_title, entry, cursor)

  cursor.connection.commit()
