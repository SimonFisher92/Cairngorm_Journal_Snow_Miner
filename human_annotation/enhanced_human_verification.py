import tkinter as tk
from tkinter import messagebox
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageDraw
import io
from collections import defaultdict
import re
import unicodedata


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
        self.comment_col = comment_col  # annotator comment

        self.df = pd.read_csv(csv_path)

        # ensure needed columns exist and are string dtype
        for col in [self.date_col, self.location_col, self.comment_col]:
            if col not in self.df.columns:
                self.df[col] = ""
            self.df[col] = self.df[col].astype(str)

        self.doc = fitz.open(pdf_path)
        self.current_idx = 0

        # keep the render zoom consistent across methods
        self.render_zoom = 1.5

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

        # Snippet info + Jump buttons
        info_row = tk.Frame(master)
        info_row.pack(fill="x", pady=(4, 0))
        self.info_label = tk.Label(info_row, text="", wraplength=1000, justify="left", anchor="w")
        self.info_label.pack(side="left", fill="x", expand=True)
        tk.Button(info_row, text="Jump to highlight", command=self.jump_to_highlight)\
            .pack(side="right", padx=6)
        tk.Button(info_row, text="Enhanced jump", command=self.enhanced_jump_to_highlight)\
            .pack(side="right", padx=6)

        # --- Edit text hallucination (above Date row) ---
        edit_frame = tk.Frame(master)
        edit_frame.pack(pady=(6, 2), fill="x")
        tk.Label(edit_frame, text="Edit text hallucination (optional):").pack(anchor="w")
        self.entry_edit_text = tk.Text(edit_frame, height=3, width=100, wrap="word")
        self.entry_edit_text.pack(fill="x")
        tk.Button(edit_frame, text="Apply edit to snippet", command=self.apply_text_edit)\
            .pack(anchor="e", pady=(4, 0))

        # Date Entry
        date_frame = tk.Frame(master)
        date_frame.pack(pady=2, fill="x")
        tk.Label(date_frame, text="Date:").pack(side="left")
        self.entry_date = tk.Entry(date_frame, width=40)
        self.entry_date.pack(side="left")
        tk.Button(date_frame, text="⟲ Same as previous", command=self.fill_prev_date)\
            .pack(side="left", padx=6)

        # Location Entry
        loc_frame = tk.Frame(master)
        loc_frame.pack(pady=2, fill="x")
        tk.Label(loc_frame, text="Location:").pack(side="left")
        self.entry_location = tk.Entry(loc_frame, width=40)
        self.entry_location.pack(side="left")
        tk.Button(loc_frame, text="⟲ Same as previous", command=self.fill_prev_location)\
            .pack(side="left", padx=6)

        # Annotator Comment (multi-line)
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

        self.images = []         # keep Tk image refs
        self.page_offsets = []   # y-offset for each page in the scroll canvas
        self.page_x_offsets = [] # x-offset for each page image (for overlays)

        # Precompute all highlights once
        self.page_highlights = defaultdict(list)  # page_num -> list[fitz.Rect]
        self.snippet_target_page = {}             # row_idx  -> page_num (or None)
        self._precompute_all_highlights()

        # Render once with ALL highlights baked on the previews
        self.show_pdf_pages(highlights=self.page_highlights)

        # Now just scroll to each snippet (no re-render needed)
        self.show_snippet()

    # ---------- text normalization & shards ----------
    _WORD_RE = re.compile(r"[A-Za-z0-9'’-]+")

    def _norm(self, s: str) -> str:
        s = unicodedata.normalize("NFKC", s or "")
        s = s.replace("\u00AD", "")                      # soft hyphen
        s = re.sub(r"[\u2010-\u2015]", "-", s)          # en/em dashes -> '-'
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _tok(self, s: str):
        return [w.strip("’'") for w in self._WORD_RE.findall(s.lower())]

    def _page_shard_search(self, page, snippet: str,
                           max_words: int = 8, min_words: int = 3) -> list:
        """
        Exact search, then descending n-gram shards (8->3 words), then a prefix fallback.
        Returns list[fitz.Rect].
        """
        if not snippet:
            return []
        s = self._norm(snippet)

        # 1) exact
        rects = list(page.search_for(s))
        if rects:
            return rects

        # 2) n-gram shards
        toks = self._tok(s)
        found = []
        for size in range(min(max_words, len(toks)), min_words - 1, -1):
            for i in range(0, len(toks) - size + 1):
                shard = " ".join(toks[i:i + size])
                hits = list(page.search_for(shard))
                if hits:
                    found.extend(hits)
        if found:
            return found

        # 3) prefix fallback
        return list(page.search_for(s[:120])) if len(s) > 0 else []

    # ---------- overlay drawer (ENHANCED ONLY) ----------
    def _draw_enhanced_highlights(self, rects, page_idx):
        """Overlay blue rectangles for Enhanced matches only."""
        # clear previous enhanced overlays
        self.canvas.delete("bluehl")
        if not rects or page_idx is None:
            return
        if page_idx < 0 or page_idx >= len(self.page_offsets):
            return

        z = self.render_zoom
        x_off = self.page_x_offsets[page_idx] if page_idx < len(self.page_x_offsets) else 0
        y_off = self.page_offsets[page_idx]

        for r in rects:
            x0 = x_off + r.x0 * z
            y0 = y_off + r.y0 * z
            x1 = x_off + r.x1 * z
            y1 = y_off + r.y1 * z
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="blue", width=2, tags="bluehl")

    # ---------- helpers for "same as previous" ----------
    def _get_prev_value(self, col_name: str) -> str:
        """Return previous row's value for a given column, or empty string if none."""
        prev_idx = self.current_idx - 1
        if prev_idx < 0 or prev_idx >= len(self.df):
            return ""
        val = self.df.iloc[prev_idx].get(col_name, "")
        return "" if pd.isna(val) else str(val)

    def fill_prev_date(self):
        prev = self._get_prev_value(self.date_col)
        self.entry_date.delete(0, tk.END)
        if prev:
            self.entry_date.insert(0, prev)

    def fill_prev_location(self):
        prev = self._get_prev_value(self.location_col)
        self.entry_location.delete(0, tk.END)
        if prev:
            self.entry_location.insert(0, prev)

    # ---------- row management ----------
    def reject_snippet(self):
        if len(self.df) == 0:
            return

        self.df = self.df.drop(self.df.index[self.current_idx]).reset_index(drop=True)

        if hasattr(self, "snippet_target_page") and isinstance(self.snippet_target_page, dict):
            new_map = {}
            for k, v in self.snippet_target_page.items():
                if k == self.current_idx:
                    continue
                new_k = k if k < self.current_idx else k - 1
                new_map[new_k] = v
            self.snippet_target_page = new_map

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
    def render_page_image(self, page_num, highlight_rects=None, zoom=None):
        page = self.doc[page_num]
        if zoom is None:
            zoom = self.render_zoom
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
        self.page_x_offsets.clear()          # track x offsets for overlays
        self.canvas.delete("bluehl")         # clear any old enhanced overlays

        y = 0
        for i in range(len(self.doc)):
            highlight_rects = highlights.get(i, []) if highlights else []
            img = self.render_page_image(i, highlight_rects, zoom=self.render_zoom)
            tk_img = ImageTk.PhotoImage(img)
            self.images.append(tk_img)
            x = max(0, (self.canvas.winfo_width() - tk_img.width()) // 2)
            self.canvas.create_image(x, y, anchor="nw", image=tk_img)
            self.page_offsets.append(y)
            self.page_x_offsets.append(x)
            y += tk_img.height()

        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    # ---------- interaction ----------
    def show_snippet(self):
        if self.current_idx >= len(self.df):
            messagebox.showinfo("Done", "All snippets processed!")
            self.quit_app()
            return

        # Clear enhanced overlays when switching rows
        self.canvas.delete("bluehl")

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

        # keep the edit box EMPTY (do not prefill)
        self.entry_edit_text.delete("1.0", tk.END)

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

    def apply_text_edit(self):
        """Apply human-edited snippet text to the current row and re-locate its highlight/page."""
        if self.current_idx >= len(self.df):
            return
        new_text = self.entry_edit_text.get("1.0", "end").strip()
        if not new_text:
            messagebox.showwarning("Empty text", "Please enter some text before applying the edit.")
            return

        self.df.at[self.current_idx, self.text_col] = new_text

        found_page = None
        rects_for_page = None
        for page_num, page in enumerate(self.doc):
            rects = page.search_for(new_text)
            if not rects and len(new_text) > 120:
                rects = page.search_for(new_text[:120])
            if rects:
                found_page = page_num
                rects_for_page = rects
                break

        self.snippet_target_page[self.current_idx] = found_page
        if found_page is not None and rects_for_page:
            self.page_highlights[found_page].extend(rects_for_page)

        self.info_label.config(
            text=f"[{self.current_idx+1}/{len(self.df)}] Snippet (edited):\n"
                 f"{(new_text[:500] + '...') if len(new_text)>500 else new_text}\n\n"
                 f"{'✅ Found on page ' + str(found_page+1) if found_page is not None else '❌ Not found'}"
        )
        if found_page is not None:
            first = rects_for_page[0]
            y_on_page = first.y0 * self.render_zoom
            target_y = self.page_offsets[found_page] + y_on_page - 80
            bbox = self.canvas.bbox("all")
            if bbox:
                total_h = max(1, bbox[3])
                target_y = max(0, min(target_y, total_h - 1))
                self.canvas.yview_moveto(target_y / total_h)

    def jump_to_highlight(self):
        """Re-center the canvas on this snippet's highlight (exact/prefix only)."""
        if self.current_idx >= len(self.df):
            return

        # Clear enhanced overlays (this is the non-enhanced path)
        self.canvas.delete("bluehl")

        snippet = (str(self.df.iloc[self.current_idx][self.text_col]) or "").strip()
        page_idx = self.snippet_target_page.get(self.current_idx, None)

        if page_idx is None:
            messagebox.showinfo(
                "Not found",
                "This is likely due to parsing issues. Try 'Enhanced jump'."
            )
            return

        page = self.doc[page_idx]
        rects = page.search_for(snippet) if snippet else []
        if not rects and snippet and len(snippet) > 120:
            rects = page.search_for(snippet[:120])

        if rects:
            first = rects[0]
            y_on_page = first.y0 * self.render_zoom
            target_y = self.page_offsets[page_idx] + y_on_page - 80
        else:
            target_y = self.page_offsets[page_idx]

        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        total_h = max(1, bbox[3])
        target_y = max(0, min(target_y, total_h - 1))
        self.canvas.yview_moveto(target_y / total_h)

    def enhanced_jump_to_highlight(self):
        """
        Enhanced jump:
        - Chunk the snippet into word n-grams and try to match any shard.
        - Search the 'known' page if we have one, plus neighbours (for two-page spans).
          If unknown, scan all pages and pick the page with most matches.
        - Draw BLUE overlays for these enhanced matches.
        """
        if self.current_idx >= len(self.df):
            return

        snippet = (str(self.df.iloc[self.current_idx][self.text_col]) or "").strip()
        if not snippet:
            return

        known_idx = self.snippet_target_page.get(self.current_idx, None)

        # Build candidate page list
        if known_idx is None:
            candidates = list(range(len(self.doc)))
        else:
            candidates = sorted(set([
                max(0, known_idx - 1), known_idx, min(len(self.doc) - 1, known_idx + 1)
            ]))

        best_page = None
        best_rects = []
        for p in candidates:
            page = self.doc[p]
            rects = self._page_shard_search(page, snippet, max_words=8, min_words=3)
            if len(rects) > len(best_rects):
                best_rects = rects
                best_page = p
            # fast path: strong evidence if we found many rects on a page
            if len(best_rects) >= 3 and known_idx is not None:
                break

        if not best_rects:
            messagebox.showinfo(
                "Not found",
                "No highlight recorded for this snippet (enhanced).\n\n"
                "There are two reasons for this:\n\n"
                "• The snippet spans two pages.\n"
                "• GPT hallucinated one or two words (rare, <5%). "
                "Use the 'Edit text hallucination' box to correct it, then click "
                "'Apply edit to snippet' and try again."
            )
            return

        # Update mapping to the newly inferred best page
        if best_page is not None:
            self.snippet_target_page[self.current_idx] = best_page

        # Center to topmost rect from best page
        first = sorted(best_rects, key=lambda r: (r.y0, r.x0))[0]
        y_on_page = first.y0 * self.render_zoom
        target_y = self.page_offsets[best_page] + y_on_page - 80

        # Draw BLUE overlays for enhanced matches
        self._draw_enhanced_highlights(best_rects, best_page)

        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        total_h = max(1, bbox[3])
        target_y = max(0, min(target_y, total_h - 1))
        self.canvas.yview_moveto(target_y / total_h)

    def save_values(self):
        date_val = self.entry_date.get().strip()
        loc_val = self.entry_location.get().strip()
        com_val = self.text_comment.get("1.0", "end").strip()
        self.df.at[self.current_idx, self.date_col] = date_val
        self.df.at[self.current_idx, self.location_col] = loc_val
        self.df.at[self.current_idx, self.comment_col] = com_val
        self.next_snippet()

    def next_snippet(self):
        self.current_idx += 1
        self.show_snippet()

    def quit_app(self):
        out_csv = self.csv_path.replace("out", "hand_curated")
        #out_csv = "../scripts/hand_curated"
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
    issue = '002'
    csv_file = rf"../scripts/out/issue_{issue}.csv"
    pdf_file = rf"../scripts/data/pdfs/The%20Cairngorm%20Club%20Journal%20{issue}%20WM.pdf"

    root = tk.Tk()
    root.title("Snippet Annotator")
    app = SnippetAnnotator(root, csv_file, pdf_file)
    root.mainloop()
