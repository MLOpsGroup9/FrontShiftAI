import sys
import tqdm
import logging
import requests
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import os  # Keep for os.getenv only

load_dotenv()

# ---------------------------------------------------------------------
# Dynamic and portable directory setup (works on any system)
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]  # one level up from scripts/
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
LOG_DIR = BASE_DIR / "logs" / "download_data_log"
URLS_PATH = DATA_DIR / "url.json"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logging.basicConfig(
    filename=LOG_DIR / "download.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------------------------------------------------------------
# PDF Download Function
# ---------------------------------------------------------------------
def download_pdf(urls_path: Path, save_dir: Path) -> None:
    """
    Downloads PDFs from a list of URLs specified in a JSON file.

    Args:
        urls_path (Path): Path to the JSON file containing list of {"domain": ..., "company": ..., "url": ...}
        save_dir (Path): Directory where the downloaded PDFs should be saved.
    """
    with open(urls_path, 'r') as f:
        url_list = json.load(f)

    logging.info(f"\n{'=' * 50} NEW RUN @ {datetime.now()} {'=' * 50}")

    for entry in tqdm.tqdm(url_list, desc="Downloading PDFs..."):
        domain = entry.get("domain")
        company = entry.get("company")
        url = entry.get("url")

        if not url:
            logging.warning(f"Skipping empty URL for domain {domain}, company {company}")
            continue

        try:
            # Clean up names to avoid invalid characters in filenames
            sanitized_domain = re.sub(r'[^\w\-_.]', '_', domain or "unknown_domain")
            sanitized_company = re.sub(r'[^\w\-_.]', '_', company or "unknown_company")

            # Create descriptive filename
            url_path = Path(url)
            filename = f"{sanitized_domain}_{sanitized_company}_{url_path.name}"
            savepath = save_dir / filename

            if savepath.exists():
                logging.info(f"File already exists: {filename}, skipping download")
                continue

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.9; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0 Safari/537.36"
                )
            }

            response = requests.get(url, headers=headers, stream=True, timeout=10)

            if response.ok:
                with open(savepath, "wb") as f_out:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f_out.write(chunk)
                logging.info(f"Downloaded: {filename} | Domain: {domain} | Company: {company}")
            else:
                logging.info(f"Failed to download {url} (Status: {response.status_code}) | Domain: {domain} | Company: {company}")

        except requests.exceptions.RequestException as e:
            logging.exception(f"Error downloading {url} | Domain: {domain} | Company: {company} | Error: {e}")

# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    if not URLS_PATH.exists():
        logging.error(f"URL file not found: {URLS_PATH}")
        sys.exit(1)

    download_pdf(urls_path=URLS_PATH, save_dir=RAW_DATA_DIR)
