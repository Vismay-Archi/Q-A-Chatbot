import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import List, Dict, Any

URL = "https://www.iit.edu/student-accounting/faqs"

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

def extract_file_attachments(content_div) -> List[Dict[str, str]]:
    """Extract file attachments (PDFs, etc.) from content"""
    files = []
    if not content_div:
        return files
    
    for file_span in content_div.find_all('span', class_='file'):
        file_link = file_span.find('a')
        if file_link:
            href = file_link.get('href', '')
            text = clean_text(file_link.get_text())
            if href.startswith('/'):
                href = f"https://www.iit.edu{href}"
            
            # Try to get file size
            file_size = None
            size_span = file_span.find_next_sibling(string=True)
            if size_span and '(' in size_span and ')' in size_span:
                file_size = clean_text(size_span)
            
            files.append({
                "name": text,
                "url": href,
                "size": file_size,
                "type": "pdf" if href.lower().endswith('.pdf') else "document"
            })
    return files

def extract_table_data(table) -> List[Dict[str, Any]]:
    """Extract data from HTML tables"""
    table_data = []
    if not table:
        return table_data
    
    headers = []
    header_row = table.find('thead')
    if header_row:
        for th in header_row.find_all('th'):
            headers.append(clean_text(th.get_text()))
    
    tbody = table.find('tbody')
    if tbody:
        for row in tbody.find_all('tr'):
            row_data = {}
            cells = row.find_all(['td', 'th'])
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = clean_text(cell.get_text())
                else:
                    row_data[f"column_{i}"] = clean_text(cell.get_text())
            if row_data:
                table_data.append(row_data)
    
    return table_data

def parse_faq_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Parse FAQ sections from the page"""
    faqs = []
    
    # Find all h3 headings (these are the question categories/topics)
    h3_headings = soup.find_all('h3')
    
    for heading in h3_headings:
        question = clean_text(heading.get_text())
        if not question or "Withdrawing from VS. Dropping" in question:
            continue
        
        # Get content after this heading until next h3
        content = []
        links = []
        files = []
        tables = []
        
        next_elem = heading.find_next_sibling()
        while next_elem and next_elem.name != 'h3':
            if next_elem.name in ['p', 'div', 'ol', 'ul']:
                # Skip if it's just a heading for another section
                if next_elem.name == 'div' and next_elem.find('h6'):
                    subheading = next_elem.find('h6')
                    if subheading:
                        content.append(f"[Note: {clean_text(subheading.get_text())}]")
                
                text = clean_text(next_elem.get_text())
                if text and len(text) > 5:
                    content.append(text)
                
                # Extract links
                links.extend(extract_links_from_content(next_elem))
                
                # Extract file attachments
                files.extend(extract_file_attachments(next_elem))
            
            # Extract tables
            if next_elem.name == 'div' and next_elem.find('table'):
                table = next_elem.find('table')
                table_data = extract_table_data(table)
                if table_data:
                    tables.append({
                        "caption": "Comparison Table",
                        "data": table_data
                    })
            
            next_elem = next_elem.find_next_sibling()
        
        if content:
            faqs.append({
                "question": question,
                "answer": " ".join(content),
                "answer_paragraphs": content,
                "links": links,
                "files": files,
                "tables": tables
            })
    
    return faqs

def extract_contact_info(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract contact information for Student Accounting"""
    contact_info = {
        "email": None,
        "phone": None,
        "office": None
    }
    
    # Look for email in the page
    email_links = soup.find_all('a', href=re.compile(r'mailto:sa@'))
    if email_links:
        for link in email_links:
            href = link.get('href', '')
            if 'sa@illinoistech.edu' in href:
                contact_info["email"] = "sa@illinoistech.edu"
                break
    
    return contact_info

def extract_withdraw_vs_drop_table(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract the specific Withdraw vs Drop comparison table"""
    # Find the h3 heading for this section
    heading = soup.find('h3', string=re.compile("Withdrawing from VS. Dropping", re.I))
    if not heading:
        return None
    
    # Find the table after this heading
    next_elem = heading.find_next_sibling()
    while next_elem and next_elem.name != 'table':
        next_elem = next_elem.find_next_sibling()
        if next_elem and next_elem.name == 'div' and next_elem.find('table'):
            next_elem = next_elem.find('table')
            break
    
    if next_elem and next_elem.name == 'table':
        table_data = extract_table_data(next_elem)
        if table_data:
            return {
                "title": "Withdrawing vs. Dropping a Course",
                "description": clean_text(heading.find_next_sibling('p').get_text() if heading.find_next_sibling('p') else ""),
                "comparison": table_data
            }
    return None

def scrape_student_accounting_faqs():
    """Main scraper function"""
    print("=" * 60)
    print("Student Accounting FAQs Scraper")
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
    page_title = clean_text(title_elem.get_text() if title_elem else "Student Accounting FAQs")
    
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
    
    # Extract contact information
    contact_info = extract_contact_info(soup)
    
    # Extract the special Withdraw vs Drop table
    withdraw_vs_drop = extract_withdraw_vs_drop_table(soup)
    
    # Extract all FAQ sections
    faqs = parse_faq_sections(soup)
    
    # Compile final data
    output_data = {
        "source_url": URL,
        "page_title": page_title,
        "scrape_date": time.strftime('%Y-%m-%d %H:%M:%S'),
        "breadcrumbs": breadcrumbs,
        "contact": contact_info,
        "withdraw_vs_drop": withdraw_vs_drop,
        "total_faqs": len(faqs),
        "faqs": faqs
    }
    
    # Save to JSON following team naming convention
    filename = "iit_student_accounting_faqs.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print("Scraping Complete!")
    print(f"{'=' * 60}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ FAQs found: {len(faqs)}")
    if withdraw_vs_drop:
        print(f"✓ Withdraw vs Drop comparison table extracted")
    
    return output_data

def print_statistics(data):
    """Print statistics about the scraped data"""
    if not data:
        return
    
    print(f"\nStatistics:")
    print(f"  Source: {data['source_url']}")
    print(f"  Scrape Date: {data['scrape_date']}")
    print(f"  Total FAQs: {data['total_faqs']}")
    
    if data['contact']['email']:
        print(f"  Contact: {data['contact']['email']}")
    
    # Show FAQ categories
    print(f"\nFAQ Topics:")
    for i, faq in enumerate(data['faqs'][:5], 1):  # Show first 5
        print(f"  {i}. {faq['question']}")
        if faq.get('files'):
            print(f"     - {len(faq['files'])} file attachments")
    
    if len(data['faqs']) > 5:
        print(f"  ... and {len(data['faqs']) - 5} more")

def show_sample(data):
    """Show sample entries"""
    if not data or not data['faqs']:
        return
    
    print(f"\nSample Entries:")
    print("-" * 60)
    
    # Show first FAQ
    first_faq = data['faqs'][0]
    print(f"\nQ: {first_faq['question']}")
    print(f"A: {first_faq['answer'][:200]}...")
    
    if first_faq.get('files'):
        print(f"\nAttachments:")
        for file in first_faq['files'][:2]:
            print(f"  • {file['name']} ({file.get('size', 'unknown size')})")

# Main execution
if __name__ == "__main__":
    print("\nStarting Student Accounting FAQs scraper...")
    result = scrape_student_accounting_faqs()
    
    if result:
        print_statistics(result)
        show_sample(result)
    
    print("\n✓ Done!")