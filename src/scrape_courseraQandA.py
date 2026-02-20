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
    s = re.sub(r"\s+", " ", str(s)).strip()
    s = s.replace("\xa0", " ")
    return s

def extract_links_from_content(content_div) -> List[Dict[str, str]]:
    """Extract links from content"""
    links = []
    if not content_div:
        return links
    
    for a in content_div.find_all('a', href=True):
        href = a.get('href', '')
        text = clean_text(a.get_text())
        if text and href and not href.startswith('#'):
            # Make sure URL is absolute
            if href.startswith('/'):
                href = f"https://www.iit.edu{href}"
            links.append({
                "text": text,
                "url": href,
                "type": "external" if href.startswith('http') and 'iit.edu' not in href else "internal"
            })
    return links

def extract_images_from_content(content_div) -> List[Dict[str, str]]:
    """Extract images from content"""
    images = []
    if not content_div:
        return images
    
    for img in content_div.find_all('img'):
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

def extract_section_faqs(soup: BeautifulSoup, section_title: str) -> List[Dict[str, Any]]:
    """Extract FAQs from a section"""
    faqs = []
    
    # Find the section heading
    heading = soup.find('h2', string=re.compile(section_title, re.I))
    if not heading:
        return faqs
    
    # Find the section div that follows this heading
    section = heading.find_next('div', class_='section--accordion')
    if not section:
        return faqs
    
    # Find all accordion items in this section
    accordions = section.find_all('div', class_='accordion')
    
    for accordion in accordions:
        # Get question from button text
        button = accordion.find('button', class_='accordion__button')
        if not button:
            continue
        
        question_elem = button.find('h3', class_='accordion__button-text')
        question = clean_text(question_elem.get_text() if question_elem else button.get_text())
        
        # Get answer from content
        content = accordion.find('div', class_='accordion__content')
        if not content:
            continue
        
        # Extract paragraphs and list items
        paragraphs = []
        for elem in content.find_all(['p', 'li', 'div'], recursive=True):
            # Skip if it's a container with other elements
            if elem.name == 'div' and elem.find(['p', 'li']):
                continue
            text = clean_text(elem.get_text())
            if text and len(text) > 5:  # Filter out very short text
                paragraphs.append(text)
        
        # If no paragraphs found, get all text
        if not paragraphs:
            full_text = clean_text(content.get_text())
            if full_text:
                paragraphs = [full_text]
        
        # Extract links and images
        links = extract_links_from_content(content)
        images = extract_images_from_content(content)
        
        if question and paragraphs:
            faq_item = {
                "question": question,
                "answer_paragraphs": paragraphs,
                "full_answer": " ".join(paragraphs),
                "links": links,
                "images": images
            }
            faqs.append(faq_item)
    
    return faqs

def scrape_coursera():
    """Main scraper function"""
    print("=" * 60)
    print("Coursera FAQ Scraper")
    print("=" * 60)
    print(f"URL: {URL}")
    print("-" * 60)
    
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
    
    # Define sections to extract (based on page structure)
    sections = [
        "Admission and Student Record",
        "Registration",
        "Coursera",
        "Tuition and Payment",
        "Illinois Tech Resources"
    ]
    
    all_faqs = []
    sections_data = []
    
    print("\nExtracting FAQ sections:")
    print("-" * 40)
    
    for section_title in sections:
        print(f"Processing: {section_title}...", end=" ")
        faqs = extract_section_faqs(soup, section_title)
        if faqs:
            sections_data.append({
                "section": section_title,
                "faq_count": len(faqs),
                "faqs": faqs
            })
            all_faqs.extend(faqs)
            print(f"✓ Found {len(faqs)} FAQs")
        else:
            print(f"✗ No FAQs found")
    
    # Extract communication section separately
    print("\nProcessing: Communication...", end=" ")
    comm_section = soup.find('h2', string=re.compile("Communication", re.I))
    if comm_section:
        comm_content = comm_section.find_next('article', class_='full-wysiwyg')
        if comm_content:
            comm_paragraphs = []
            for p in comm_content.find_all(['p', 'li']):
                text = clean_text(p.get_text())
                if text:
                    comm_paragraphs.append(text)
            
            comm_links = extract_links_from_content(comm_content)
            
            sections_data.append({
                "section": "Communication",
                "faq_count": 1,
                "faqs": [{
                    "question": "Contact Information and Support",
                    "answer_paragraphs": comm_paragraphs,
                    "full_answer": " ".join(comm_paragraphs),
                    "links": comm_links,
                    "images": []
                }]
            })
            print("✓ Found communication info")
    else:
        print("✗ No communication section found")
    
    # Compile final data
    output_data = {
        "source_url": URL,
        "page_title": page_title,
        "scrape_date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "total_sections": len(sections_data),
        "total_faqs": len(all_faqs),
        "sections": sections_data
    }
    
    # Save to JSON following team naming convention
    filename = "iit_courseraFQA.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print("Scraping Complete!")
    print(f"{'=' * 60}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ Total sections: {len(sections_data)}")
    print(f"✓ Total FAQs: {len(all_faqs)}")
    
    return output_data

def print_statistics(data):
    """Print statistics about the scraped data"""
    if not data:
        return
    
    print(f"\nStatistics:")
    print(f"  Source: {data['source_url']}")
    print(f"  Scrape Date: {data['scrape_date']}")
    print(f"  Total Sections: {data['total_sections']}")
    print(f"  Total FAQs: {data['total_faqs']}")
    
    for section in data['sections']:
        print(f"  • {section['section']}: {section['faq_count']} FAQs")

def show_sample(data):
    """Show sample entries"""
    if not data or not data['sections']:
        return
    
    print(f"\nSample Entries:")
    print("-" * 60)
    
    # Show first section and first FAQ
    first_section = data['sections'][0]
    print(f"\nSection: {first_section['section']}")
    if first_section['faqs']:
        first_faq = first_section['faqs'][0]
        print(f"  Q: {first_faq['question']}")
        print(f"  A: {first_faq['full_answer'][:200]}...")
        if first_faq['links']:
            print(f"  Links found: {len(first_faq['links'])}")
        if first_faq['images']:
            print(f"  Images found: {len(first_faq['images'])}")

# Main execution
if __name__ == "__main__":
    print("\nStarting Coursera FAQ scraper...")
    result = scrape_coursera()
    
    if result:
        print_statistics(result)
        show_sample(result)
    
    print("\n✓ Done!")