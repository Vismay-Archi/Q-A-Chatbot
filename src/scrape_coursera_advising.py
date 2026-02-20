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

def extract_adviser_info(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract information about advisers from the main content"""
    advisers = []
    
    main_content = soup.find('article', class_='full-wysiwyg')
    if not main_content:
        return advisers
    
    # Find all h3 headings (adviser titles)
    h3_tags = main_content.find_all('h3')
    
    for h3 in h3_tags:
        title = clean_text(h3.get_text())
        if 'Adviser' in title or 'Program Manager' in title:
            adviser = {
                "title": title,
                "name": "",
                "profile_url": "",
                "bio": [],
                "image": None
            }
            
            # Get the next element (usually a paragraph with a link)
            next_elem = h3.find_next_sibling()
            if next_elem and next_elem.name == 'p':
                link = next_elem.find('a')
                if link:
                    adviser["name"] = clean_text(link.get_text())
                    href = link.get('href', '')
                    if href.startswith('/'):
                        adviser["profile_url"] = f"https://www.iit.edu{href}"
                    else:
                        adviser["profile_url"] = href
                    
                    # Get bio paragraphs after this
                    bio_paragraphs = []
                    current = next_elem.find_next_sibling()
                    while current and current.name == 'p' and not current.find('h3'):
                        text = clean_text(current.get_text())
                        if text and len(text) > 20:  # Avoid very short text
                            bio_paragraphs.append(text)
                        current = current.find_next_sibling()
                    
                    adviser["bio"] = bio_paragraphs
                    adviser["full_bio"] = " ".join(bio_paragraphs)
            
            advisers.append(adviser)
    
    return advisers

def parse_accordion_content(accordion) -> Dict[str, Any]:
    """Parse a single accordion item"""
    # Get title from button
    button = accordion.find('button', class_='accordion__button')
    if not button:
        return None
    
    title_elem = button.find('h3', class_='accordion__button-text')
    title = clean_text(title_elem.get_text() if title_elem else button.get_text())
    
    # Get content
    content = accordion.find('div', class_='accordion__content')
    if not content:
        return None
    
    # Extract paragraphs and list items
    paragraphs = []
    list_items = []
    
    for elem in content.find_all(['p', 'li', 'div'], recursive=True):
        if elem.name == 'div' and elem.find(['p', 'li']):
            continue
        text = clean_text(elem.get_text())
        if text and len(text) > 3:
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
    
    # Check for file attachments (PDFs, docs)
    files = []
    for a in content.find_all('a', href=True):
        href = a.get('href', '')
        if href.endswith(('.pdf', '.docx', '.doc', '.xlsx')):
            files.append({
                "name": clean_text(a.get_text()),
                "url": href if href.startswith('http') else f"https://www.iit.edu{href}",
                "type": href.split('.')[-1] if '.' in href else "file"
            })
    
    return {
        "title": title,
        "content_paragraphs": paragraphs,
        "full_content": " ".join(paragraphs),
        "list_items": list_items,
        "links": links,
        "files": files,
        "images": images
    }

def scrape_coursera_advising():
    """Main scraper function"""
    print("=" * 70)
    print("Coursera Advising and Planning Webpage Scraper")
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
    page_title = clean_text(title_elem.get_text() if title_elem else "Coursera Advising and Planning")
    
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
    
    # Extract introduction
    introduction = []
    intro_section = soup.find('h2', string=re.compile("Introduction", re.I))
    if intro_section:
        intro_content = intro_section.find_next('article', class_='full-wysiwyg')
        if intro_content:
            for p in intro_content.find_all('p'):
                text = clean_text(p.get_text())
                if text:
                    introduction.append(text)
    
    # Extract adviser information
    advisers = extract_adviser_info(soup)
    
    # Extract resource sections (accordions)
    resource_sections = []
    resource_headings = soup.find_all('h2', class_='section-heading__heading')
    
    for heading in resource_headings:
        section_title = clean_text(heading.get_text())
        if not section_title or section_title == "Introduction":
            continue
        
        # Get the subheading if exists
        subheading = None
        parent_div = heading.find_parent('div', class_='section-heading')
        if parent_div:
            subheading_elem = parent_div.find('span', class_='section-heading__subheading')
            if subheading_elem:
                subheading = clean_text(subheading_elem.get_text())
        
        # Find the section div
        section_div = heading.find_next('div', class_='section--accordion')
        if section_div:
            # Find all accordions in this section
            accordions = section_div.find_all('div', class_='accordion')
            
            section_items = []
            for accordion in accordions:
                item = parse_accordion_content(accordion)
                if item:
                    section_items.append(item)
            
            if section_items:
                resource_sections.append({
                    "section_title": section_title,
                    "section_subheading": subheading,
                    "item_count": len(section_items),
                    "items": section_items
                })
                print(f"  ✓ {section_title}: {len(section_items)} items")
    
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
        "main_image": main_image,
        "introduction": introduction,
        "advisers": advisers,
        "resource_sections": resource_sections,
        "total_sections": len(resource_sections),
        "total_resources": sum(section['item_count'] for section in resource_sections),
        "all_page_links": unique_links[:50]  # Limit to first 50 to keep file size reasonable
    }
    
    # Save to JSON following team naming convention
    filename = "iit_coursera_advising.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 70}")
    print("Scraping Complete!")
    print(f"{'=' * 70}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ Total resource sections: {len(resource_sections)}")
    print(f"✓ Total resources: {output_data['total_resources']}")
    print(f"✓ Advisers found: {len(advisers)}")
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
    print(f"Advisers: {len(data['advisers'])}")
    print(f"Resource Sections: {data['total_sections']}")
    print(f"Total Resources: {data['total_resources']}")
    
    print(f"\nAdvisers:")
    for adviser in data['advisers']:
        print(f"  • {adviser['title']}: {adviser['name']}")
    
    print(f"\nResource Sections:")
    for section in data['resource_sections']:
        print(f"  📁 {section['section_title']}")
        print(f"     └─ {section['item_count']} resources")
        # Show first few items as preview
        for i, item in enumerate(section['items'][:2], 1):
            print(f"        {i}. {item['title']}")
        if section['item_count'] > 2:
            print(f"        ... and {section['item_count'] - 2} more")

def show_sample(data):
    """Show a detailed sample of the first resource"""
    if not data:
        return
    
    print(f"\n{'=' * 70}")
    print("SAMPLE RESOURCE (First item from first section)")
    print(f"{'=' * 70}")
    
    if data['resource_sections']:
        first_section = data['resource_sections'][0]
        if first_section['items']:
            first_item = first_section['items'][0]
            
            print(f"Section: {first_section['section_title']}")
            print(f"\nResource: {first_item['title']}")
            print(f"\nContent: {first_item['full_content'][:300]}...")
            
            if first_item.get('links'):
                print(f"\nLinks in this resource: {len(first_item['links'])}")
                for link in first_item['links'][:3]:
                    print(f"  • {link['text']} -> {link['url'][:50]}...")
            
            if first_item.get('files'):
                print(f"\nFiles: {len(first_item['files'])}")
                for file in first_item['files']:
                    print(f"  • {file['name']} ({file['type']})")
    
    if data['advisers']:
        print(f"\n{'=' * 70}")
        print("SAMPLE ADVISER")
        print(f"{'=' * 70}")
        adviser = data['advisers'][0]
        print(f"{adviser['title']}: {adviser['name']}")
        print(f"Profile: {adviser['profile_url']}")
        if adviser['bio']:
            print(f"\nBio: {adviser['bio'][0][:200]}...")

def export_readable_text(data, filename="coursera_advising_readable.txt"):
    """Export a human-readable text version of all content"""
    if not data:
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"{data['page_title']}\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Source: {data['url']}\n")
        f.write(f"Scraped: {data['scrape_date']}\n\n")
        
        if data['advisers']:
            f.write(f"\n{'─' * 80}\n")
            f.write("ADVISERS\n")
            f.write(f"{'─' * 80}\n\n")
            for adviser in data['advisers']:
                f.write(f"{adviser['title']}: {adviser['name']}\n")
                f.write(f"Profile: {adviser['profile_url']}\n")
                if adviser['bio']:
                    f.write("\n".join(adviser['bio']))
                f.write("\n\n")
        
        for section in data['resource_sections']:
            f.write(f"\n{'─' * 80}\n")
            f.write(f"{section['section_title']}\n")
            if section.get('section_subheading'):
                f.write(f"{section['section_subheading']}\n")
            f.write(f"{'─' * 80}\n\n")
            
            for i, item in enumerate(section['items'], 1):
                f.write(f"{i}. {item['title']}\n")
                f.write(f"{'─' * 40}\n")
                f.write(f"{item['full_content']}\n\n")
                
                if item.get('links'):
                    f.write("Links:\n")
                    for link in item['links']:
                        f.write(f"  • {link['text']}: {link['url']}\n")
                
                if item.get('files'):
                    f.write("\nFiles:\n")
                    for file in item['files']:
                        f.write(f"  • {file['name']} ({file['type']})\n")
                f.write("\n")
    
    print(f"\n✓ Readable text exported to: {filename}")

# Main execution
if __name__ == "__main__":
    print("\n🚀 Starting Coursera Advising and Planning webpage scraper...")
    print("This will extract ALL content from the page and save it to JSON.\n")
    
    result = scrape_coursera_advising()
    
    if result:
        print_statistics(result)
        show_sample(result)
        
        # Also export a readable text version for easy viewing
        export_readable_text(result)
    
    print("\n✅ Scraping process completed successfully!")