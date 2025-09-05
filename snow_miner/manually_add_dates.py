import tkinter as tk
from tkinter import messagebox
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import io
from collections import defaultdict


class SnippetAnnotator:
    def __init__(self, master, csv_path, pdf_path,
                 text_col="text", date_col="date",
                 location_col="location", comment_col="annotator_comment"):
        self.master = master
        self.csv_path = csv_path
        self.pdf_path = pdf_path
        self.text_col = text_col
        self.date_col = date_col
        self.location_col = location_col
        self.comment_col = comment_col  # NEW: annotator comment

        self.df = pd.read_csv(csv_path)

        # ensure needed columns exist and are string dtype
        for col in [self.date_col, self.location_col, self.comment_col]:
            if col not in self.df.columns:
                self.df[col] = ""
            self.df[col] = self.df[col].astype(str)

        self.doc = fitz.open(pdf_path)
        self.current_idx = 0

        # --- UI Layout ---
        self.frame = tk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # scrollable canvas
        self.canvas = tk.Canvas(self.frame, bg="black", highlightthickness=0)
        self.scroll_y = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scroll_x = tk.Scrollbar(self.frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)

        self.scroll_y.pack(side="right", fill="y")
        self.scroll_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        # mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)   # Windows/macOS
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)     # Linux up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)     # Linux down

        self.info_label = tk.Label(master, text="", wraplength=1000, justify="left")
        self.info_label.pack()

        # Date Entry
        date_frame = tk.Frame(master)
        date_frame.pack(pady=2, fill="x")
        tk.Label(date_frame, text="Date:").pack(side="left")
        self.entry_date = tk.Entry(date_frame, width=40)
        self.entry_date.pack(side="left")

        # Location Entry
        loc_frame = tk.Frame(master)
        loc_frame.pack(pady=2, fill="x")
        tk.Label(loc_frame, text="Location:").pack(side="left")
        self.entry_location = tk.Entry(loc_frame, width=40)
        self.entry_location.pack(side="left")

        # NEW: Annotator Comment (multi-line)
        com_frame = tk.Frame(master)
        com_frame.pack(pady=4, fill="both", expand=False)
        tk.Label(com_frame, text="Annotator comment:").pack(anchor="w")
        self.text_comment = tk.Text(com_frame, height=4, width=80, wrap="word")
        self.text_comment.pack(fill="x")

        # Buttons
        btn_frame = tk.Frame(master)
        btn_frame.pack(pady=4)
        tk.Button(btn_frame, text="Save", command=self.save_values).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Skip", command=self.next_snippet).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Reject suggestion", command=self.reject_snippet).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Quit", command=self.quit_app).grid(row=0, column=3, padx=5)

        self.images = []       # keep Tk image refs
        self.page_offsets = [] # y-offset for each page in the scroll canvas

        # Precompute all highlights once
        self.page_highlights = defaultdict(list)  # page_num -> list[fitz.Rect]
        self.snippet_target_page = {}             # row_idx  -> page_num (or None)
        self._precompute_all_highlights()

        # Render once with ALL highlights baked on the previews
        self.show_pdf_pages(highlights=self.page_highlights)

        # Now just scroll to each snippet (no re-render needed)
        self.show_snippet()

    def reject_snippet(self):
        """Remove the current row from the dataframe and advance."""
        if len(self.df) == 0:
            return

        # Drop current row and reindex
        self.df = self.df.drop(self.df.index[self.current_idx]).reset_index(drop=True)

        # Keep precomputed mapping consistent
        if hasattr(self, "snippet_target_page") and isinstance(self.snippet_target_page, dict):
            new_map = {}
            for k, v in self.snippet_target_page.items():
                if k == self.current_idx:
                    continue  # remove this row's mapping
                new_k = k if k < self.current_idx else k - 1
                new_map[new_k] = v
            self.snippet_target_page = new_map

        # Adjust index and continue
        if self.current_idx >= len(self.df):
            if len(self.df) == 0:
                messagebox.showinfo("Done", "All snippets processed!")
                self.quit_app()
                return
            self.current_idx = len(self.df) - 1

        self.show_snippet()

    def _precompute_all_highlights(self):
        for idx, row in self.df.iterrows():
            snippet = str(row[self.text_col]) if pd.notna(row[self.text_col]) else ""
            snippet = snippet.strip()
            if not snippet:
                self.snippet_target_page[idx] = None
                continue

            found_page = None
            rects_for_page = None
            for page_num, page in enumerate(self.doc):
                rects = page.search_for(snippet)
                if not rects and len(snippet) > 120:
                    rects = page.search_for(snippet[:120])
                if rects:
                    found_page = page_num
                    rects_for_page = rects
                    break

            self.snippet_target_page[idx] = found_page
            if found_page is not None and rects_for_page:
                self.page_highlights[found_page].extend(rects_for_page)

    # ---------- rendering ----------
    def render_page_image(self, page_num, highlight_rects=None, zoom=1.5):
        page = self.doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

        if highlight_rects:
            draw = ImageDraw.Draw(img)
            for rect in highlight_rects:
                r = [int(rect.x0 * zoom), int(rect.y0 * zoom),
                     int(rect.x1 * zoom), int(rect.y1 * zoom)]
                draw.rectangle(r, outline="red", width=2)

        return img

    def show_pdf_pages(self, highlights=None):
        self.canvas.delete("all")
        self.images.clear()
        self.page_offsets.clear()

        y = 0
        for i in range(len(self.doc)):
            highlight_rects = highlights.get(i, []) if highlights else []
            img = self.render_page_image(i, highlight_rects, zoom=1.5)
            tk_img = ImageTk.PhotoImage(img)
            self.images.append(tk_img)
            x = max(0, (self.canvas.winfo_width() - tk_img.width()) // 2)
            self.canvas.create_image(x, y, anchor="nw", image=tk_img)
            self.page_offsets.append(y)
            y += tk_img.height()

        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    # ---------- interaction ----------
    def show_snippet(self):
        if self.current_idx >= len(self.df):
            messagebox.showinfo("Done", "All snippets processed!")
            self.quit_app()
            return

        row = self.df.iloc[self.current_idx]
        snippet = str(row[self.text_col]) if pd.notna(row[self.text_col]) else ""
        snippet = snippet.strip()

        target_page = self.snippet_target_page.get(self.current_idx, None)
        if target_page is not None:
            target_y = self.page_offsets[target_page]
            total_h = max(1, self.canvas.bbox("all")[3])
            self.canvas.yview_moveto(target_y / total_h)
            status = f"✅ Found on page {target_page+1}"
        else:
            status = "❌ Not found"

        self.info_label.config(
            text=f"[{self.current_idx+1}/{len(self.df)}] Snippet:\n{(snippet[:500] + '...') if len(snippet)>500 else snippet}\n\n{status}"
        )

        # Fill input widgets
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, str(row[self.date_col]) if row[self.date_col] else "")

        self.entry_location.delete(0, tk.END)
        self.entry_location.insert(0, str(row[self.location_col]) if row[self.location_col] else "")

        self.text_comment.delete("1.0", tk.END)
        self.text_comment.insert("1.0", str(row[self.comment_col]) if row[self.comment_col] else "")

    def save_values(self):
        date_val = self.entry_date.get().strip()
        loc_val = self.entry_location.get().strip()
        com_val = self.text_comment.get("1.0", "end").strip()  # NEW: read multi-line text
        self.df.at[self.current_idx, self.date_col] = date_val
        self.df.at[self.current_idx, self.location_col] = loc_val
        self.df.at[self.current_idx, self.comment_col] = com_val
        self.next_snippet()

    def next_snippet(self):
        self.current_idx += 1
        self.show_snippet()

    def quit_app(self):
        out_csv = self.csv_path.replace(".csv", "_dated.csv")
        self.df.to_csv(out_csv, index=False)
        self.doc.close()
        self.master.destroy()
        print(f"Saved {out_csv}")

    # ---------- scrolling ----------
    def _on_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            steps = -int(event.delta / 120) if event.delta else 0
            if steps == 0:
                steps = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(steps * 3, "units")


if __name__ == "__main__":
    # Hardcode file paths here
    csv_file = r"C:\Projects\cairngorm-snow-miner\scripts\out\issue_001_year_1893.csv"
    pdf_file = r"C:\Projects\cairngorm-snow-miner\scripts\data\pdfs\The%20Cairngorm%20Club%20Journal%20001%20WM.pdf"

    root = tk.Tk()
    root.title("Snippet Annotator")
    app = SnippetAnnotator(root, csv_file, pdf_file)
    root.mainloop()


