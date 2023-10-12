import json
import os
import sqlite3
import concurrent.futures
import g4f
from sqliteconnectionpool import SQLiteConnectionPool



from database import initialize_db, complete_database
from feed import parse_opml, update_article_text_for_all_tables, update_summary_for_all_tables
from markdown import write_markdown_for_all_tables
from nextcloudsync import sync_with_nextcloud


# Define an asynchronous main function
def main():
  #conn, cursor = initialize_db()
  initialize_db()

  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  opml_file = config.get("opml_file", "feeds.opml")
  output_directory = config.get("output_directory", "output_directory")
  nextcloud_folder = config.get("nextcloud_folder", ".Notes/Current")
  database_name = config.get("database_name", "rss_feed.db")

  pool = SQLiteConnectionPool(max_connections=50, database_uri=database_name)


  if not os.path.exists(output_directory):
    os.makedirs(output_directory)

  complete_database(pool, opml_file)
  print("New entries added to the database")

  update_article_text_for_all_tables(pool)
  print("Article text updated in the database")

 

  for _ in range(5):
    update_summary_for_all_tables(pool, g4f)

  print("summary for new entries updated in the database")

  write_markdown_for_all_tables(pool)
  print("Markdown files written")

  #conn.commit()
  #conn.close()
  pool.close_all_connections()

  sync_with_nextcloud(output_directory, nextcloud_folder, resync=False)


if __name__ == '__main__':
  main()
