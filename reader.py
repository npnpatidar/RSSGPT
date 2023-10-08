import os
import feedparser
import requests
from bs4 import BeautifulSoup
import markdown
import openai
import pickle
import g4f

# Function to fetch and parse RSS feeds
def fetch_rss_feeds(opml_file):
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

# Function to generate Markdown file
def generate_markdown(feeds, output_file, processed_entries_file):
    
    # Load processed entries from the file
    processed_entries = load_processed_entries(processed_entries_file)

    with open(output_file, 'w', encoding='utf-8') as md_file:
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                entry_id = entry.get('id')  # Use the 'id' field as the unique identifier
                if entry_id not in processed_entries:
                    print(entry_id)
                    title = entry.title
                    link = entry.link
                    article_text = fetch_article_text(link)
                   # article_text=entry_id
                    if article_text:
                        generated_summary = summarise(article_text)
                        md_file.write(f"## [{title}]({link})\n\n")
                        md_file.write(generated_summary + '\n\n')
                    processed_entries.add(entry_id)  # Add the entry to the processed set
    # Save the updated processed entries back to the file
    save_processed_entries(processed_entries, processed_entries_file)



# Function to load processed entries from a file
def load_processed_entries(file_path):
    try:
        with open(file_path, 'rb') as file:
            processed_entries = pickle.load(file)
            if isinstance(processed_entries, set):
                return processed_entries
            else:
                return set()  # Initialize an empty set if the loaded data is not a set
    except (FileNotFoundError, pickle.UnpicklingError):
        return set()  # Initialize an empty set if the file doesn't exist or is empty

# Function to save processed entries to a file
def save_processed_entries(processed_entries, file_path):
    with open(file_path, 'wb') as file:
        pickle.dump(processed_entries, file)


# Function to generate summary from local model
def generate_summary(article_text, model_name="ggml-model-gpt4all-falcon-q4_0"):
    openai.api_base = "http://localhost:4891/v1"  # Replace with your local API endpoint
    # openai.api_base = "https://api.openai.com/v1"
    
    # You can set your API key here if needed, but it's not required for a local model
    openai.api_key = "not needed for a local LLM"

    # Set up the prompt and other parameters for the API request
    prompt = article_text
    
    # Make the API request
    response = openai.Completion.create(
        model=model_name,
        prompt=prompt,
        max_tokens=250,  # Adjust max_tokens as needed for desired summary length
        temperature=0.28,
        top_p=0.95,
        n=1,
        echo=True,
        stream=False
    )

    # Extract and return the generated summary from the response
    summary = response.choices[0].text.strip()
    return summary


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
       

# Main function
def main():
    opml_file = 'FocusReader.opml'  # Replace with the path to your OPML file
    output_file = 'articles.md'  # Customize the output file name
    processed_entries_file= 'processed_entries.pickle'  # Save processed entries to this file 

    if not os.path.exists(opml_file):
        print(f"OPML file '{opml_file}' not found.")
        return

    feeds = fetch_rss_feeds(opml_file)
    if not feeds:
        print("No RSS feeds found in the OPML file.")
        return

    generate_markdown(feeds, output_file, processed_entries_file)
    print(f"Markdown file '{output_file}' generated with article text.")

if __name__ == "__main__":
    main()