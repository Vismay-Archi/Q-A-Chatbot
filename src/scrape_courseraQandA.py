# Coursera Frequently Asked Questions
import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import List, Dict, Any


URL = "https://www.iit.edu/coursera/coursera-faqs"



def clean_text(s: str) -> str:
    """Clean and normalize text"""
    if not s:
        return ""
    # Remove extra whitespace and normalize
    s = re.sub(r"\s+", " ", str(s)).strip()
    # Remove non-breaking spaces and other special characters
    s = s.replace("\xa0", " ")
    s = s.replace("\u200b", "")  # Zero-width space
    return s

def extract_links_from_element(element) -> List[Dict[str, str]]:
    """Extract all links from an element"""
    links = []
    if not element:
        return links
    
    for a in element.find_all('a', href=True):
        href = a.get('href', '')
        text = clean_text(a.get_text())
        if text and href and not href.startswith('#'):
            # Make relative URLs absolute
            if href.startswith('/'):
                href = f"https://www.iit.edu{href}"
            links.append({
                "text": text,
                "url": href,
                "type": "external" if href.startswith('http') and 'iit.edu' not in href else "internal"
            })
    return links

def extract_images_from_element(element) -> List[Dict[str, str]]:
    """Extract all images from an element"""
    images = []
    if not element:
        return images
    
    for img in element.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '')
        if src:
            if src.startswith('/'):
                src = f"https://www.iit.edu{src}"
            images.append({
                "src": src,
                "alt": clean_text(alt)
            })
    return images

def parse_accordion_content(accordion) -> Dict[str, Any]:
    """Parse a single accordion item (FAQ)"""
    # Get question from button
    button = accordion.find('button', class_='accordion__button')
    if not button:
        return None
    
    question_elem = button.find('h3', class_='accordion__button-text')
    question = clean_text(question_elem.get_text() if question_elem else button.get_text())
    
    # Get content
    content = accordion.find('div', class_='accordion__content')
    if not content:
        return None
    
    # Extract all paragraphs and list items
    paragraphs = []
    list_items = []
    
    for elem in content.find_all(['p', 'li', 'div'], recursive=True):
        # Skip if it's a container with other elements
        if elem.name == 'div' and elem.find(['p', 'li']):
            continue
        
        text = clean_text(elem.get_text())
        if text and len(text) > 3:  # Filter out very short text
            if elem.name == 'li':
                list_items.append(text)
            else:
                paragraphs.append(text)
    
    # If we have list items but no paragraphs, use list items
    if not paragraphs and list_items:
        paragraphs = list_items
    
    # If still no paragraphs, get all text
    if not paragraphs:
        full_text = clean_text(content.get_text())
        if full_text:
            paragraphs = [full_text]
    
    # Extract links and images
    links = extract_links_from_element(content)
    images = extract_images_from_element(content)
    
    # Check for nested structure (like the PBA course drop process which has subsections)
    subsections = []
    strong_tags = content.find_all('strong')
    for strong in strong_tags:
        subsection_title = clean_text(strong.get_text())
        if subsection_title and len(subsection_title) > 5:
            # Find the content after this strong tag until next strong or end
            subsection_content = []
            next_elem = strong.find_next_sibling()
            while next_elem and next_elem.name not in ['strong', 'h4', 'h5']:
                if next_elem.name in ['p', 'ul', 'ol', 'div']:
                    sub_text = clean_text(next_elem.get_text())
                    if sub_text:
                        subsection_content.append(sub_text)
                next_elem = next_elem.find_next_sibling()
            
            if subsection_content:
                subsections.append({
                    "title": subsection_title,
                    "content": subsection_content
                })
    
    faq_item = {
        "question": question,
        "answer_paragraphs": paragraphs,
        "full_answer": " ".join(paragraphs),
        "links": links,
        "images": images
    }
    
    if subsections:
        faq_item["subsections"] = subsections
    
    return faq_item

def parse_communication_section(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parse the communication section at the end"""
    comm_section = soup.find('h2', string=re.compile("Communication", re.I))
    if not comm_section:
        return None
    
    comm_content = comm_section.find_next('article', class_='full-wysiwyg')
    if not comm_content:
        return None
    
    # Extract paragraphs
    paragraphs = []
    for p in comm_content.find_all(['p', 'li']):
        text = clean_text(p.get_text())
        if text:
            paragraphs.append(text)
    
    # Extract email links specifically
    emails = []
    for a in comm_content.find_all('a', href=re.compile(r'mailto:')):
        href = a.get('href', '')
        email = href.replace('mailto:', '')
        text = clean_text(a.get_text())
        emails.append({
            "email": email,
            "purpose": text
        })
    
    links = extract_links_from_element(comm_content)
    
    return {
        "section_title": "Communication",
        "content": paragraphs,
        "emails": emails,
        "links": links
    }

def scrape_coursera_faqs():
    """Main scraper function"""
    print("=" * 70)
    print("Coursera FAQs Webpage Scraper")
    print("=" * 70)
    print(f"URL: {URL}")
    print("-" * 70)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        print("✓ Page loaded successfully")
    except Exception as e:
        print(f"✗ Error loading page: {e}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract page metadata
    title_elem = soup.find('h1')
    page_title = clean_text(title_elem.get_text() if title_elem else "Coursera FAQs")
    
    # Extract meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    page_description = meta_desc.get('content', '') if meta_desc else ""
    
    # Extract breadcrumbs
    breadcrumbs = []
    breadcrumb_list = soup.find('ol', class_='breadcrumbs')
    if breadcrumb_list:
        for li in breadcrumb_list.find_all('li'):
            link = li.find('a')
            if link:
                breadcrumbs.append({
                    "name": clean_text(link.get_text()),
                    "url": f"https://www.iit.edu{link.get('href', '')}"
                })
            else:
                breadcrumbs.append({"name": clean_text(li.get_text()), "url": None})
    
    # Extract all FAQ sections (accordion sections)
    sections = []
    section_headings = soup.find_all('h2', class_='section-heading__heading')
    
    for heading in section_headings:
        section_title = clean_text(heading.get_text())
        if not section_title or section_title == "Communication":
            continue
        
        # Find the section div that follows this heading
        section_div = heading.find_parent('div', class_='section--accordion')
        if not section_div:
            # Try to find the next section--accordion
            section_div = heading.find_next('div', class_='section--accordion')
        
        if section_div:
            # Find all accordions in this section
            accordions = section_div.find_all('div', class_='accordion')
            
            section_faqs = []
            for accordion in accordions:
                faq = parse_accordion_content(accordion)
                if faq:
                    section_faqs.append(faq)
            
            if section_faqs:
                sections.append({
                    "section_title": section_title,
                    "faq_count": len(section_faqs),
                    "faqs": section_faqs
                })
                print(f"  ✓ {section_title}: {len(section_faqs)} FAQs")
    
    # Parse communication section
    communication = parse_communication_section(soup)
    if communication:
        print(f"  ✓ Communication section found")
    
    # Extract all links from the page for reference
    all_links = []
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        text = clean_text(a.get_text())
        if text and href and not href.startswith('#') and not href.startswith('javascript:'):
            if href.startswith('/'):
                href = f"https://www.iit.edu{href}"
            all_links.append({
                "text": text,
                "url": href
            })
    
    # Remove duplicate links
    unique_links = []
    seen_urls = set()
    for link in all_links:
        if link['url'] not in seen_urls:
            seen_urls.add(link['url'])
            unique_links.append(link)
    
    # Compile complete webpage data
    output_data = {
        "url": URL,
        "page_title": page_title,
        "page_description": page_description,
        "scrape_date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "breadcrumbs": breadcrumbs,
        "total_sections": len(sections),
        "total_faqs": sum(section['faq_count'] for section in sections),
        "sections": sections,
        "communication": communication,
        "all_page_links": unique_links[:50]  # Limit to first 50 to keep file size reasonable
    }
    
    # Save to JSON following team naming convention
    filename = "iit_coursera_faqs.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 70}")
    print("Scraping Complete!")
    print(f"{'=' * 70}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ Total sections: {len(sections)}")
    print(f"✓ Total FAQs: {output_data['total_faqs']}")
    print(f"✓ File size: {len(json.dumps(output_data)) / 1024:.1f} KB")
    
    return output_data

def print_statistics(data):
    """Print statistics about the scraped data"""
    if not data:
        return
    
    print(f"\n{'=' * 70}")
    print("SCRAPING STATISTICS")
    print(f"{'=' * 70}")
    print(f"URL: {data['url']}")
    print(f"Page Title: {data['page_title']}")
    print(f"Scrape Date: {data['scrape_date']}")
    print(f"Total Sections: {data['total_sections']}")
    print(f"Total FAQs: {data['total_faqs']}")
    
    for section in data['sections']:
        print(f"\n  📁 {section['section_title']}")
        print(f"     └─ {section['faq_count']} FAQs")
        # Show first few questions as preview
        for i, faq in enumerate(section['faqs'][:2], 1):
            print(f"        {i}. {faq['question'][:60]}...")
        if section['faq_count'] > 2:
            print(f"        ... and {section['faq_count'] - 2} more")
    
    if data.get('communication'):
        print(f"\n  📧 Communication section found")
        if data['communication'].get('emails'):
            print(f"     └─ {len(data['communication']['emails'])} contact emails")

def show_sample(data):
    """Show a detailed sample of the first FAQ"""
    if not data or not data['sections']:
        return
    
    print(f"\n{'=' * 70}")
    print("SAMPLE FAQ (First question from first section)")
    print(f"{'=' * 70}")
    
    first_section = data['sections'][0]
    first_faq = first_section['faqs'][0]
    
    print(f"Section: {first_section['section_title']}")
    print(f"\nQ: {first_faq['question']}")
    print(f"\nA: {first_faq['full_answer'][:300]}...")
    
    if first_faq.get('links'):
        print(f"\nLinks in this answer: {len(first_faq['links'])}")
        for link in first_faq['links'][:3]:
            print(f"  • {link['text']} -> {link['url'][:50]}...")
    
    if first_faq.get('subsections'):
        print(f"\nSubsections: {len(first_faq['subsections'])}")

def export_readable_text(data, filename="coursera_faqs_readable.txt"):
    """Export a human-readable text version of all FAQs"""
    if not data:
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"{data['page_title']}\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Source: {data['url']}\n")
        f.write(f"Scraped: {data['scrape_date']}\n\n")
        
        for section in data['sections']:
            f.write(f"\n{'─' * 80}\n")
            f.write(f"{section['section_title']}\n")
            f.write(f"{'─' * 80}\n\n")
            
            for i, faq in enumerate(section['faqs'], 1):
                f.write(f"Q{i}: {faq['question']}\n\n")
                f.write(f"A: {faq['full_answer']}\n\n")
                if faq.get('links'):
                    f.write("Related links:\n")
                    for link in faq['links']:
                        f.write(f"  • {link['text']}: {link['url']}\n")
                f.write("\n" + "-" * 40 + "\n\n")
    
    print(f"\n✓ Readable text exported to: {filename}")

# Main execution
if __name__ == "__main__":
    print("\n🚀 Starting Coursera FAQs webpage scraper...")
    print("This will extract ALL content from the page and save it to JSON.\n")
    
    result = scrape_coursera_faqs()
    
    if result:
        print_statistics(result)
        show_sample(result)
        
        # Also export a readable text version for easy viewing
        export_readable_text(result)
    
    print("\n✅ Scraping process completed successfully!")