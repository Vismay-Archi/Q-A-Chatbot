import requests
from bs4 import BeautifulSoup
import json
import time

URL = "https://www.iit.edu/commencement"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def scrape_commencement(url):
    print(f"Scraping: {url}")
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    sections = []
    current_section = {"title": "Overview", "paragraphs": [], "lists": [], "links": [], "full_text": ""}

    main_content = soup.find('main') or soup.find('body')
    if not main_content:
        main_content = soup

    for tag in main_content.descendants:
        if not getattr(tag, 'name', None):
            continue

        # Headings
        if tag.name in ['h1', 'h2', 'h3']:
            if current_section["paragraphs"] or current_section["lists"] or current_section["full_text"]:
                sections.append(current_section)

            current_section = {
                "title": tag.get_text(strip=True),
                "paragraphs": [],
                "lists": [],
                "links": [],
                "full_text": ""
            }

        # Paragraphs
        elif tag.name == 'p':
            text = tag.get_text(strip=True)
            if text:
                current_section["paragraphs"].append(text)
                current_section["full_text"] += text + "\n"

        # Lists
        elif tag.name in ['ul', 'ol']:
            items = [li.get_text(strip=True) for li in tag.find_all('li') if li.get_text(strip=True)]
            if items:
                current_section["lists"].append({
                    "type": tag.name,
                    "items": items
                })
                current_section["full_text"] += "\n".join(items) + "\n"

        # Links
        elif tag.name == 'a' and tag.get('href'):
            href = tag['href']
            if href.startswith('/'):
                href = 'https://www.iit.edu' + href
            link_text = tag.get_text(strip=True)
            current_section["links"].append({
                "text": link_text,
                "url": href
            })
            if link_text:
                current_section["full_text"] += link_text + "\n"

    # Add last section
    if current_section["paragraphs"] or current_section["lists"] or current_section["full_text"]:
        sections.append(current_section)

    return sections

# Run scraper
print("Commencement Page Scraper")
print("="*50)

sections = scrape_commencement(URL)

output = {
    "scrape_date": time.strftime('%Y-%m-%d %H:%M:%S'),
    "url": URL,
    "total_sections": len(sections),
    "sections": sections
}

# Save JSON
json_file = "iit_commencement.json"
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"✓ Saved structured JSON to {json_file}")
