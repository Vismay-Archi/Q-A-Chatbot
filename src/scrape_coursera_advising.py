import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import List, Dict, Any

URL = "https://www.iit.edu/coursera/advising-and-planning"

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

def extract_advisers(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract adviser information from the main content"""
    advisers = []
    
    # Find the main content article
    main_content = soup.find('article', class_='full-wysiwyg')
    if not main_content:
        return advisers
    
    # Look for adviser sections (h3 followed by paragraphs)
    h3_tags = main_content.find_all('h3')
    for h3 in h3_tags:
        title = clean_text(h3.get_text())
        if 'Adviser' in title or 'Program Manager' in title:
            # Get the next elements until next h3
            adviser_info = {
                "title": title,
                "name": "",
                "profile_url": "",
                "bio": [],
                "image": None
            }
            
            # Check for link in the next element (usually a paragraph with a link)
            next_elem = h3.find_next_sibling()
            if next_elem and next_elem.name == 'p':
                link = next_elem.find('a')
                if link:
                    adviser_info["name"] = clean_text(link.get_text())
                    href = link.get('href', '')
                    if href.startswith('/'):
                        adviser_info["profile_url"] = f"https://www.iit.edu{href}"
                    else:
                        adviser_info["profile_url"] = href
                    
                    # Get bio paragraphs after this
                    bio_paragraphs = []
                    current = next_elem.find_next_sibling()
                    while current and current.name == 'p':
                        text = clean_text(current.get_text())
                        if text and not current.find('a'):  # Skip if it contains the link again
                            bio_paragraphs.append(text)
                        current = current.find_next_sibling()
                    adviser_info["bio"] = bio_paragraphs
            
            advisers.append(adviser_info)
    
    return advisers

def extract_resources(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract course planning resources from accordions"""
    resources = []
    
    # Find the Course Planning Resources section
    section_heading = soup.find('h2', string=re.compile("Course Planning Resources", re.I))
    if not section_heading:
        return resources
    
    # Find the section div
    section = section_heading.find_next('div', class_='section--accordion')
    if not section:
        return resources
    
    # Find all accordions
    accordions = section.find_all('div', class_='accordion')
    
    for accordion in accordions:
        # Get title from button
        button = accordion.find('button', class_='accordion__button')
        if not button:
            continue
        
        title_elem = button.find('h3', class_='accordion__button-text')
        title = clean_text(title_elem.get_text() if title_elem else button.get_text())
        
        # Get content
        content = accordion.find('div', class_='accordion__content')
        if not content:
            continue
        
        # Extract paragraphs
        paragraphs = []
        for p in content.find_all(['p', 'li']):
            text = clean_text(p.get_text())
            if text:
                paragraphs.append(text)
        
        # Extract links
        links = extract_links_from_content(content)
        
        if title:
            resources.append({
                "category": title,
                "description": paragraphs,
                "links": links
            })
    
    return resources

def extract_advising_options(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract advising session options"""
    options = []
    
    # Find the Our advisers are here to help section
    section_heading = soup.find('h2', string=re.compile("Our advisers are here to help", re.I))
    if not section_heading:
        return options
    
    # Find the section div
    section = section_heading.find_next('div', class_='section--accordion')
    if not section:
        return options
    
    # Find all accordions
    accordions = section.find_all('div', class_='accordion')
    
    for accordion in accordions:
        # Get title from button
        button = accordion.find('button', class_='accordion__button')
        if not button:
            continue
        
        title_elem = button.find('h3', class_='accordion__button-text')
        title = clean_text(title_elem.get_text() if title_elem else button.get_text())
        
        # Get content
        content = accordion.find('div', class_='accordion__content')
        if not content:
            continue
        
        # Extract paragraphs
        paragraphs = []
        for p in content.find_all(['p', 'li']):
            text = clean_text(p.get_text())
            if text:
                paragraphs.append(text)
        
        # Extract links
        links = extract_links_from_content(content)
        
        if title:
            options.append({
                "option_type": title,
                "description": paragraphs,
                "links": links
            })
    
    return options

def scrape_coursera_advising():
    """Main scraper function"""
    print("=" * 60)
    print("Coursera Advising and Planning Scraper")
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
    page_title = clean_text(title_elem.get_text() if title_elem else "Coursera Advising and Planning")
    
    # Extract main content (introduction and advisers)
    main_content = soup.find('article', class_='full-wysiwyg')
    intro_paragraphs = []
    if main_content:
        # Get all paragraphs before the first h3 (introduction)
        for p in main_content.find_all('p', recursive=True):
            # Stop if we hit an h3
            if p.find_previous('h3'):
                break
            text = clean_text(p.get_text())
            if text:
                intro_paragraphs.append(text)
    
    # Extract main image
    main_image = None
    img_tag = soup.find('img', {'alt': re.compile(r'Coursera Student Advising', re.I)})
    if img_tag:
        src = img_tag.get('src', '')
        if src:
            if src.startswith('/'):
                src = f"https://www.iit.edu{src}"
            main_image = {
                "src": src,
                "alt": clean_text(img_tag.get('alt', ''))
            }
    
    # Extract data sections
    advisers = extract_advisers(soup)
    resources = extract_resources(soup)
    advising_options = extract_advising_options(soup)
    
    # Compile final data
    output_data = {
        "source_url": URL,
        "page_title": page_title,
        "scrape_date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "main_image": main_image,
        "introduction": intro_paragraphs,
        "advisers": advisers,
        "planning_resources": resources,
        "advising_options": advising_options
    }
    
    # Save to JSON following team naming convention
    filename = "iit_coursera_advising.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print("Scraping Complete!")
    print(f"{'=' * 60}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ Introduction paragraphs: {len(intro_paragraphs)}")
    print(f"✓ Advisers found: {len(advisers)}")
    print(f"✓ Resource categories: {len(resources)}")
    print(f"✓ Advising options: {len(advising_options)}")
    
    return output_data

def print_statistics(data):
    """Print statistics about the scraped data"""
    if not data:
        return
    
    print(f"\nStatistics:")
    print(f"  Source: {data['source_url']}")
    print(f"  Scrape Date: {data['scrape_date']}")
    print(f"  Introduction: {len(data['introduction'])} paragraphs")
    print(f"  Advisers: {len(data['advisers'])}")
    for adviser in data['advisers']:
        print(f"    • {adviser['title']}: {adviser['name']}")
    print(f"  Resource Categories: {len(data['planning_resources'])}")
    for resource in data['planning_resources']:
        print(f"    • {resource['category']}: {len(resource['links'])} resources")
    print(f"  Advising Options: {len(data['advising_options'])}")

def show_sample(data):
    """Show sample entries"""
    if not data:
        return
    
    print(f"\nSample Entries:")
    print("-" * 60)
    
    # Show first adviser
    if data['advisers']:
        adviser = data['advisers'][0]
        print(f"\nAdviser: {adviser['title']}")
        print(f"  Name: {adviser['name']}")
        if adviser['bio']:
            print(f"  Bio: {adviser['bio'][0][:150]}...")
    
    # Show first resource category
    if data['planning_resources']:
        resource = data['planning_resources'][0]
        print(f"\nResource Category: {resource['category']}")
        if resource['links']:
            print(f"  Sample link: {resource['links'][0]['text']}")

# Main execution
if __name__ == "__main__":
    print("\nStarting Coursera Advising and Planning scraper...")
    result = scrape_coursera_advising()
    
    if result:
        print_statistics(result)
        show_sample(result)
    
    print("\n✓ Done!")