import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import List, Dict, Any

URL = "https://www.iit.edu/gaa/students/faqs"

def clean_text(s: str) -> str:
    """Clean and normalize text"""
    if not s:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip()
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

def extract_files_from_element(element) -> List[Dict[str, str]]:
    """Extract file attachments (PDFs, etc.) from an element"""
    files = []
    if not element:
        return files
    
    for a in element.find_all('a', href=True):
        href = a.get('href', '')
        if href.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
            text = clean_text(a.get_text())
            if href.startswith('/'):
                href = f"https://www.iit.edu{href}"
            files.append({
                "name": text,
                "url": href,
                "type": href.split('.')[-1] if '.' in href else "file"
            })
    return files

def parse_qa_pairs(content_div) -> List[Dict[str, Any]]:
    """Parse multiple Q&A pairs from accordion content"""
    qa_pairs = []
    if not content_div:
        return qa_pairs
    
    # Find all strong tags (likely questions)
    strong_tags = content_div.find_all('strong')
    
    for strong in strong_tags:
        question = clean_text(strong.get_text())
        if not question or len(question) < 5:
            continue
        
        # Get answer content after this strong tag
        answer_paragraphs = []
        current = strong.find_next_sibling()
        
        # Collect all following elements until next strong tag
        while current and current.name != 'strong':
            if current.name in ['p', 'div']:
                text = clean_text(current.get_text())
                if text:
                    answer_paragraphs.append(text)
            elif current.name in ['ul', 'ol']:
                for li in current.find_all('li'):
                    li_text = clean_text(li.get_text())
                    if li_text:
                        answer_paragraphs.append(f"• {li_text}")
            current = current.find_next_sibling()
        
        # If we couldn't find structured answer, try getting all text after
        if not answer_paragraphs:
            next_content = []
            for sibling in strong.find_next_siblings():
                if sibling.name == 'strong':
                    break
                text = clean_text(sibling.get_text())
                if text:
                    next_content.append(text)
            if next_content:
                answer_paragraphs = next_content
        
        if answer_paragraphs:
            # Extract links from this Q&A
            links = []
            for p in strong.find_all_next():
                if p.name == 'strong':
                    break
                links.extend(extract_links_from_element(p))
            
            qa_pairs.append({
                "question": question,
                "answer_paragraphs": answer_paragraphs,
                "full_answer": " ".join(answer_paragraphs),
                "links": links
            })
    
    # If no strong tags found, try to parse as a single Q&A
    if not qa_pairs:
        # Look for paragraphs that might contain questions
        paragraphs = content_div.find_all('p')
        i = 0
        while i < len(paragraphs):
            p = paragraphs[i]
            text = clean_text(p.get_text())
            if text and '?' in text:
                # This might be a question
                question = text
                answer_paragraphs = []
                
                # Collect following paragraphs as answer
                i += 1
                while i < len(paragraphs):
                    next_text = clean_text(paragraphs[i].get_text())
                    if next_text and '?' in next_text and len(next_text) < 200:
                        break
                    if next_text:
                        answer_paragraphs.append(next_text)
                    i += 1
                
                if answer_paragraphs:
                    qa_pairs.append({
                        "question": question,
                        "answer_paragraphs": answer_paragraphs,
                        "full_answer": " ".join(answer_paragraphs),
                        "links": extract_links_from_element(p)
                    })
            else:
                i += 1
    
    return qa_pairs

def parse_accordion_content(accordion) -> Dict[str, Any]:
    """Parse a single accordion item (FAQ category)"""
    # Get category title from button
    button = accordion.find('button', class_='accordion__button')
    if not button:
        return None
    
    title_elem = button.find('h3', class_='accordion__button-text')
    category_title = clean_text(title_elem.get_text() if title_elem else button.get_text())
    
    # Get content
    content = accordion.find('div', class_='accordion__content')
    if not content:
        return None
    
    # Parse Q&A pairs within this category
    qa_pairs = parse_qa_pairs(content)
    
    # Also extract all paragraphs as fallback
    all_paragraphs = []
    for p in content.find_all(['p', 'li']):
        text = clean_text(p.get_text())
        if text:
            all_paragraphs.append(text)
    
    # Extract all links and files in this category
    all_links = extract_links_from_element(content)
    all_files = extract_files_from_element(content)
    
    return {
        "category": category_title,
        "qa_count": len(qa_pairs),
        "qa_pairs": qa_pairs,
        "all_content_paragraphs": all_paragraphs,
        "full_content": " ".join(all_paragraphs),
        "links": all_links,
        "files": all_files
    }

def scrape_gaa_faqs():
    """Main scraper function"""
    print("=" * 70)
    print("Graduate Academic Affairs FAQs Webpage Scraper")
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
    page_title = clean_text(title_elem.get_text() if title_elem else "Graduate Academic Affairs FAQs")
    
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
    
    # Extract sidebar navigation
    sidebar_links = []
    sidebar = soup.find('nav', class_='sidebar-menu')
    if sidebar:
        for a in sidebar.find_all('a', href=True):
            href = a.get('href', '')
            text = clean_text(a.get_text())
            if text and href:
                if href.startswith('/'):
                    href = f"https://www.iit.edu{href}"
                sidebar_links.append({
                    "text": text,
                    "url": href,
                    "is_active": 'is-active' in a.get('class', [])
                })
    
    # Extract all FAQ categories (accordions)
    categories = []
    accordions = soup.find_all('div', class_='accordion')
    
    for accordion in accordions:
        category = parse_accordion_content(accordion)
        if category:
            categories.append(category)
            print(f"  ✓ {category['category']}: {category['qa_count']} Q&A pairs")
    
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
        "sidebar_navigation": sidebar_links,
        "total_categories": len(categories),
        "total_qa_pairs": sum(cat['qa_count'] for cat in categories),
        "categories": categories,
        "all_page_links": unique_links[:50]  # Limit to first 50 to keep file size reasonable
    }
    
    # Save to JSON following team naming convention
    filename = "iit_gaa_faqs.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 70}")
    print("Scraping Complete!")
    print(f"{'=' * 70}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ Total FAQ categories: {len(categories)}")
    print(f"✓ Total Q&A pairs: {output_data['total_qa_pairs']}")
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
    print(f"Total FAQ Categories: {data['total_categories']}")
    print(f"Total Q&A Pairs: {data['total_qa_pairs']}")
    
    print(f"\nFAQ Categories:")
    for category in data['categories']:
        print(f"  📁 {category['category']}")
        print(f"     └─ {category['qa_count']} questions")
        # Show first few questions as preview
        for i, qa in enumerate(category['qa_pairs'][:2], 1):
            print(f"        {i}. {qa['question'][:60]}...")
        if category['qa_count'] > 2:
            print(f"        ... and {category['qa_count'] - 2} more")

def show_sample(data):
    """Show a detailed sample of the first Q&A pair"""
    if not data or not data['categories']:
        return
    
    print(f"\n{'=' * 70}")
    print("SAMPLE Q&A (First question from first category)")
    print(f"{'=' * 70}")
    
    first_category = data['categories'][0]
    if first_category['qa_pairs']:
        first_qa = first_category['qa_pairs'][0]
        
        print(f"Category: {first_category['category']}")
        print(f"\nQ: {first_qa['question']}")
        print(f"\nA: {first_qa['full_answer'][:300]}...")
        
        if first_qa.get('links'):
            print(f"\nLinks in this answer: {len(first_qa['links'])}")
            for link in first_qa['links'][:3]:
                print(f"  • {link['text']} -> {link['url'][:50]}...")

def export_readable_text(data, filename="gaa_faqs_readable.txt"):
    """Export a human-readable text version of all FAQs"""
    if not data:
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"{data['page_title']}\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Source: {data['url']}\n")
        f.write(f"Scraped: {data['scrape_date']}\n\n")
        
        for category in data['categories']:
            f.write(f"\n{'─' * 80}\n")
            f.write(f"{category['category']}\n")
            f.write(f"{'─' * 80}\n\n")
            
            for i, qa in enumerate(category['qa_pairs'], 1):
                f.write(f"Q{i}: {qa['question']}\n\n")
                f.write(f"A: {qa['full_answer']}\n\n")
                
                if qa.get('links'):
                    f.write("Related links:\n")
                    for link in qa['links']:
                        f.write(f"  • {link['text']}: {link['url']}\n")
                f.write("\n" + "-" * 40 + "\n\n")
    
    print(f"\n✓ Readable text exported to: {filename}")

def export_qa_csv(data, filename="gaa_faqs.csv"):
    """Export Q&A pairs to CSV format for easy import into databases"""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Category', 'Question', 'Answer', 'Links'])
        
        for category in data['categories']:
            for qa in category['qa_pairs']:
                # Format links as a string
                links_str = "; ".join([f"{link['text']}: {link['url']}" for link in qa.get('links', [])])
                writer.writerow([
                    category['category'],
                    qa['question'],
                    qa['full_answer'],
                    links_str
                ])
    
    print(f"\n✓ CSV data exported to: {filename}")

# Main execution
if __name__ == "__main__":
    print("\n🚀 Starting Graduate Academic Affairs FAQs webpage scraper...")
    print("This will extract ALL content from the page and save it to JSON.\n")
    
    result = scrape_gaa_faqs()
    
    if result:
        print_statistics(result)
        show_sample(result)
        
        # Also export additional formats for flexibility
        export_readable_text(result)
        export_qa_csv(result)
    
    print("\n✅ Scraping process completed successfully!")