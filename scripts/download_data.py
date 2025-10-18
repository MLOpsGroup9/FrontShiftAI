import sys
import tqdm 
import logging
import requests
import json 
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
import os  # Keep for os.getenv only

load_dotenv()

RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "./data/raw"))
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs/download_data_log"))

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "download.log",
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)


def get_first_json_path(folder_path: str) -> Optional[Path]:
    """Return the path to the first .json file in the given folder."""
    folder = Path(folder_path)
    for file in folder.iterdir():
        if file.suffix == ".json":
            return file
    return None


def download_pdf(urls_path: Path, save_dir: Path) -> None: 
    """
    Downloads PDFs from a list of URLs specified in a JSON file.

    Args:
        urls_path (Path): Path to the JSON file containing list of {"domain": ..., "url": ...}
        save_dir (Path): Directory where the downloaded PDFs should be saved.
    """
    with open(urls_path, 'r') as f:
        url_list = json.load(f) 

    logging.info(f"\n{'='*50} NEW RUN @ {datetime.now()} {'='*50}")

    for entry in tqdm.tqdm(url_list, desc="Downloading PDFs..."):
        domain = entry.get("domain")
        url = entry.get("url")

        if not url: 
            logging.warning(f"Skipping empty URL for domain {domain}")
            continue 

        try:
            sanitized_domain = re.sub(r'[^\w\-_.]', '_', domain)
            url_path = Path(url)
            filename = f"{sanitized_domain}_{url_path.name}"
            savepath = save_dir / filename

            if savepath.exists():
                logging.info(f"File already exists: {filename}, skipping download")
                continue
                
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.9; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, stream=True, timeout=10)

            if response.ok:
                with open(savepath, "wb") as f_out:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f_out.write(chunk)
                logging.info(f"Successfully downloaded: {filename}")
            else:
                logging.info(f"Failed to download {url} with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            logging.exception(f"Error Downloading {url}: {e}")


if __name__ == "__main__":
    urls_path = get_first_json_path("./data")
    if urls_path is None:
        logging.error("No JSON file found in the ./data folder")
        sys.exit(1)

    download_pdf(urls_path=urls_path, save_dir=RAW_DATA_DIR)