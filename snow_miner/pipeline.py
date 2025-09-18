
import os
import csv
import regex as re
from typing import Dict, List, Tuple, Optional
from .scraper import get_pdf_links, download_pdfs
from .pdf_text import extract_text_pages
#from .entities import iter_sentences, find_entities_in_sentence, nearest_date
from .gpt_analyse import analyze_with_gpt
from .config import YEAR_REGEX

def detect_issue_from_filename(path: str) -> Optional[str]:
    issue = str(path.split("%")[4][2:])

    start_year = 1893 - 1
    year = start_year + int(issue)

    #return f"issue_{issue}_year_{year}"
    return f"issue_{issue}"


import os
import csv
from typing import Optional

def process_pdf(pdf_path: str, out_dir: str = "out", include_date_col: bool = True, overwrite: bool = False) -> Optional[str]:
    pages = extract_text_pages(pdf_path)
    if not pages:
        return None

    issue = detect_issue_from_filename(pdf_path)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{issue}.csv")

    # --- skip if already processed ---
    if not overwrite and os.path.exists(out_path):
        print(f"[skip] {out_path} already exists; skipping this journal.")
        return out_path  # or return None if you prefer a 'skipped' signal

    full_text = "\n\n".join(page_text for _, page_text in pages)

    # One call over the whole document (the analyzer will chunk internally as needed).
    rows = analyze_with_gpt(full_text)

    fieldnames = ["text", "entity", "score", "location"] + (["date"] if include_date_col else [])
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            row = {
                "text": r.get("text"),
                "entity": r.get("entity"),
                "score": int(r.get("score", 2)),
                "location": r.get("location"),
            }
            if include_date_col:
                row["date"] = r.get("date")  # gpt_analyse returns "date" (string or None)
            writer.writerow(row)

    return out_path


def process_all(pdf_dir: str = "data/pdfs", out_dir: str = "out", include_date_col: bool = True) -> List[str]:
    results = []
    for name in sorted(os.listdir(pdf_dir)):
        if name.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, name)
            out = process_pdf(pdf_path, out_dir=out_dir, include_date_col=include_date_col)
            if out:
                results.append(out)
    return results

def scrape_and_download(base_url: str = None, pdf_dir: str = "data/pdfs") -> List[str]:
    urls = get_pdf_links()
    return download_pdfs(urls, dest_dir=pdf_dir)
