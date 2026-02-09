import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.iit.edu/student-accounting/tuition-and-fees/future-tuition-and-fees/mies-campus-undergraduate"

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def collect_text_until_next_h2(h2_tag):
    """Collect plain text nodes after this h2 until the next h2."""
    out = []
    for el in h2_tag.next_elements:
        # Stop when we hit the next section header
        if getattr(el, "name", None) == "h2":
            break

        # Grab raw text nodes (this is what your previous version missed)
        if isinstance(el, str):
            t = norm(el)
            if not t:
                continue
            # Filter obvious junk
            if t in {"»", "|"}:
                continue
            out.append(t)

    # De-dup while preserving order
    seen = set()
    cleaned = []
    for x in out:
        if x not in seen:
            seen.add(x)
            cleaned.append(x)
    return cleaned

resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (academic project scraper)"}, timeout=30)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "lxml")

root = soup.find("main") or soup

targets = {"Tuition Rates 2025–2026", "Mandatory Fees", "Other Fees"}
sections = {}

for h2 in root.find_all("h2"):
    title = norm(h2.get_text(" ", strip=True))
    if title in targets:
        sections[title] = collect_text_until_next_h2(h2)

data = {
    "source_url": URL,
    "page_title": norm((root.find("h1") or soup.find("title")).get_text(" ", strip=True)),
    "sections": sections,
}

print("Sections captured:", list(sections.keys()))
for k, v in sections.items():
    print(f"- {k}: {len(v)} text items")
    print("  sample:", v[:8])

with open("iit_mies_ug_tuition_fees.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Saved: iit_mies_ug_tuition_fees.json")

