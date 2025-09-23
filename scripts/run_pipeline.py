
import argparse

from dotenv import load_dotenv

from snow_miner.pipeline import scrape_and_download, process_all

load_dotenv()

def main():

    """
    Wrapper script with three options. Please do not spam to cairngorm club servers unless you need to- PDFs can be obtained from huggingface

    --all - both scrape and mine pdfs (new users)
    --scrape-only - only download pdfs
    --process-only - only create GPT API calls for extracting snow data

    By design, any GPT calls require a .env file containing your API key from GPT (obviously not provided in this codebase :) )

    """

    ap = argparse.ArgumentParser(description="Cairngorm Snow Miner")
    ap.add_argument("--all", action="store_true", help="Scrape, download, and process PDFs")
    ap.add_argument("--scrape-only", action="store_true", help="Only scrape/download PDFs")
    ap.add_argument("--process-only", action="store_true", help="Only process already-downloaded PDFs")
    ap.add_argument("--base-url", type=str, default="https://www.cairngormclub.org.uk/journals/search_the_journals.htm", help="Base URL to scrape")
    ap.add_argument("--pdf-dir", type=str, default="C:\Projects\cairngorm-snow-miner\scripts\data\pdfs", help="Directory to store PDFs")
    ap.add_argument("--out-dir", type=str, default="out", help="Directory for CSV outputs")
    ap.add_argument("--no-date-column", action="store_true", help="Omit the 'date' column in CSVs")

    args = ap.parse_args()

    if args.all:
        saved = scrape_and_download(base_url=args.base_url, pdf_dir=args.pdf_dir)
        print(f"Downloaded/kept {len(saved)} PDFs in {args.pdf_dir}")
        outs = process_all(pdf_dir=args.pdf_dir, out_dir=args.out_dir, include_date_col=not args.no_date_column)
        print(f"Wrote {len(outs)} CSVs to {args.out_dir}")
        return

    if args.scrape_only:
        saved = scrape_and_download(base_url=args.base_url, pdf_dir=args.pdf_dir)
        print(f"Downloaded/kept {len(saved)} PDFs in {args.pdf_dir}")
        return

    if args.process_only:
        outs = process_all(pdf_dir=args.pdf_dir, out_dir=args.out_dir, include_date_col=not args.no_date_column)
        print(f"Wrote {len(outs)} CSVs to {args.out_dir}")
        return

    ap.print_help()

if __name__ == "__main__":
    main()
