import os
import subprocess
import tempfile


def create_rclone_config(nextcloud_url, nextcloud_user, nextcloud_pass):
  # Create a temporary rclone configuration file
  with tempfile.NamedTemporaryFile(mode="w", delete=False) as config_file:
    config = f"""
        [nextcloud]
        type = webdav
        url = {nextcloud_url}
        vendor = nextcloud
        user = {nextcloud_user}
        pass = {nextcloud_pass}
        """
    config_file.write(config)
    return config_file.name


def sync_with_nextcloud(local_folder, nextcloud_folder, resync=False):
  try:
    # Get the Nextcloud configuration from environment variables
    nextcloud_url = os.environ['NEXTCLOUD_URL']
    nextcloud_user = os.environ['NEXTCLOUD_USER']
    nextcloud_pass = os.environ['NEXTCLOUD_PASS']

    # Create the rclone configuration file
    rclone_config_file = create_rclone_config(nextcloud_url, nextcloud_user,
                                              nextcloud_pass)

    # Define the rclone command with or without --resync based on the resync flag
    command = [
        "rclone",
        "--config",
        rclone_config_file,  # Use the dynamically created config file
        "sync",
        local_folder,
        f"nextcloud:{nextcloud_folder}",
    ]

    # Include --resync if resync is True
    if resync:
      command.append("--resync")

    # Run the rclone command
    result = subprocess.run(command,
                            capture_output=True,
                            text=True,
                            check=True)

    # Print the command output
    print("Rclone Output:", result.stdout)
    print("Rclone Error Output:", result.stderr)

    return True
  except subprocess.CalledProcessError as e:
    print("Error running rclone:", e)
    return False
