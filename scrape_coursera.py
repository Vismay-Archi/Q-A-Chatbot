
import requests
from bs4 import BeautifulSoup
import json
import time

# URLs to scrape
urls = [
    "https://www.iit.edu/coursera",
    "https://www.iit.edu/coursera/coursera-faqs",
    "https://www.iit.edu/coursera/advising-and-planning"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def scrape_page(url):
    """Scrape a single page and extract all content"""
    print(f"\nScraping: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  ✗ Error: Status code {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        page_data = {
            'url': url,
            'title': '',
            'headings': [],
            'paragraphs': [],
            'lists': [],
            'links': [],
            'tables': [],
            'faqs': [],
            'full_text': ''
        }
        
        # Get page title
        title_tag = soup.find('h1')
        if title_tag:
            page_data['title'] = title_tag.get_text(strip=True)
        else:
            title_tag = soup.find('title')
            if title_tag:
                page_data['title'] = title_tag.get_text(strip=True)
        
        # Get all headings (h1, h2, h3, etc.)
        for level in range(1, 7):
            headings = soup.find_all(f'h{level}')
            for heading in headings:
                text = heading.get_text(strip=True)
                if text:
                    page_data['headings'].append({
                        'level': level,
                        'text': text
                    })
        
        # Get all paragraphs
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) > 10:  # Skip very short paragraphs
                page_data['paragraphs'].append(text)
        
        # Get all lists (ul, ol)
        lists = soup.find_all(['ul', 'ol'])
        for lst in lists:
            items = lst.find_all('li')
            list_items = [li.get_text(strip=True) for li in items if li.get_text(strip=True)]
            if list_items:
                page_data['lists'].append({
                    'type': lst.name,
                    'items': list_items
                })
        
        # Get all links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href')
            text = link.get_text(strip=True)
            if text and href:
                # Make absolute URLs
                if href.startswith('/'):
                    href = 'https://www.iit.edu' + href
                page_data['links'].append({
                    'text': text,
                    'url': href
                })
        
        # Get all tables
        tables = soup.find_all('table')
        for table in tables:
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            if rows:
                page_data['tables'].append(rows)
        
        # Look for FAQ sections
        faq_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'faq' in x.lower())
        for faq_section in faq_sections:
            # Look for question/answer pairs
            questions = faq_section.find_all(['h3', 'h4', 'dt', 'strong'])
            for q in questions:
                question_text = q.get_text(strip=True)
                # Try to find the answer (next sibling or within same container)
                answer = ""
                next_elem = q.find_next_sibling(['p', 'dd', 'div'])
                if next_elem:
                    answer = next_elem.get_text(strip=True)
                
                if question_text:
                    page_data['faqs'].append({
                        'question': question_text,
                        'answer': answer
                    })
        
        # Get full text content (for search/analysis)
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            page_data['full_text'] = main_content.get_text(separator='\n', strip=True)
        
        print(f"  ✓ Extracted:")
        print(f"    - Title: {page_data['title']}")
        print(f"    - Headings: {len(page_data['headings'])}")
        print(f"    - Paragraphs: {len(page_data['paragraphs'])}")
        print(f"    - Lists: {len(page_data['lists'])}")
        print(f"    - Links: {len(page_data['links'])}")
        print(f"    - Tables: {len(page_data['tables'])}")
        print(f"    - FAQs: {len(page_data['faqs'])}")
        
        return page_data
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return None

# Main execution
print("IIT Coursera Pages Scraper")
print("=" * 60)

all_pages = []

for url in urls:
    page_data = scrape_page(url)
    if page_data:
        all_pages.append(page_data)
    time.sleep(1)  # Be nice to the server

# Save all data
output_data = {
    'scrape_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'total_pages': len(all_pages),
    'pages': all_pages
}

with open('iit_coursera_pages.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

print(f"\n{'=' * 60}")
print(f"✓ All data saved to iit_coursera_pages.json")
print(f"  Total pages scraped: {len(all_pages)}")
print("=" * 60)

# Also save each page separately for easier access
for i, page in enumerate(all_pages):
    filename = page['url'].split('/')[-1] or 'coursera'
    filename = f'coursera_{filename}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(page, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ {filename}")

print("\nDone!")
