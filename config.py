import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Chrome CDP Configuration
CHROME_CDP_URL = os.getenv("CHROME_CDP_URL", "http://localhost:9222")

# Directories and files
OUTPUT_DIR = BASE_DIR / "downloads"
COOKIES_FILE = BASE_DIR / "cookies.txt"
LOG_FILE = BASE_DIR / "downloader.log"               # File log text thô
DOWNLOAD_LOG_JSON = BASE_DIR / "download_log.json"    # File JSON lưu lịch sử download
METADATA_FILE = BASE_DIR / "metadata.json"

# Download Configuration
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VIDEO_QUALITY = "best"  # Giá trị mặc định là "best" để tránh build sai format filter của yt-dlp
MAX_WORKERS = 3

# Cleanup Configuration
CLEANUP_HOURS = 24
