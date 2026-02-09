import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from urllib.parse import urljoin

URL = "https://www.iit.edu/registrar/policies-and-procedures"

def scrape_registrar_policies():
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Locate the main content area ONLY
    content = soup.select_one("article.basic-page article.full-wysiwyg")

    if not content:
        raise ValueError("Main content not found")

    policies = []

    for p in content.find_all("p"):
        link = p.find("a")

        # Policy links
        if link and link.get("href"):
            policies.append({
                "title": link.get_text(strip=True),
                "url": urljoin(URL, link["href"])
            })

    data = {
        "source": "Illinois Institute of Technology – Office of the Registrar",
        "page_title": "Policies and Procedures",
        "url": URL,
        "scraped_at": datetime.utcnow().isoformat(),
        "description": (
            "Official registrar policies and procedures available to "
            "Illinois Tech students, faculty, and staff."
        ),
        "policies": policies
    }

    return data


if __name__ == "__main__":
    scraped_data = scrape_registrar_policies()

    with open("registrar_policies.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)

    print("Scraping complete. Data saved to registrar_policies.json")
