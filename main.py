import feeder
import nextcloudsync
import os

os.environ['TZ'] = 'Asia/Kolkata'
opml_file = "markdown_files/config_files/Feeds.opml"
last_run_date_file = "markdown_files/config_files/last_run_date.txt"
local_folder = "markdown_files"
nextcloud_folder = ".Notes/Current"
resync_flag = False  # Set to True or False as needed

feeder.write_markdown_files(opml_file, last_run_date_file)

# Call the sync function with the resync flag
nextcloudsync.sync_with_nextcloud(local_folder,
                                  nextcloud_folder,
                                  resync=resync_flag)
