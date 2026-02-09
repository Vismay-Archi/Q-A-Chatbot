import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.iit.edu/registrar/people"

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def is_phone(s: str) -> bool:
    return bool(re.fullmatch(r"\d{3}\.\d{3}\.\d{4}", s))

def is_email(s: str) -> bool:
    return "@" in s and "." in s and " " not in s

resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (academic project scraper)"}, timeout=30)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "lxml")

main = soup.find("main") or soup

# The page contains the section "Office of the Registrar Staff"
section_h2 = None
for h2 in main.find_all("h2"):
    if "Office of the Registrar Staff" in norm(h2.get_text(" ", strip=True)):
        section_h2 = h2
        break

if not section_h2:
    raise RuntimeError("Couldn't find the staff section header. Page structure may have changed.")

people = []
current = None

# After the staff header, each person starts at an h3 with their name.
for el in section_h2.find_all_next():
    # Stop if we reach a new major section
    if el.name == "h2" and el is not section_h2:
        break

    if el.name == "h3":
        # start a new person
        if current:
            people.append(current)
        current = {
            "name": norm(el.get_text(" ", strip=True)),
            "title": None,
            "bio": None,
            "phone": None,
            "email": None,
            "source_url": URL
        }
        continue

    if not current:
        continue

    text = norm(el.get_text(" ", strip=True))
    if not text:
        continue

    # Title tends to be a short line right after the name
    if current["title"] is None and el.name in {"p", "div"} and len(text) < 80 and not is_phone(text) and not is_email(text):
        current["title"] = text
        continue

    # Phone & email show as their own lines
    if current["phone"] is None and is_phone(text):
        current["phone"] = text
        continue

    if current["email"] is None and is_email(text):
        current["email"] = text
        continue

    # Bio: first longer paragraph we see after title
    if current["bio"] is None and el.name in {"p", "div"} and len(text) >= 80 and not is_phone(text) and not is_email(text):
        current["bio"] = text
        continue

# append last person
if current:
    people.append(current)

out = {
    "source_url": URL,
    "page_title": norm((main.find("h1") or soup.find("title")).get_text(" ", strip=True)),
    "people": people
}

print("People extracted:", len(people))
for p in people:
    print("-", p["name"], "|", p["title"])

with open("iit_registrar_people.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("Saved: iit_registrar_people.json")

