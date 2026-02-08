import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from urllib.parse import urljoin


class ImportantInformationScraper:
    def __init__(self):
        self.url = "https://www.iit.edu/registrar/important-information"

    # -------------------------------
    # FETCH PAGE
    # -------------------------------
    def fetch_page(self):
        response = requests.get(self.url)
        response.raise_for_status()
        return response.text

    # -------------------------------
    # PARSE PAGE CONTENT
    # -------------------------------
    def parse_page(self, html):

        soup = BeautifulSoup(html, "html.parser")

        # -------- PAGE TITLE --------
        title_tag = soup.find("h1")
        page_title = title_tag.get_text(strip=True) if title_tag else ""

        # -------- META DESCRIPTION --------
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        # -------- BREADCRUMBS --------
        breadcrumbs = []
        breadcrumb_items = soup.select(".breadcrumbs li")

        for item in breadcrumb_items:
            breadcrumbs.append(item.get_text(strip=True))

        # -------- MAIN PARAGRAPHS --------
        paragraphs = []
        main_content = soup.select(".main-content p")

        for p in main_content:
            text = p.get_text(strip=True)
            if text:
                paragraphs.append(text)

        # -------- CONTENT RESOURCE LINKS --------
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

        # -------- BUILD JSON --------
        data = {
            "url": self.url,
            "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": page_title,
            "meta_description": meta_desc,
            "breadcrumbs": breadcrumbs,
            "sections": [
                {
                    "section_id": "important_information_overview",
                    "title": page_title,
                    "paragraphs": paragraphs,
                    "resource_links": resource_links,
                    "sidebar_links": sidebar_links
                }
            ]
        }

        return data

    # -------------------------------
    # SAVE JSON
    # -------------------------------
    def save_json(self, data, filename="important_information.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Data saved to {filename}")

    # -------------------------------
    # RUN SCRAPER
    # -------------------------------
    def run(self):
        html = self.fetch_page()
        parsed_data = self.parse_page(html)
        self.save_json(parsed_data)


if __name__ == "__main__":
    scraper = ImportantInformationScraper()
    scraper.run()
