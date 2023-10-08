import os
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict
import requests
import feedparser
import re
import g4f
import zipfile


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

# Function to simplify a URL
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
                article_text = fetch_article_text(entry.link)
                print("summarising article text for ", entry.title)
                generated_summary = summarise(article_text)
                print("writing summary for ", entry.title)
                markdown_file.write(generated_summary + '\n\n')


# function to generate summary
def summarise(article_text):
    
    summary=""

        # Define your conversation with the model
    conversation = [
        {"role": "system", "content": "You are a helpful assistant that summarizes articles.Now summarize this article:" + article_text },
    ]

    # Make a request to GPT-3 for summarization
    response = g4f.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation,
        max_tokens=500,  # Adjust the max_tokens to control the length of the summary
        stream=False,  # Set to False to get a single response
    )

    # Extract and print the summary from the response
    for message in response:

        summary += message
    
    return summary



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



# Function to parse OPML file and extract feed URLs
def parse_opml1(opml_content):
    feed_urls = []
    soup = BeautifulSoup(opml_content, "html.parser")
    outlines = soup.find_all("outline")
    for outline in outlines:
        if outline.get("xmlUrl"):
            feed_urls.append(outline["xmlUrl"])
    return feed_urls

# Function to parse OPML file and extract feed URLs
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


def share_folder_contents(folder_path, api_url):
    try:
        # Name for the ZIP archive
        zip_file_name = "folder_contents.zip"

        # Create the ZIP archive
        with zipfile.ZipFile(zip_file_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname=arcname)

        # Upload the ZIP file to the file-sharing service
        with open(zip_file_name, "rb") as file:
            response = requests.post(api_url, files={"file": file})

        # Parse the response JSON to get the sharing link
        if response.status_code == 200:
            data = response.json()
            share_link = data.get("link")
            if share_link:
                # Delete the ZIP file after successful upload and sharing
                os.remove(zip_file_name)
            return share_link
        else:
            return None

    except Exception as e:
        print("An error occurred:", str(e))
        return None


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



# share folder
folder_path = "markdown_files"
api_url = "https://file.io"
share_link = share_folder_contents(folder_path, api_url)
if share_link:
    print("File uploaded and shared:", share_link)
else:
    print("Failed to upload and share the file.")
