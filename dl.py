import os
import re
import requests
from urllib.parse import urlparse

# Get the script's directory as the working root
project_root = os.path.dirname(os.path.abspath(__file__))
assets_folder = os.path.join(project_root, "assets")
fonts_folder = os.path.join(assets_folder, "fonts")

# Ensure assets and fonts folders exist
os.makedirs(assets_folder, exist_ok=True)
os.makedirs(fonts_folder, exist_ok=True)

# Supported file extensions
image_extensions = [".svg", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".bmp", ".avif"]
font_extensions = [".woff", ".woff2"]
pdf_extensions = [".pdf"]
video_extensions = [".webm"]

# Regex patterns for finding references in HTML and CSS
html_img_pattern = re.compile(
    r'(https?://[^"\'>]+\.(?:' + '|'.join(ext.strip('.') for ext in image_extensions) + '))',
    re.IGNORECASE,
)
html_pdf_pattern = re.compile(
    r'(https?://[^"\'>]+\.(?:' + '|'.join(ext.strip('.') for ext in pdf_extensions) + '))',
    re.IGNORECASE,
)
html_video_pattern = re.compile(
    r'(https?://[^"\'>]+\.(?:' + '|'.join(ext.strip('.') for ext in video_extensions) + '))',
    re.IGNORECASE,
)

srcset_pattern = re.compile(r'srcset\s*=\s*"([^"]+)"', re.IGNORECASE)
css_asset_pattern = re.compile(
    r'''url\(["']?(http[s]?://[^"')]+\.(?:''' + '|'.join(ext.strip('.') for ext in image_extensions + font_extensions) + r'''))["']?\)''',
    re.IGNORECASE
)

def download_file(file_url, target_folder):
    """Download file to the target folder if it doesn't already exist.
       Removes '%20' from the URL and all special characters from the file name.
    """
    try:
        # Remove '%20' from the URL to sanitize the file name.
        sanitized_url = file_url.replace("%20", "")
        parsed_url = urlparse(sanitized_url)
        file_name = os.path.basename(parsed_url.path)
        # Remove '%20' from file_name as well.
        file_name = file_name.replace("%20", "")
        # Remove special characters from file_name except alphanumeric characters, underscores, hyphens, and periods.
        file_name = re.sub(r'[^A-Za-z0-9._-]', '', file_name)
        local_path = os.path.join(target_folder, file_name)

        if os.path.exists(local_path):
            print(f"Already exists: {file_name}")
            return os.path.relpath(local_path, project_root)

        response = requests.get(file_url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Downloaded: {file_name}")
            return os.path.relpath(local_path, project_root)
        else:
            print(f"Failed to download (status code {response.status_code}): {file_url}")
    except requests.RequestException as e:
        print(f"Request failed for {file_url}: {e}")
    return None

def replace_urls_in_srcset(content):
    """Extract all URLs from srcset and replace them."""
    matches = srcset_pattern.findall(content)
    for match in matches:
        parts = match.split(',')
        for part in parts:
            url = part.strip().split(' ')[0]
            if url.startswith('http'):
                ext = os.path.splitext(urlparse(url).path)[1].lower()
                folder = fonts_folder if ext in font_extensions else assets_folder
                local_path = download_file(url, folder)
                if local_path:
                    content = content.replace(url, local_path.replace('\\', '/'))
    return content

def replace_references(file_path, pattern):
    """Replace URLs with local paths in a file based on the provided pattern."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = replace_urls_in_srcset(content)

    modified = False
    matches = pattern.findall(content)
    for url in set(matches):
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        folder = fonts_folder if ext in font_extensions else assets_folder
        local_path = download_file(url, folder)
        if local_path:
            content = content.replace(url, "/"+local_path.replace('\\', '/'))
            modified = True

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated: {file_path}")

def process_files():
    """Walk through all HTML and CSS files and process them."""
    for root, _, files in os.walk(project_root):
        for file in files:
            file_path = os.path.join(root, file)
            if file.lower().endswith(".html"):
                # Process image URLs
                replace_references(file_path, html_img_pattern)
                # Process PDF URLs in HTML
                replace_references(file_path, html_pdf_pattern)
                # Process video URLs in HTML
                replace_references(file_path, html_video_pattern)
            elif file.lower().endswith(".css"):
                replace_references(file_path, css_asset_pattern)

if __name__ == "__main__":
    process_files()
    print("✅ All external assets downloaded and references updated!")