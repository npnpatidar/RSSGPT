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
def write_entries_to_markdown(pool, table_name):
  connection = pool.get_connection()
  cursor = connection.cursor()
  cursor.execute(f'''
    SELECT *
    FROM {table_name}
    WHERE entry_written = 0  -- Select entries with entry_written as false
      AND entry_summary <> "NO SUMMARY"  -- Exclude entries with entry_summary as "NO SUMMARY"
  ''')
  entries = cursor.fetchall()
  entries = sorted(entries, key=lambda x: datetime.strptime(x[6], '%a, %d %b %Y %H:%M:%S %z'), reverse=True)

  if not entries:
    return  # No entries to write

  with open('config.json', 'r') as config_file:
    config = json.load(config_file)

  output_directory = config.get("output_directory", "output_directory")
  is_summary = config.get("is_summary", True)

  markdown_filepath = os.path.join(output_directory, f"{table_name}.md")
  file_exists = os.path.isfile(markdown_filepath)

  with open(markdown_filepath, 'a', encoding='utf-8') as markdown_file:
    for entry in entries:
      entry_id, _, entry_title, entry_url, entry_summary, entry_article_text, entry_date, _ = entry
      formatted_date = datetime.strptime(
          entry_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d')

      # Write the entry to the markdown file
      markdown_file.write(f"Published Date: {formatted_date}\n")
      markdown_file.write(f"## [{entry_title}]({entry_url})\n\n")
      if is_summary:
        markdown_file.write(f"Summary: {entry_summary}\n")
      else:
        markdown_file.write(f"Article: {entry_article_text}\n\n")
  
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
  connection.commit()
  pool.release_connection(connection)


# Function to write markdown for all tables
def write_markdown_for_all_tables(pool):
  connection = pool.get_connection()
  cursor = connection.cursor()
  cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
  table_names = cursor.fetchall()

  for table_name in table_names:
    table_name = table_name[0]  # Extract the table name from the result
    write_entries_to_markdown(pool, table_name)
  cursor.connection.commit()
  pool.release_connection(connection)




def write_markdown_for_date(pool, specific_date):
    try:
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Get the list of table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        table_names = cursor.fetchall()

        # Create a list to store the results
        entries = []

        # Loop through the tables and execute the query for each table
        for table_name in table_names:
            table_name = table_name[0]

            # Construct and execute the SQL query
            query = f'''
                SELECT *
                FROM {table_name}
                WHERE strftime('%d/%m/%Y', entry_date) = ?
            '''
            cursor.execute(query, (specific_date,))

            # Fetch the results and add them to the list
            entries.extend(cursor.fetchall())

    except Exception as e:
        print(f"Error: {str(e)}")
        return

    finally:
        pool.release_connection(connection)

    with open('config.json', 'r') as config_file:
        config = json.load(config_file)

    output_directory = config.get("output_directory", "output_directory")
    date_formatted_file_path = specific_date.replace('/', '_')
    markdown_filepath = os.path.join(output_directory, f"{date_formatted_file_path}.md")

    # Write the markdown file
    with open(markdown_filepath, 'w', encoding='utf-8') as markdown_file:
        for entry in entries:
            entry_id, _, entry_title, entry_url, entry_summary, entry_article_text, entry_date, _ = entry
            formatted_date = datetime.strptime(entry_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%d/%m/%Y')

            # Write the entry to the markdown file
            markdown_file.write(f"Published Date: {formatted_date}\n")
            markdown_file.write(f"## [{entry_title}]({entry_url})\n\n")
            if entry_summary != "NO SUMMARY":
                markdown_file.write(f"Summary: {entry_summary}\n")
            else:
                markdown_file.write(f"Article: {entry_article_text}\n\n")

            markdown_file.write("\n")
