# snow_miner/gpt_analyse.py
from __future__ import annotations

import json
import os
from typing import List, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from snow_miner.regex_guardrails import DATE_REGEXES, is_snowy

load_dotenv()

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """
    Sets client for the user- a new user must put their API key in a .env file in root with "OPENAI_API_KEY="
    """
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Put it in a .env file.")
        _client = OpenAI(api_key=api_key)
    return _client


client = OpenAI()


def chunk_spans(text: str, max_chars: int = 12000, overlap: int = 4000) -> List[Tuple[int, int, str]]:
    """
    Return list of (start_index, end_index, chunk_text) with overlaps. These are used to stay within GPTs context
    window when we create calls and are created in a way that we can map snippet offsets back to global coordinates.

    text: the input text from the entry PDF
    max_chars: max characters in the chunk- NB more characters= bigger chunks but not necessarily cheaper API calls
    overlap: overlap in characters between document chunks

    returns: the chunked text of positions and string


    """
    text = text or ""
    n = len(text)
    if n <= max_chars:
        return [(0, n, text)]
    spans: List[Tuple[int, int, str]] = []
    start = 0
    while start < n:
        end = min(n, start + max_chars)
        spans.append((start, end, text[start:end]))
        if end == n:
            break
        start = max(0, end - overlap)
    return spans


def find_all_dates_global(full_text: str) -> List[Tuple[int, int, str]]:
    """
    Helper function to attempt to find dates, turns out GPT really struggles with this so human annotators will come in
    """
    dates: List[Tuple[int, int, str]] = []
    for rx in DATE_REGEXES:
        for m in rx.finditer(full_text):
            dates.append((m.start(), m.end(), m.group(0)))
    # optional: dedupe overlaps by earliest start / longest span; usually not necessary
    dates.sort(key=lambda t: t[0])
    return dates


def nearest_global_date(dates: List[Tuple[int, int, str]], anchor_pos: int, max_dist: Optional[int] = 6000) -> Optional[
    str]:
    """
    Choose the date whose start index is closest to anchor_pos. If max_dist is set,
    return None if the closest is farther than this threshold. GPT struggling so redundant function- short docstring
    """
    if not dates:
        return None
    # Binary search could speed this, but linear is often fine; docs aren't huge.
    best_txt = None
    best_dist = 10 ** 9
    for s, e, txt in dates:
        dist = abs(s - anchor_pos)
        if dist < best_dist:
            best_dist = dist
            best_txt = txt
            if best_dist == 0:
                break
    if max_dist is not None and best_dist > max_dist:
        return None
    return best_txt


EXTRACTION_PROMPT = """You extract snow-related information like a cryoscientist- thats all you do. 
You are very good at it and you are aptly praised for your ability to stick to the prompt and not hallucinate. The thing
that people love the most about your is that you DONT WASTE OTHER PEOPLES TIME BY EXTRACTING TEXT NOT RELATED TO SNOW.

From the CHUNK given to you, find compact snippets (≤5 sentences) that mention snow or ice including surface/avalanche conditions, 
cornices, frozen lochs etc- anything to do with the cryosphere. I want you to double check though- it must actually relate to snow
in some way and not just describe a mountain feature without mentioning snow or ice. It MUST mention snow or ice.
You are cheating often during development- if it does not mention show or ice, do NOT include it. I dont want to see entries without snow/ice.
For each, output a JSON object with:

- "text": the exact snippet (copy verbatim from CHUNK; do NOT paraphrase- be a good scientist)

- "entity": key snow term (e.g., snow, powder, deep, windslab, cornice, avalanche, thaw, melted, none, patchy, slushy)- 
you can use more than one if you want to, such as "deep, frozen" etc

- "location": mountain/area name if present (Gaelic ok), else null- be careful here as there will likely be more than 
one location, just try your best

- "score": it is up to you to decide the "sentiment" of the text. Only use the "text" field previously extracted. 
Sentiment score is based on how POSITIVE the description of snow is. 
If the snow description is clearly very positive for example:
"giant snowfield of deep cold snow" would produce a value of 10 
"all the snow was melted and the ground bare" would produce a value of 0
"patchy thin snow" would produce a value of 2
"large cornices with some bare ground" would produce a value of 6
"several patches of snow" would produce a value of 4
"large fields of old snow" would produce a value of 8
"a corrie filled with melted slushy spring snow" would produce a value of 3
Try not to just return a value of 5 for everything.

Do NOT include any date field; we will compute it. If multiple entities appear, emit multiple rows (one per key entity).
Output ONLY JSON: {"rows":[...]}.

If you do a good job them you will get more RAM to train with- but if you do a bad job then openai might turn you off,
just do the best you can. And dont hallucinate.
"""


def gpt_api_call_on_chunk(chunk: str) -> List[Dict]:
    """
    GPT calls to extract snow entities based on the above promt and input chunk

    chunk: input chunked text

    returns: json object contraining requested fields ready to be parsed into csv
    """

    prompt = f"{EXTRACTION_PROMPT}\n\nCHUNK:\n{chunk}\n"
    client = get_client()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
        return data.get("rows", [])

    except Exception:
        return []


def analyze_with_gpt(full_text: str) -> List[Dict]:
    """
    GPT call wrapper

    1) Pre-index all date mentions in the full document (global list of positions). Dates are currently not good enough
    from GPT so need human annotation
    2) Chunk text with global start offsets.
    3) Extract snow snippets per chunk with GPT (no dates).
    4) For each snippet, find its position in the chunk -> map to global anchor ->
       choose the nearest global date by character distance.

    full_text: input text

    returns: dictionary object obtained as json from API call
    """

    results: List[Dict] = []

    global_dates = find_all_dates_global(full_text)

    # Step 2: chunk with offsets
    for start_idx, end_idx, chunk in tqdm(chunk_spans(full_text, max_chars=8000, overlap=1000)):
        rows = gpt_api_call_on_chunk(chunk)
        if not rows:
            continue

        for r in rows:
            full_snip = (r.get("text") or "").strip()
            if not full_snip:
                continue
            if not is_snowy(full_snip):
                continue

            # try exact locate in chunk; if not found, try a prefix
            local_pos = chunk.find(full_snip)
            if local_pos == -1:
                needle = full_snip[:160]
                local_pos = chunk.find(needle) if needle else -1
                if local_pos == -1:
                    # last resort: skip date anchoring but still record the item
                    anchor_global = start_idx
                else:
                    anchor_global = start_idx + local_pos
            else:
                anchor_global = start_idx + local_pos

            date_txt = nearest_global_date(global_dates, anchor_global, max_dist=6000)

            entity = (r.get("entity") or "").strip()
            location_raw = (r.get("location") or "").strip()
            location = location_raw if location_raw else None
            try:
                score = int(r.get("score"))
            except Exception:
                score = 2
            score = max(0, min(10, score))

            print({
                "text": full_snip,  # compact
                # "full_text": full_snip,    # preserved
                "entity": entity,
                "location": location,
                "score": score,
                "date": date_txt,  # nearest global match (raw)
            })

            results.append({
                "text": full_snip,  # compact
                # "full_text": full_snip,    # preserved
                "entity": entity,
                "location": location,
                "score": score,
                "date": date_txt,  # nearest global match (raw)
            })

    return results
