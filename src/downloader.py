import requests
import os
from urllib.parse import urlparse
from typing import Tuple

class Downloader:
    def download_markdown_from_url(self, url: str) -> Tuple[str, str]:
        """Download markdown file from URL and validate."""
        try:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            if not filename.endswith('.md'):
                print(f"❌ Error: File must have .md extension. Got: {filename}")
                return None, None
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            content = response.text
            
            if not content.strip():
                print(f"❌ Error: Downloaded file is empty")
                return None, None
                
            print(f"✅ Downloaded: {filename} ({len(content)} characters)")
            return filename, content
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading from {url}: {e}")
            return None, None
        except Exception as e:
            print(f"❌ Error processing {url}: {e}")
            return None, None
