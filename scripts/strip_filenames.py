from pathlib import Path

def strip_year_and_after(dir_path, rename=False):
    for p in Path(dir_path).glob("*.csv"):
        stem = p.stem  # filename without .csv
        pos = stem.find("_year")
        if pos == -1:
            continue  # nothing to strip

        new_stem = stem[:pos]  # drop "_year" and everything after
        if not new_stem:       # avoid renaming to ".csv"
            print(f"SKIP (empty name): {p.name}")
            continue

        new_name = new_stem + ".csv"
        if new_name == p.name:
            continue  # already clean

        dest = p.with_name(new_name)
        if dest.exists():
            print(f"SKIP (exists): {p.name} -> {new_name}")
            continue

        print(f"{p.name} -> {new_name}")
        if rename:
            p.rename(dest)

if __name__ == "__main__":
    folder = r'C:\Projects\cairngorm-snow-miner\scripts\out'
    strip_year_and_after(folder, rename=True)
