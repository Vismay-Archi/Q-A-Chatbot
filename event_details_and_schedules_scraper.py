import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

URL = "https://www.iit.edu/commencement/event-details-and-schedules"

def scrape_event_details():
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    content = soup.select_one("article.basic-page article.full-wysiwyg")
    if not content:
        raise ValueError("Main content not found")

    sections = []
    current_section = None

    for element in content.children:
        if not hasattr(element, "name"):
            continue

        # Major event headings
        if element.name in ["h3", "h4"]:
            if current_section:
                sections.append(current_section)

            current_section = {
                "title": element.get_text(strip=True),
                "content": []
            }

        # Paragraphs (ALL are important here)
        elif element.name == "p" and current_section:
            text = element.get_text(" ", strip=True)
            if text:
                current_section["content"].append(text)

    if current_section:
        sections.append(current_section)

    data = {
        "source": "Illinois Institute of Technology – Commencement",
        "page_title": "Event Details and Schedules",
        "url": URL,
        "scraped_at": datetime.utcnow().isoformat(),
        "sections": sections
    }

    return data


if __name__ == "__main__":
    data = scrape_event_details()

    with open("event_details_and_schedules.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Scraping complete. Data saved to event_details_and_schedules.json")
