import os
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict
import requests
import feedparser
import re
import reader

# Function to read the last run date from a file
def read_last_run_date():
    last_run_date = None
    try:
        with open("last_run_date.txt", "r", encoding="utf-8") as file:
            last_run_date = file.read()
            last_run_date = datetime.strptime(last_run_date, "%Y-%m-%d %H:%M:%S")
    except FileNotFoundError:
        pass  # The file doesn't exist yet, so the default value remains None
    except ValueError:
        pass  # Error parsing the date, the default value remains None

    print("last run date is ", last_run_date)
    return last_run_date

# Function to write the last run date to a file
def write_last_run_date(date):
    with open("last_run_date.txt", "w", encoding="utf-8") as file:
        print("last run date is ", date)
        file.write(date.strftime("%Y-%m-%d %H:%M:%S"))

def simplify_string(s):
    # Remove common web prefixes and suffixes
    s = re.sub(r'^https?://', '', s)  # Remove http:// or https://
    s = re.sub(r'^www\.', '', s)      # Remove www.
    s = re.sub(r'\.com', '', s)      # Remove .com
    s = re.sub(r'\.xml', '', s)      # Remove .xml
    s = re.sub(r'\.in', '', s)      # Remove .in
    s = re.sub(r'\.org', '', s)      # Remove .org
    s = re.sub(r'\.gov', '', s)      # Remove .gov
   

    # Split the URL and keep only the website name and the last part
    parts = s.split('/')
    if parts:
        s = parts[0] + '-' + parts[-1]

    # Remove non-alphabet characters
    return re.sub(r'[^a-zA-Z-]', '', s)



# Function to create a Markdown file from a feed's entries
def create_markdown_file(feed_url, entries):
    # Create a directory to store Markdown files if it doesn't exist
    if not os.path.exists("markdown_files"):
        os.mkdir("markdown_files")
    
    simplified_feedurl = simplify_string(feed_url)

    # Create a Markdown file for the feed
    file_name = os.path.join("markdown_files", f"{simplified_feedurl}.md")

    with open(file_name, "a", encoding="utf-8") as markdown_file:
        # Group entries by published date
        entries_by_date = defaultdict(list)
        for entry in entries:
            published_date = entry.published_parsed
            entries_by_date[published_date].append(entry)

        # Sort entries within each date group by published date
        for date, date_entries in sorted(entries_by_date.items(), reverse=True):
            markdown_file.write(f"### {datetime(*date[:6]).strftime('%B %d, %Y')}\n\n")
            for entry in date_entries:
                markdown_file.write(f"## [{entry.title}]({entry.link})\n\n")
                print("fetching article text for ", entry.title)
                article_text = reader.fetch_article_text(entry.link)
                print("summarising article text for ", entry.title)
                generated_summary = reader.summarise(article_text)
                print("writing summary for ", entry.title)
                markdown_file.write(generated_summary + '\n\n')

               

# Function to parse OPML file and extract feed URLs
def parse_opml1(opml_content):
    feed_urls = []
    soup = BeautifulSoup(opml_content, "html.parser")
    outlines = soup.find_all("outline")
    for outline in outlines:
        if outline.get("xmlUrl"):
            feed_urls.append(outline["xmlUrl"])
    return feed_urls


def parse_opml(opml_file):
    feeds = []
    with open(opml_file, 'r') as file:
        soup = BeautifulSoup(file, 'xml')
        outlines = soup.find_all('outline')
        for outline in outlines:
            if 'xmlUrl' in outline.attrs:
                feed_url = outline['xmlUrl']
                feeds.append(feed_url)
    print(feeds)
    return feeds



# Load the OPML file
opml_file = "Feeds.opml"

# Read the OPML file content
with open(opml_file, "r", encoding="utf-8") as file:
    opml_content = file.read()

# Parse the OPML content to get feed URLs
feed_urls = parse_opml(opml_file)

# Read the last run date from the file
last_run_date = read_last_run_date()

# Iterate through each feed URL and create Markdown files for new articles
for feed_url in feed_urls:
    response = requests.get(feed_url)
    response.raise_for_status()
    feed_content = response.text

    entries = feedparser.parse(feed_content).entries

    # Filter entries to keep only those published after the last run date
    if last_run_date:
        entries = [entry for entry in entries if datetime(*entry.published_parsed[:6]) > last_run_date]

    if entries:
        # Create or append to the Markdown file for the feed
        create_markdown_file(feed_url, entries)

# Write the current date and time as the new last run date
write_last_run_date(datetime.now())

print("Markdown files updated successfully.")
