
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


HEADERS = {"User-Agent": "cairngorm-snow-miner/1.0"}

def get_pdf_links():

    pdf_links = []

    for i in [f"{i:03d}" for i in range(1,117)]:
        pdf_links.append(f"http://www.cairngormclub.org.uk/journals/PDFs/Complete/The%20Cairngorm%20Club%20Journal%20{i}%20WM.pdf")

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
                    for chunk in r.iter_content(chunk_size=15000):
                        if chunk:
                            f.write(chunk)
            saved.append(out)
            time.sleep(delay)
        except requests.RequestException:
            # skip failed downloads
            continue

    return saved
