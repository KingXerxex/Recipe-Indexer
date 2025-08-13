import requests
import subprocess
import os

# --- DYNAMIC URL CONFIGURATION ---
# The user and repository for your project
GITHUB_USER = "KingXerxex"
GITHUB_REPO = "Recipe-Indexer"

# The name of the application executable
APP_NAME = "recipe_hub.exe"

# The URL for the raw version.txt file
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}//refs/heads/main/version.txt"

# This is now a TEMPLATE for the download URL.
# The {tag} part will be replaced with the version number (e.g., v1.1, v1.2).
DOWNLOAD_URL_TEMPLATE = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/{{tag}}/{APP_NAME}"


try:
    # 1. Fetch latest version number from the server
    response = requests.get(VERSION_URL)
    response.raise_for_status() # Raise an error if the download fails
    server_version_str = response.text.strip()
    server_version = float(server_version_str)

    # 2. Read the local version number
    local_version = 0.0
    if os.path.exists("local_version.txt"):
        with open("local_version.txt", "r") as f:
            local_version = float(f.read().strip())

    # 3. Compare versions
    if server_version > local_version:
        print(f"Update found! Downloading version {server_version}...")
        
        # 4. Construct the dynamic download URL for the new version
        # Creates the tag name like "v1.2" from the version string "1.2"
        tag_name = "v" + server_version_str
        dynamic_download_url = DOWNLOAD_URL_TEMPLATE.format(tag=tag_name)
        
        print(f"Downloading from: {dynamic_download_url}")
        
        # 5. Download the new version using the dynamic URL
        new_app_data = requests.get(dynamic_download_url).content
        
        # 6. Replace the old file safely
        with open(APP_NAME + ".new", "wb") as f:
            f.write(new_app_data)
        
        if os.path.exists(APP_NAME):
            os.remove(APP_NAME)
        os.rename(APP_NAME + ".new", APP_NAME)
        
        # 7. Update the local version file
        with open("local_version.txt", "w") as f:
            f.write(server_version_str)
        
        print("Update complete!")

except Exception as e:
    print(f"Could not check for updates: {e}")

# 8. Launch the main application
print("Launching Recipe Hub...")
subprocess.Popen([APP_NAME])
