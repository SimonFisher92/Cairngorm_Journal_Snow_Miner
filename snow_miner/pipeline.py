import csv
import os
from typing import List
from typing import Optional

from .gpt_analyse import analyze_with_gpt
from .pdf_text import extract_text_pages
from .scraper import get_pdf_links, download_pdfs


def detect_issue_from_filename(path: str) -> Optional[str]:
    issue = str(path.split("%")[4][2:])

    return f"issue_{issue}"


def process_pdf(pdf_path: str, out_dir: str = "out", include_date_col: bool = True, overwrite: bool = False) -> Optional[str]:

    """
    Main function to process a pdf document and extract snow entities using GPT. Initially by page, but context awareness improved
    by doing wider chunking (currently buried in 'analyse_with_gpt')

    pdf-Path: path to input pdf
    out-dir: path to write out csv
    include_date_col: optionally include buggy dates from GPT
    overwrite: optionally overwrite previous outputs
    """


    pages = extract_text_pages(pdf_path)
    if not pages:
        return None

    issue = detect_issue_from_filename(pdf_path)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{issue}.csv")

    if not overwrite and os.path.exists(out_path):
        print(f"[skip] {out_path} already exists; skipping this journal.")
        return out_path  # or return None if you prefer a 'skipped' signal

    full_text = "\n\n".join(page_text for _, page_text in pages)

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

def scrape_and_download(pdf_dir: str = "data/pdfs") -> List[str]:
    urls = get_pdf_links()
    return download_pdfs(urls, dest_dir=pdf_dir)
