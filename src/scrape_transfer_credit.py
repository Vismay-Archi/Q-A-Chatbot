import requests
from bs4 import BeautifulSoup
import json
import time
import re

URL = "https://catalog.iit.edu/graduate/academic-policies-procedures/academic-progress/transfer-credit/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def scrape_transfer_credit():
    response = requests.get(URL, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    main_content = soup.find("div", id="content")
    text_container = main_content.find("div", id="textcontainer")

    page_title = clean_text(
        main_content.find("h1", class_="page-title").get_text()
    )

    sections = []
    current_section = None

    for element in text_container.find_all(
        ["h2", "h3", "h4", "p", "ol", "ul"], recursive=True
    ):
        tag = element.name

        if tag in ["h2", "h3", "h4"]:
            if current_section:
                current_section["full_text"] = " ".join(current_section["content"])
                sections.append(current_section)

            current_section = {
                "title": clean_text(element.get_text()),
                "level": int(tag[1]),
                "content": [],
                "full_text": ""
            }

        elif tag == "p" and current_section:
            text = clean_text(element.get_text())
            if text:
                current_section["content"].append(text)

        elif tag in ["ol", "ul"] and current_section:
            for li in element.find_all("li"):
                text = clean_text(li.get_text())
                if text:
                    current_section["content"].append(text)

    if current_section:
        current_section["full_text"] = " ".join(current_section["content"])
        sections.append(current_section)

    return {
        "url": URL,
        "scrape_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "page_title": page_title,
        "sections": sections
    }


if __name__ == "__main__":
    data = scrape_transfer_credit()

    with open("transfer_credit.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✓ Transfer Credit data scraped successfully")
    print(f"✓ Sections extracted: {len(data['sections'])}")
