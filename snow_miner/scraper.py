
import os
import re
import time
import pathlib
import urllib.parse
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://www.cairngormclub.org.uk/journals/search_the_journals.htm"
HEADERS = {"User-Agent": "cairngorm-snow-miner/1.0 (+https://example.local)"}

BASE_TEMPLATE = "https://www.cairngormclub.org.uk/journals/search_by_journal_year/search_journal_{:03d}.htm"
HEADERS = {"User-Agent": "cairngorm-snow-miner/1.0"}

def get_pdf_links():
    nums = range(116)  # 0–115 inclusive
    candidates = [BASE_TEMPLATE.format(i) for i in nums]
    pdf_links = []

    for url in tqdm(candidates):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            # Look for <a> with that button text
            link = soup.find("a", string=lambda s: s and "Download Complete Journal" in s)
            if link and link.get("href"):
                abs_url = requests.compat.urljoin(url, link["href"])
                pdf_links.append(abs_url)
        except requests.RequestException:
            continue

    print(pdf_links)
    return pdf_links

def download_pdfs(urls, dest_dir="data/pdfs", delay=0.5):
    os.makedirs(dest_dir, exist_ok=True)
    saved = []
    for url in tqdm(urls):
        fn = pathlib.Path(urllib.parse.urlparse(url).path).name
        if not fn.lower().endswith(".pdf"):
            fn += ".pdf"
        out = os.path.join(dest_dir, fn)
        if os.path.exists(out):
            saved.append(out)
            continue
        try:
            with requests.get(url, headers=HEADERS, timeout=90, stream=True) as r:
                r.raise_for_status()
                with open(out, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            saved.append(out)
            time.sleep(delay)
        except requests.RequestException:
            # skip failed downloads
            continue
    return saved
