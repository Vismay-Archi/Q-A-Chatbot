import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from urllib.parse import urljoin


class RegistrationScraper:
    def __init__(self):
        self.url = "https://www.iit.edu/registrar/registration"

    def fetch_page(self):
        """Fetch webpage HTML"""
        response = requests.get(self.url)
        response.raise_for_status()
        return response.text

    def parse_page(self, html):
        """Extract needed information from webpage"""
        soup = BeautifulSoup(html, "html.parser")

        # -------- PAGE TITLE --------
        page_title = soup.find("h1").get_text(strip=True)

        # -------- BREADCRUMBS --------
        breadcrumbs = []
        breadcrumb_items = soup.select(".breadcrumbs li")

        for item in breadcrumb_items:
            breadcrumbs.append(item.get_text(strip=True))

        # -------- MAIN CONTENT --------
        main_content = soup.select(".main-content p")
        paragraphs = [p.get_text(strip=True) for p in main_content]

        # -------- SIDEBAR LINKS --------
        sidebar_links = []
        sidebar = soup.select(".sidebar-menu a")

        for link in sidebar:
            text = link.get_text(strip=True)
            href = link.get("href")

            if text and href:
                sidebar_links.append({
                    "title": text,
                    "url": urljoin(self.url, href)
                })

        # -------- RESOURCE LINKS IN CONTENT --------
        resource_links = []
        content_links = soup.select(".main-content a")

        for link in content_links:
            text = link.get_text(strip=True)
            href = link.get("href")

            if text and href:
                resource_links.append({
                    "title": text,
                    "url": urljoin(self.url, href)
                })

        # -------- BUILD JSON STRUCTURE --------
        data = {
            "url": self.url,
            "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": page_title,
            "breadcrumbs": breadcrumbs,
            "sections": [
                {
                    "section_id": "registration_overview",
                    "title": page_title,
                    "paragraphs": paragraphs,
                    "resource_links": resource_links,
                    "sidebar_links": sidebar_links
                }
            ]
        }

        return data

    def save_json(self, data, filename="registration.json"):
        """Save data to JSON file"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Data saved to {filename}")

    def run(self):
        html = self.fetch_page()
        parsed_data = self.parse_page(html)
        self.save_json(parsed_data)


if __name__ == "__main__":
    scraper = RegistrationScraper()
    scraper.run()
