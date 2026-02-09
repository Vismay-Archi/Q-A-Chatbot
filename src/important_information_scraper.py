import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

URL = "https://www.iit.edu/registrar/important-information"

def scrape_important_information():
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    content = soup.select_one("article.basic-page article.full-wysiwyg")
    if not content:
        raise ValueError("Main content not found")

    sections = []

    # Each major topic is marked by an <h2>
    for h2 in content.find_all("h2"):
        section = {
            "id": h2.get("id"),
            "title": h2.get_text(strip=True),
            "paragraphs": [],
            "steps": []
        }

        # Walk through siblings until the next <h2>
        for sibling in h2.find_next_siblings():
            if sibling.name == "h2":
                break

            if sibling.name == "p":
                text = sibling.get_text(strip=True)
                if text:
                    section["paragraphs"].append(text)

            if sibling.name == "ol":
                for li in sibling.find_all("li"):
                    section["steps"].append(li.get_text(strip=True))

        sections.append(section)

    data = {
        "source": "Illinois Institute of Technology – Office of the Registrar",
        "page_title": "Important Information",
        "url": URL,
        "scraped_at": datetime.utcnow().isoformat(),
        "sections": sections
    }

    return data


if __name__ == "__main__":
    scraped_data = scrape_important_information()

    with open("important_information.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)

    print("Scraping complete. Data saved to important_information.json")
