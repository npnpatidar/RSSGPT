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
  conn.close()
  #return conn, cursor


# Function to create a table
def create_table(feed_title, pool):
  connection = pool.get_connection()
  cursor = connection.cursor()
  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  table_name = feed_title.replace(' ', '_')
  table_schema = config.get("table_schema", {})
  schema_str = ", ".join(f"{col} {type}" for col, type in table_schema.items())

  cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} ({schema_str})
    ''')
  cursor.connection.commit()
  pool.release_connection(connection)


# Function to complete the database
def complete_database(pool, feed_file):
  connection = pool.get_connection()
  cursor = connection.cursor()
  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  feeds = parse_opml(feed_file)
  for feed in feeds:
    feed_title = feed['title']
    feed_url = feed['url']

    create_table(feed_title, pool)
    feed_data = fetch_feed_data(feed_url)

    for entry in feed_data:
      insert_article_data(feed_title, entry, pool)

  pool.release_connection(connection)



def mark_entry_not_written_in_all_tables(pool):
    try:
      connection = pool.get_connection()
      cursor =  connection.cursor()
     
      # Fetch all table names in the database
      cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
      tables = cursor.fetchall()

      for table in tables:
          table_name = table[0]
          cursor.execute(f"UPDATE {table_name} SET entry_written = 0;")

      cursor.connection.commit()
      pool.release_connection(connection)
      print("Successfully marked 'entry_written' as False in all tables.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
      print(f"Error: {e}")


