
from pdfminer.high_level import extract_text
from typing import List, Tuple

def extract_text_pages(pdf_path: str) -> List[Tuple[int, str]]:
    """
    Return a list of (page_number (1-based), text) tuples.
    """
    full_text = extract_text(pdf_path) or ""
    # pdfminer doesn't split pages by default here; in many PDFs it inserts form feed \x0c between pages.
    # We'll split on \x0c to approximate page boundaries.
    pages = [p for p in full_text.split("\x0c") if p is not None]
    out = []
    for idx, page_text in enumerate(pages, start=1):
        if page_text and page_text.strip():
            out.append((idx, page_text))
    if not out and full_text.strip():
        out.append((1, full_text))
    return out
