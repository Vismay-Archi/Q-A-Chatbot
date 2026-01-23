import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.iit.edu/registrar/academic-calendar"

TERM_RE = re.compile(r"^(Spring|Summer|Fall|Winter)\s+20\d{2}\b", re.I)

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

resp = requests.get(
    URL,
    headers={"User-Agent": "Mozilla/5.0 (academic project scraper)"},
    timeout=30,
)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "lxml")

# Narrow to main content so we don't accidentally grab menus/footers
root = soup.find("main") or soup

# Find any header tags that look like term titles
term_headers = []
for tag_name in ("h2", "h3", "h4"):
    for h in root.find_all(tag_name):
        txt = normalize_ws(h.get_text(" ", strip=True))
        if TERM_RE.match(txt):
            term_headers.append(h)

results = []

for h in term_headers:
    term = normalize_ws(h.get_text(" ", strip=True))
    items = []

    # Walk forward in document order until the next term header
    for el in h.find_all_next():
        if el is h:
            continue

        # Stop at the next term header
        if el.name in {"h2", "h3", "h4"}:
            next_txt = normalize_ws(el.get_text(" ", strip=True))
            if TERM_RE.match(next_txt):
                break

        # Pull table rows: usually Date | Event
        if el.name == "table":
            for tr in el.find_all("tr"):
                cells = [normalize_ws(td.get_text(" ", strip=True)) for td in tr.find_all(["th", "td"])]
                if len(cells) >= 2:
                    date_text, event_text = cells[0], cells[1]
                    # skip header row
                    if date_text.lower() == "date" and event_text.lower() == "event":
                        continue
                    if date_text and event_text:
                        items.append({"date": date_text, "event": event_text, "source": "table"})

        # Also capture list items / paragraphs that sometimes contain date+event
        if el.name in {"li", "p"}:
            text = normalize_ws(el.get_text(" ", strip=True))
            # keep only lines that look date-ish to avoid grabbing random page text
            if re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b\s+\d{1,2}", 
text):
                items.append({"date": None, "event": text, "source": el.name})

    if items:
        results.append({"term": term, "items": items})

print("TERMS FOUND:", len(results))
for block in results[:3]:
    print(block["term"], "items:", len(block["items"]))

with open("iit_academic_calendar.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Saved: iit_academic_calendar.json")

