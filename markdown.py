import os
import markdown
import json
import sqlite3
from datetime import datetime


# Function to write entry to markdown
def write_to_markdown(cursor, feed_title, entry):
  table_name = feed_title.replace(' ', '_')
  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  output_directory = config.get("output_directory", "output_directory")

  markdown_content = f"{entry.title}\n\nPublished Date: {entry.published}\n\n{entry.summary}"
  markdown_filename = f"{feed_title}.md"
  markdown_filepath = os.path.join(output_directory, markdown_filename)

  with open(markdown_filepath, 'a', encoding='utf-8') as markdown_file:
    markdown_file.write(markdown_content)
    cursor.execute(
        f"UPDATE {table_name} SET entry_written = ? WHERE feed_unique_id = ?",
        (True, entry.id))
  cursor.connection.commit()


# Function to write entries to markdown
def write_entries_to_markdown(cursor, table_name):

  cursor.execute(f'''
        SELECT *
        FROM {table_name}
        WHERE entry_written = 0  -- Select entries with entry_written as false
        ORDER BY entry_date DESC  -- Sort by entry_date in descending order (latest to oldest)
    ''')
  entries = cursor.fetchall()

  if not entries:
    return  # No entries to write

  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  output_directory = config.get("output_directory", "output_directory")

  markdown_filepath = os.path.join(output_directory, f"{table_name}.md")
  file_exists = os.path.isfile(markdown_filepath)

  with open(markdown_filepath, 'a', encoding='utf-8') as markdown_file:
    for entry in entries:
      entry_id, _, entry_title, _, entry_summary, entry_article_text, entry_date, _ = entry
      formatted_date = datetime.strptime(
          entry_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d')

      # Write the entry to the markdown file
      markdown_file.write(f"# {entry_title}\n")
      markdown_file.write(f"Published Date: {formatted_date}\n")
      markdown_file.write(f"{entry_summary}\n")
      markdown_file.write(f"{entry_article_text}\n")
      markdown_file.write("\n")
      # Add more details as needed

      # Mark the entry as written in the database
      cursor.execute(
          f'''
                UPDATE {table_name}
                SET entry_written = 1
                WHERE entry_id = ?
            ''', (entry_id, ))

  # Commit changes to the database
  cursor.connection.commit()


# Function to write markdown for all tables
def write_markdown_for_all_tables(cursor):
  cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
  table_names = cursor.fetchall()

  for table_name in table_names:
    table_name = table_name[0]  # Extract the table name from the result
    write_entries_to_markdown(cursor, table_name)
  cursor.connection.commit()
