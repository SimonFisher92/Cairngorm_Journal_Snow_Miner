from pathlib import Path

def rename_pdfs_sequential(pdf_dir: Path, expected_issues: int = 115):
    """
    Rename PDFs in pdf_dir to issue_001.pdf .. issue_{expected_issues}.pdf
    Asserts that no issues are missing.
    """

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if len(pdf_files) != expected_issues:
        raise AssertionError(
            f"Expected {expected_issues} PDFs, found {len(pdf_files)} in {pdf_dir}"
        )

    for idx, pdf_file in enumerate(pdf_files, start=1):
        issue = str(idx).zfill(3)
        new_name = f"issue_{issue}.pdf"
        new_path = pdf_file.with_name(new_name)

        if new_path.exists() and new_path != pdf_file:
            raise FileExistsError(f"Target file {new_path} already exists.")

        print(f"Renaming {pdf_file.name} → {new_name}")
        pdf_file.rename(new_path)

    # Final verification
    renamed = sorted(pdf_dir.glob("issue_*.pdf"))
    expected = [pdf_dir / f"issue_{str(i).zfill(3)}.pdf" for i in range(1, expected_issues + 1)]
    if renamed != expected:
        raise AssertionError("Renamed set does not exactly match expected issue sequence.")

    print("✅ All PDFs successfully renamed and sequence verified.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Rename PDFs to sequential issue_xxx.pdf")
    parser.add_argument("--pdf_dir", type=Path, help="Directory containing PDFs")
    parser.add_argument("--expected", type=int, default=115, help="Number of expected issues")

    args = parser.parse_args()
    rename_pdfs_sequential(args.pdf_dir, expected_issues=args.expected)
