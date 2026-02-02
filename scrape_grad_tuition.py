import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.iit.edu/student-accounting/tuition-and-fees/future-tuition-and-fees/mies-campus-graduate"

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def collect_text_until_next_header(start_tag, stop_names={"h2"}):
    """
    Collect raw text nodes after a header until the next header in stop_names.
    This is robust for IIT pages where data is rendered as plain text nodes.
    """
    out = []
    for el in start_tag.next_elements:
        if getattr(el, "name", None) in stop_names:
            break
        if isinstance(el, str):
            t = norm(el)
            if not t:
                continue
            # filter tiny junk tokens
            if t in {"»", "|"}:
                continue
            out.append(t)

    # de-dup preserving order
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

# We'll capture these main buckets from this page:
# - Tuition Rates 2025–2026 (h2)
# - Other Fees (h2)
sections = {}

# capture h2 sections first
for h2 in root.find_all("h2"):
    title = norm(h2.get_text(" ", strip=True))
    if title in {"Tuition Rates 2025–2026", "Other Fees"}:
        sections[title] = collect_text_until_next_header(h2, stop_names={"h2"})

# additionally, the "Per Semester" and "Per Year" blocks are h3 on this page
# and sit inside the Tuition Rates section.
subsections = {}
for h3 in root.find_all("h3"):
    title = norm(h3.get_text(" ", strip=True))
    if title in {"Per Semester", "Per Year (billed during the fall semester)"}:
        subsections[title] = collect_text_until_next_header(h3, stop_names={"h2", "h3"})

data = {
    "source_url": URL,
    "page_title": norm((root.find("h1") or soup.find("title")).get_text(" ", strip=True)),
    "sections": sections,
    "subsections": subsections,
}

print("Captured sections:", {k: len(v) for k, v in sections.items()})
print("Captured subsections:", {k: len(v) for k, v in subsections.items()})

with open("iit_mies_grad_tuition_fees.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Saved: iit_mies_grad_tuition_fees.json")

