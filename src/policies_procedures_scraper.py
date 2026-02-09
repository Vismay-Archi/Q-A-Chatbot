import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from urllib.parse import urljoin


class PoliciesProceduresScraper:

    def __init__(self):
        self.url = "https://www.iit.edu/registrar/policies-and-procedures"

    # ---------------------------
    # FETCH PAGE
    # ---------------------------
    def fetch_page(self):
        response = requests.get(self.url)
        response.raise_for_status()
        return response.text

    # ---------------------------
    # PARSE PAGE
    # ---------------------------
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

        # -------- POLICY / RESOURCE LINKS --------
        policy_links = []
        content_links = soup.select(".main-content a")

        for link in content_links:
            text = link.get_text(strip=True)
            href = link.get("href")

            if text and href:
                policy_links.append({
                    "title": text,
                    "url": urljoin(self.url, href)
                })

        # -------- SIDEBAR NAVIGATION --------
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

        # -------- CONTACT INFO EXTRACTION --------
        contact_info = {}

        contact_email = soup.find("a", href=lambda x: x and "mailto:" in x if x else False)
        if contact_email:
            contact_info["email"] = contact_email.get_text(strip=True)

        phone_text = soup.get_text()
        if "312." in phone_text:
            contact_info["phone"] = "312.567.3100"

        # -------- BUILD JSON --------
        data = {
            "url": self.url,
            "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": page_title,
            "meta_description": meta_desc,
            "breadcrumbs": breadcrumbs,
            "contact_information": contact_info,
            "sections": [
                {
                    "section_id": "policies_and_procedures_overview",
                    "title": page_title,
                    "paragraphs": paragraphs,
                    "policy_links": policy_links,
                    "sidebar_links": sidebar_links
                }
            ]
        }

        return data

    # ---------------------------
    # SAVE JSON
    # ---------------------------
    def save_json(self, data, filename="policies_procedures.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Data saved to {filename}")

    # ---------------------------
    # RUN SCRAPER
    # ---------------------------
    def run(self):
        html = self.fetch_page()
        parsed = self.parse_page(html)
        self.save_json(parsed)


if __name__ == "__main__":
    scraper = PoliciesProceduresScraper()
    scraper.run()
