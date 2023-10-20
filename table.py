import sqlite3

# Function to list all tables in the database
def list_tables(database_name):
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    conn.close()

    return [table[0] for table in tables]

# Function to delete a specific table
def delete_table(database_name, table_name):
    conn = sqlite3.connect(database_name)
    cursor = conn.cursor()

    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
    conn.commit()

    conn.close()

# Example usage:
# Replace "your_database.db" with the name of your SQLite database file
database_name = "rss_feed.db"

# List all tables in the database
tables = list_tables(database_name)
print("Tables in the database:")
for table in tables:
    print(table)

# Specify the table to delete
table_to_delete = "table_name_to_delete"

# Delete the specified table
delete_table(database_name, table_to_delete)

# Confirm deletion by listing tables again
tables = list_tables(database_name)
print(f"{table_to_delete} has been deleted.")