"""
FrontShiftAI – Government HR FAQ Scraper (EEOC + DOL)
Version 3 — broader DOL coverage + relaxed filters
"""

import os, re, json, requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def clean(txt):
    txt = re.sub(r"\s+", " ", txt or "").strip()
    txt = re.sub(r"^\(Q\)\s*|^Q:\s*", "", txt, flags=re.I)
    txt = re.sub(r"^\(A\)\s*|^A:\s*", "", txt, flags=re.I)
    return txt


# --------------------------- EEOC ---------------------------
def parse_eeoc(soup, url):
    out = []
    p = soup.find_all("p")
    i = 0
    while i < len(p):
        if re.match(r"^(Q:|\(Q\))", p[i].get_text().strip(), re.I):
            if i + 1 < len(p) and re.match(r"^(A:|\(A\))", p[i + 1].get_text().strip(), re.I):
                q = clean(p[i].get_text())
                a = clean(p[i + 1].get_text())
                if len(a) > 5:
                    out.append({"question": q, "answer": a, "source": url})
                i += 1
        i += 1
    return out


# --------------------------- DOL ---------------------------
def parse_dol(soup, url):
    out = []

    # Pattern A: <div class="faq"> style
    for faq in soup.select("div.faq, div.accordion-item, section.faq-item"):
        q_tag = faq.find(["h2", "h3", "h4", "summary"])
        a_tag = faq.find(["p", "div"], recursive=False)
        q = clean(q_tag.get_text()) if q_tag else ""
        a = clean(a_tag.get_text(separator=" ")) if a_tag else ""
        if len(q) > 5 and len(a) > 10:
            out.append({"question": q, "answer": a, "source": url})

    # Pattern B: fallback (h2 → p/div)
    for h in soup.find_all(["h2", "h3"]):
        p_tag = h.find_next_sibling("p")
        if not p_tag:
            continue
        q = clean(p_tag.get_text())
        ans = p_tag.find_next_sibling(["div", "ul", "ol", "p"])
        if ans:
            a = clean(ans.get_text(separator=" "))
            if len(q) > 5 and len(a) > 10:
                out.append({"question": q, "answer": a, "source": url})
    return out


def extract_qna(url):
    print(f"\n🌐 {url}")
    try:
        html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
    except Exception as e:
        print("❌", e)
        return []
    soup = BeautifulSoup(html, "html.parser")
    return parse_eeoc(soup, url) if "eeoc" in url else parse_dol(soup, url)


def scrape_all(urls, out="data/qna/web_hr_qna_v3.jsonl"):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    seen, data = set(), []
    for url in tqdm(urls, desc="Scraping"):
        for qa in extract_qna(url):
            key = qa["question"].lower()
            if key not in seen:
                seen.add(key)
                data.append(qa)
    with open(out, "w", encoding="utf-8") as f:
        for qa in data:
            f.write(json.dumps(qa, ensure_ascii=False) + "\n")
    print(f"\n💾 {len(data)} Q&As saved → {out}")


if __name__ == "__main__":
    urls = [
        "https://www.eeoc.gov/youth/frequently-asked-questions#Q1",
        "https://www.dol.gov/agencies/whd/flsa/faq",
        "https://www.dol.gov/agencies/whd/fmla/faq",
    ]
    scrape_all(urls)
