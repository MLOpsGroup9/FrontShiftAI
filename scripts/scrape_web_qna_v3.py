"""
FrontShiftAI – HR Web Q&A Scraper
---------------------------------
Scrapes official FAQ pages (EEOC + DOL FLSA + DOL FMLA)
to extract real Q&A pairs for grounded dataset creation.

Usage:
    python scripts/scrape_web_qna.py

Output:
    data/qna/web_hr_qna.jsonl

Dependencies:
    pip install requests beautifulsoup4 tqdm
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ---------------------------------------------------------
# 1️⃣ Helper: Extract Q&A from a single page
# ---------------------------------------------------------
def extract_qna_from_url(url: str):
    print(f"\n🌐 Scraping: {url}")
    try:
        html = requests.get(url, timeout=20).text
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    qna_pairs = []

    # --- Pattern 1: <h2>/<h3> + next paragraph ---
    for h in soup.find_all(["h2", "h3"]):
        next_p = h.find_next_sibling(["p", "div"])
        if next_p and len(h.get_text(strip=True)) > 8 and len(next_p.get_text(strip=True)) > 20:
            qna_pairs.append({
                "question": h.get_text(" ", strip=True),
                "answer": next_p.get_text(" ", strip=True),
                "source": url
            })

    # --- Pattern 2: <dt>/<dd> pairs ---
    dts = soup.find_all("dt")
    dds = soup.find_all("dd")
    for dt, dd in zip(dts, dds):
        q = dt.get_text(" ", strip=True)
        a = dd.get_text(" ", strip=True)
        if len(q) > 8 and len(a) > 20:
            qna_pairs.append({
                "question": q,
                "answer": a,
                "source": url
            })

    # --- Pattern 3: <strong>Question</strong> followed by <p> ---
    for strong in soup.find_all("strong"):
        q_text = strong.get_text(" ", strip=True)
        nxt = strong.find_next_sibling("p")
        if nxt and len(q_text) > 8 and len(nxt.get_text(strip=True)) > 20:
            qna_pairs.append({
                "question": q_text,
                "answer": nxt.get_text(" ", strip=True),
                "source": url
            })

    print(f"✅ Found {len(qna_pairs)} Q&A pairs from {url}")
    return qna_pairs


# ---------------------------------------------------------
# 2️⃣ Scrape all URLs and save results
# ---------------------------------------------------------
def scrape_all(urls, output_path="data/qna/web_hr_qna.jsonl"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_qna = []

    for url in tqdm(urls, desc="Scraping sites"):
        qnas = extract_qna_from_url(url)
        all_qna.extend(qnas)

    # --- Deduplicate ---
    seen, unique_qna = set(), []
    for qa in all_qna:
        key = qa["question"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique_qna.append(qa)

    # --- Save ---
    with open(output_path, "w", encoding="utf-8") as f:
        for qa in unique_qna:
            f.write(json.dumps(qa, ensure_ascii=False) + "\n")

    print(f"\n💾 Saved {len(unique_qna)} unique Q&A pairs to {output_path}")


# ---------------------------------------------------------
# 3️⃣ Entry point
# ---------------------------------------------------------
if __name__ == "__main__":
    faq_urls = [
        "https://www.eeoc.gov/youth/frequently-asked-questions#Q1",
        "https://www.dol.gov/agencies/whd/flsa/faq",
        "https://www.dol.gov/agencies/whd/fmla/faq",
    ]
    scrape_all(faq_urls)
