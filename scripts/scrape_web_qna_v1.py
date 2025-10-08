"""
FrontShiftAI – Government HR FAQ Scraper (EEOC + DOL)
Version 2 – Fixes misaligned Q/A pairs from EEOC
------------------------------------------------------
Extracts real, grounded Q&A pairs from:
    - EEOC Youth FAQ
    - DOL FLSA FAQ
    - DOL FMLA FAQ
Output:
    data/qna/web_hr_qna_v2.jsonl
"""

import os, re, json, requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"^\(Q\)\s*|^Q:\s*", "", text, flags=re.I)
    text = re.sub(r"^\(A\)\s*|^A:\s*", "", text, flags=re.I)
    return text


# --------------------------- EEOC parser ---------------------------
def parse_eeoc_style(soup, url):
    qna = []
    p_tags = soup.find_all("p")
    i = 0
    while i < len(p_tags):
        text = clean(p_tags[i].get_text())
        # detect question
        if re.match(r"^(Q:|\(Q\))", p_tags[i].get_text().strip(), re.I):
            if i + 1 < len(p_tags):
                next_text = p_tags[i + 1].get_text().strip()
                if re.match(r"^(A:|\(A\))", next_text, re.I):
                    question = clean(p_tags[i].get_text())
                    answer = clean(p_tags[i + 1].get_text())
                    if len(question) > 10 and len(answer) > 10:
                        qna.append({
                            "question": question,
                            "answer": answer,
                            "source": url
                        })
                    i += 1  # skip the A
        i += 1
    return qna


# --------------------------- DOL parser ---------------------------
def parse_dol_style(soup, url):
    qna = []
    for h in soup.find_all(["h2", "h3"]):
        p_tag = h.find_next_sibling("p")
        if not p_tag:
            continue
        q = clean(p_tag.get_text())
        if "(Q)" not in p_tag.get_text() and "?" not in p_tag.get_text():
            continue
        ans_tag = p_tag.find_next_sibling(["div", "ul", "ol", "p"])
        if not ans_tag:
            continue
        a = clean(ans_tag.get_text(separator=" "))
        if len(q) > 10 and len(a) > 30:
            qna.append({
                "question": q,
                "answer": a,
                "source": url
            })
    return qna


# --------------------------- main function ---------------------------
def extract_qna(url):
    print(f"\n🌐 Scraping: {url}")
    try:
        html = requests.get(url, timeout=30).text
    except Exception as e:
        print(f"❌ Failed: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")

    if "eeoc" in url:
        qna = parse_eeoc_style(soup, url)
    else:
        qna = parse_dol_style(soup, url)

    print(f"✅ {len(qna)} Q&A pairs from {url}")
    return qna


def scrape_all(urls, output="data/qna/web_hr_qna_v2.jsonl"):
    os.makedirs(os.path.dirname(output), exist_ok=True)
    all_qna, seen = [], set()

    for url in tqdm(urls, desc="Scraping"):
        for qa in extract_qna(url):
            key = qa["question"].lower().strip()
            if key not in seen:
                seen.add(key)
                all_qna.append(qa)

    with open(output, "w", encoding="utf-8") as f:
        for qa in all_qna:
            f.write(json.dumps(qa, ensure_ascii=False) + "\n")

    print(f"\n💾 Saved {len(all_qna)} cleaned Q&A pairs to {output}")


if __name__ == "__main__":
    urls = [
        "https://www.eeoc.gov/youth/frequently-asked-questions#Q1",
        "https://www.dol.gov/agencies/whd/flsa/faq",
        "https://www.dol.gov/agencies/whd/fmla/faq"
    ]
    scrape_all(urls)
