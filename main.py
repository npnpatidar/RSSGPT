import feedparser
import os
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
# the base class to inherit from when creating your own formatter.
from youtube_transcript_api.formatters import Formatter

# some provided subclasses, each outputs a different string format.
from youtube_transcript_api.formatters import JSONFormatter
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.formatters import WebVTTFormatter
from youtube_transcript_api.formatters import SRTFormatter

def get_youtube_transcript(video_url, language_code='en'):
    try:
        # Parse the URL to extract the video ID
        parsed_url = urlparse(video_url)
        video_id = parse_qs(parsed_url.query)['v'][0]

        # Fetch the transcript

        # transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])

        formatter = JSONFormatter()

        # .format_transcript(transcript) turns the transcript into a JSON string.
        json_formatted = formatter.format_transcript(transcript)    
        
        # Combine the transcript into a single string
        complete_transcript = ' '.join([t['text'] for t in transcript])
        return complete_transcript
    
    except Exception as e:
        return str(e)


def read_rss_feed(url):
    try:
        # Parse the RSS feed
        feed = feedparser.parse(url)

        # Check if feed parsing was successful
        if 'title' not in feed.feed:
            return {"error": "Unable to fetch feed or feed has no title."}

        # Prepare a list to store matching entries
        matching_entries = []

        # Loop through the entries in the feed
        for entry in feed.entries:
            # Check if required keywords are in the title (case-insensitive)
            if ("Current Affairs" in entry.title and 
                ("Kumar Gaurav" in entry.title or "Narendra Sir" in entry.title)):

                # Append relevant details as JSON object
                matching_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published if 'published' in entry else "Unknown"
                })

        # Return the matching entries
        return matching_entries

    except Exception as e:
        return {"error": str(e)}



def filter_and_save_new_links(entries, file_path="processed_links.txt"):
    """
    Filters new links from entries and saves them to a file if they are not already processed.

    :param entries: List of JSON-like dictionaries containing entries with "link" key.
    :param file_path: Path to the file that stores already processed links.
    :return: List of new entries that are not in the file.
    """
    try:
        # Ensure the file exists
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                pass  # Create an empty file if it doesn't exist

        # Load existing links from the file
        with open(file_path, "r") as f:
            processed_links = set(line.strip() for line in f)

        # Filter out entries whose links are already processed
        new_entries = [entry for entry in entries if entry["link"] not in processed_links]

        # Add new links to the file
        with open(file_path, "a") as f:
            for entry in new_entries:
                f.write(entry["link"] + "\n")

        return new_entries

    except Exception as e:
        print(f"Error: {e}")
        return []


if __name__ == "__main__":
    # Example RSS feed URL
    # rss_url = input("Enter RSS feed URL: ").strip()
   matching_entries = read_rss_feed('https://www.youtube.com/feeds/videos.xml?channel_id=UCLuBF4Xr1-BIpcpFFm7zp7w')

   new_entries = filter_and_save_new_links(matching_entries)

   if not new_entries:
       print("No new entries found.")
       exit()
   else:
    for entry in new_entries:
        transcript = get_youtube_transcript(entry['link'], language_code='hi')
        with open(f"{entry['title']}.txt", "w") as f:
            f.write(transcript)



  




























# from youtube_transcript_api import YouTubeTranscriptApi

# video_url = "https://www.youtube.com/watch?v=_xmip0CvbkY&list=PLoZP2WsNfBSFZX-5fd4WWVgp0TLYKZbcj&index=1&pp=iAQB"

# # Get the video_id
# video_id = video_url.split("=")[1]
# transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi'])

# complete_transcript = ' '.join([t['text'] for t in transcript])
# print(complete_transcript)





# # Example usage
# video_url = "https://www.youtube.com/watch?v=knz9SVNhL-M&list=PLoZP2WsNfBSFZX-5fd4WWVgp0TLYKZbcj&index=2&pp=iAQB"
# video_url ="https://www.youtube.com/watch?v=oFfVt3S51T4&pp=ygULbGV4IGZyaWRtYW4%3D"
transcript = get_youtube_transcript(video_url, language_code='hi')
print(transcript)



# import argparse
# from youtube_transcript_api import YouTubeTranscriptApi
# from urllib.parse import urlparse, parse_qs

# def get_youtube_transcript(video_url, language_code='en'):
#     try:
#         # Parse the URL to extract the video ID
#         parsed_url = urlparse(video_url)
#         video_id = parse_qs(parsed_url.query)['v'][0]

#         # Fetch the transcript
#         transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
        
#         # Combine the transcript into a single string
#         complete_transcript = ' '.join([t['text'] for t in transcript])
#         return complete_transcript
    
#     except Exception as e:
#         return str(e)

# def main():
#     # Set up argument parsing
#     parser = argparse.ArgumentParser(description='Get YouTube video transcript.')
#     parser.add_argument('url', type=str, help='The URL of the YouTube video.')
#     parser.add_argument('--language', type=str, default='en', help='Language code for the transcript (default: en).')
    
#     # Parse arguments
#     args = parser.parse_args()

#     # Get the transcript
#     transcript = get_youtube_transcript(args.url, language_code=args.language)
    
#     # Print the transcript
#     print(transcript)

# if __name__ == '__main__':
#     main()

