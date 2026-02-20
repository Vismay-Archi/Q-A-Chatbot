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
            if href.startswith('/'):
                href = f"https://www.iit.edu{href}"
            links.append({
                "text": text,
                "url": href,
                "type": "external" if href.startswith('http') and 'iit.edu' not in href else "internal"
            })
    return links

def parse_qa_pairs(content_div) -> List[Dict[str, Any]]:
    """Parse Q&A pairs from accordion content"""
    qa_pairs = []
    if not content_div:
        return qa_pairs
    
    # Find all question-answer patterns (strong tags or paragraphs with bold text)
    current_question = None
    current_answer = []
    
    for element in content_div.children:
        if element.name in ['p', 'div']:
            # Check if this is a question (strong tag or bold text)
            strong = element.find('strong')
            if strong or (element.get_text().strip().endswith('?')):
                # Save previous Q&A if exists
                if current_question and current_answer:
                    qa_pairs.append({
                        "question": clean_text(current_question),
                        "answer": " ".join(current_answer),
                        "answer_paragraphs": current_answer.copy()
                    })
                
                # Start new question
                if strong:
                    current_question = clean_text(strong.get_text())
                    # Get remaining text after strong tag
                    remaining = element.get_text().replace(strong.get_text(), '', 1).strip()
                    if remaining:
                        current_answer = [clean_text(remaining)]
                    else:
                        current_answer = []
                else:
                    current_question = clean_text(element.get_text())
                    current_answer = []
            
            # This is answer text
            elif current_question:
                text = clean_text(element.get_text())
                if text:
                    current_answer.append(text)
            
            # Handle lists (ul, ol)
            elif element.name in ['ul', 'ol']:
                list_items = []
                for li in element.find_all('li', recursive=False):
                    li_text = clean_text(li.get_text())
                    if li_text:
                        list_items.append(f"• {li_text}")
                if list_items and current_question:
                    current_answer.extend(list_items)
    
    # Add last Q&A
    if current_question and current_answer:
        qa_pairs.append({
            "question": clean_text(current_question),
            "answer": " ".join(current_answer),
            "answer_paragraphs": current_answer.copy()
        })
    
    return qa_pairs

def extract_faq_categories(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract FAQ categories and their Q&A pairs"""
    categories = []
    
    # Find all accordions in the page
    accordions = soup.find_all('div', class_='accordion')
    
    for accordion in accordions:
        # Get category title
        button = accordion.find('button', class_='accordion__button')
        if not button:
            continue
        
        title_elem = button.find('h3', class_='accordion__button-text')
        category_title = clean_text(title_elem.get_text() if title_elem else button.get_text())
        
        # Get content
        content = accordion.find('div', class_='accordion__content')
        if not content:
            continue
        
        # Parse Q&A pairs from content
        qa_pairs = parse_qa_pairs(content)
        
        # Extract all links in this category
        links = extract_links_from_content(content)
        
        if category_title and qa_pairs:
            categories.append({
                "category": category_title,
                "faq_count": len(qa_pairs),
                "faqs": qa_pairs,
                "links": links
            })
    
    return categories

def scrape_gaa_faqs():
    """Main scraper function"""
    print("=" * 60)
    print("Graduate Academic Affairs FAQs Scraper")
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
    page_title = clean_text(title_elem.get_text() if title_elem else "Graduate Academic Affairs FAQs")
    
    # Extract breadcrumbs for context
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
    
    # Extract FAQ categories
    categories = extract_faq_categories(soup)
    
    # Compile final data
    output_data = {
        "source_url": URL,
        "page_title": page_title,
        "scrape_date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "breadcrumbs": breadcrumbs,
        "total_categories": len(categories),
        "total_faqs": sum(cat['faq_count'] for cat in categories),
        "categories": categories
    }
    
    # Save to JSON following team naming convention
    filename = "iit_gaa_faqs.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print("Scraping Complete!")
    print(f"{'=' * 60}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ Categories found: {len(categories)}")
    print(f"✓ Total FAQs: {output_data['total_faqs']}")
    
    return output_data

def print_statistics(data):
    """Print statistics about the scraped data"""
    if not data:
        return
    
    print(f"\nStatistics:")
    print(f"  Source: {data['source_url']}")
    print(f"  Scrape Date: {data['scrape_date']}")
    print(f"  Total Categories: {data['total_categories']}")
    print(f"  Total FAQs: {data['total_faqs']}")
    
    for category in data['categories']:
        print(f"  • {category['category']}: {category['faq_count']} FAQs")
        if category.get('links'):
            print(f"    - {len(category['links'])} resources")

def show_sample(data):
    """Show sample entries"""
    if not data or not data['categories']:
        return
    
    print(f"\nSample Entries:")
    print("-" * 60)
    
    # Show first category and its first FAQ
    first_category = data['categories'][0]
    print(f"\nCategory: {first_category['category']}")
    if first_category['faqs']:
        first_faq = first_category['faqs'][0]
        print(f"  Q: {first_faq['question']}")
        print(f"  A: {first_faq['answer'][:200]}...")
        
        # Show second FAQ if available
        if len(first_category['faqs']) > 1:
            second_faq = first_category['faqs'][1]
            print(f"\n  Q: {second_faq['question'][:100]}...")
            print(f"  A: {second_faq['answer'][:150]}...")

# Main execution
if __name__ == "__main__":
    print("\nStarting Graduate Academic Affairs FAQs scraper...")
    result = scrape_gaa_faqs()
    
    if result:
        print_statistics(result)
        show_sample(result)
    
    print("\n✓ Done!")