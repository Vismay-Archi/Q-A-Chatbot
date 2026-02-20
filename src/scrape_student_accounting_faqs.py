# scrape_student_accounting_faqs.py
# Purpose: Extract all content from Student Accounting FAQs webpage
# Output: iit_student_accounting_faqs.json

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

def extract_files_from_element(element) -> List[Dict[str, Any]]:
    """Extract file attachments (PDFs, etc.) from an element"""
    files = []
    if not element:
        return files
    
    # Look for file spans (typical in Drupal sites)
    for file_span in element.find_all('span', class_='file'):
        file_link = file_span.find('a')
        if file_link:
            href = file_link.get('href', '')
            text = clean_text(file_link.get_text())
            if href.startswith('/'):
                href = f"https://www.iit.edu{href}"
            
            # Try to get file size
            file_size = None
            size_text = file_span.find_next_sibling(string=True)
            if size_text and '(' in size_text and ')' in size_text:
                file_size = clean_text(size_text)
            
            files.append({
                "name": text,
                "url": href,
                "size": file_size,
                "type": "pdf" if href.lower().endswith('.pdf') else "document"
            })
    
    # Also look for any direct file links
    for a in element.find_all('a', href=True):
        href = a.get('href', '')
        if href.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
            # Check if we already added this file
            if not any(f['url'] == href for f in files):
                text = clean_text(a.get_text())
                if href.startswith('/'):
                    href = f"https://www.iit.edu{href}"
                files.append({
                    "name": text,
                    "url": href,
                    "size": None,
                    "type": href.split('.')[-1].lower()
                })
    
    return files

def extract_table_data(table) -> Dict[str, Any]:
    """Extract structured data from HTML tables"""
    if not table:
        return None
    
    # Get headers
    headers = []
    thead = table.find('thead')
    if thead:
        header_row = thead.find('tr')
        if header_row:
            for th in header_row.find_all('th'):
                headers.append(clean_text(th.get_text()))
    
    # Get rows
    rows = []
    tbody = table.find('tbody')
    if tbody:
        for tr in tbody.find_all('tr'):
            row_data = {}
            cells = tr.find_all(['td', 'th'])
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = clean_text(cell.get_text())
                else:
                    row_data[f"column_{i}"] = clean_text(cell.get_text())
            if row_data:
                rows.append(row_data)
    
    return {
        "headers": headers,
        "rows": rows,
        "row_count": len(rows)
    }

def parse_faq_sections(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Parse FAQ sections from the page (using h3 headings)"""
    faqs = []
    
    # Find all h3 headings (these are the question topics)
    h3_headings = soup.find_all('h3')
    
    for heading in h3_headings:
        question = clean_text(heading.get_text())
        if not question or "Withdrawing from VS. Dropping" in question:
            continue
        
        # Get content after this heading until next h3
        content_paragraphs = []
        links = []
        files = []
        tables = []
        
        next_elem = heading.find_next_sibling()
        while next_elem and next_elem.name != 'h3':
            if next_elem.name in ['p', 'div', 'ol', 'ul']:
                # Handle subheadings (h6)
                if next_elem.name == 'div' and next_elem.find('h6'):
                    subheading = next_elem.find('h6')
                    if subheading:
                        content_paragraphs.append(f"[{clean_text(subheading.get_text())}]")
                
                # Extract text
                text = clean_text(next_elem.get_text())
                if text and len(text) > 5:
                    content_paragraphs.append(text)
                
                # Extract links
                links.extend(extract_links_from_element(next_elem))
                
                # Extract files
                files.extend(extract_files_from_element(next_elem))
            
            # Extract tables
            if next_elem.name == 'div' and next_elem.find('table'):
                table = next_elem.find('table')
                table_data = extract_table_data(table)
                if table_data:
                    tables.append(table_data)
            
            next_elem = next_elem.find_next_sibling()
        
        if content_paragraphs:
            faqs.append({
                "question": question,
                "answer_paragraphs": content_paragraphs,
                "full_answer": " ".join(content_paragraphs),
                "links": links,
                "files": files,
                "tables": tables
            })
    
    return faqs

def extract_withdraw_vs_drop_table(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract the specific Withdraw vs Drop comparison table"""
    # Find the h3 heading for this section
    heading = soup.find('h3', string=re.compile("Withdrawing from VS. Dropping", re.I))
    if not heading:
        return None
    
    # Get the description paragraph
    description = None
    next_elem = heading.find_next_sibling()
    if next_elem and next_elem.name == 'p':
        description = clean_text(next_elem.get_text())
    
    # Find the table
    table_elem = None
    current = heading
    while current and not table_elem:
        current = current.find_next_sibling()
        if current and current.name == 'div' and current.find('table'):
            table_elem = current.find('table')
            break
    
    if not table_elem:
        return None
    
    table_data = extract_table_data(table_elem)
    
    return {
        "title": "Withdrawing vs. Dropping a Course",
        "description": description,
        "table": table_data
    }

def extract_contact_info(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract contact information for Student Accounting"""
    contact_info = {
        "email": None,
        "phone": None,
        "office": "Student Accounting Office"
    }
    
    # Look for email in the page
    email_links = soup.find_all('a', href=re.compile(r'mailto:sa@'))
    for link in email_links:
        href = link.get('href', '')
        if 'sa@illinoistech.edu' in href:
            contact_info["email"] = "sa@illinoistech.edu"
            break
    
    return contact_info

def extract_sidebar_navigation(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract sidebar navigation links"""
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
    
    return sidebar_links

def scrape_student_accounting_faqs():
    """Main scraper function"""
    print("=" * 70)
    print("Student Accounting FAQs Webpage Scraper")
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
    page_title = clean_text(title_elem.get_text() if title_elem else "Student Accounting FAQs")
    
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
    sidebar_navigation = extract_sidebar_navigation(soup)
    
    # Extract contact information
    contact_info = extract_contact_info(soup)
    
    # Extract the special Withdraw vs Drop table
    withdraw_vs_drop = extract_withdraw_vs_drop_table(soup)
    if withdraw_vs_drop:
        print(f"  ✓ Found Withdraw vs Drop comparison table")
    
    # Extract all FAQ sections
    faqs = parse_faq_sections(soup)
    print(f"  ✓ Found {len(faqs)} FAQ topics")
    
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
        "sidebar_navigation": sidebar_navigation,
        "contact": contact_info,
        "withdraw_vs_drop": withdraw_vs_drop,
        "total_faqs": len(faqs),
        "faqs": faqs,
        "all_page_links": unique_links[:50]  # Limit to first 50 to keep file size reasonable
    }
    
    # Save to JSON following team naming convention
    filename = "iit_student_accounting_faqs.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 70}")
    print("Scraping Complete!")
    print(f"{'=' * 70}")
    print(f"✓ Data saved to: {filename}")
    print(f"✓ Total FAQ topics: {len(faqs)}")
    if withdraw_vs_drop:
        print(f"✓ Withdraw vs Drop comparison table extracted")
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
    print(f"Total FAQ Topics: {data['total_faqs']}")
    
    if data['contact']['email']:
        print(f"Contact Email: {data['contact']['email']}")
    
    print(f"\nFAQ Topics:")
    for i, faq in enumerate(data['faqs'], 1):
        print(f"  {i}. {faq['question']}")
        if faq.get('files'):
            print(f"     └─ {len(faq['files'])} file(s)")
        if faq.get('tables'):
            print(f"     └─ {len(faq['tables'])} table(s)")

def show_sample(data):
    """Show a detailed sample of the first FAQ"""
    if not data or not data['faqs']:
        return
    
    print(f"\n{'=' * 70}")
    print("SAMPLE FAQ (First topic)")
    print(f"{'=' * 70}")
    
    first_faq = data['faqs'][0]
    
    print(f"\nQ: {first_faq['question']}")
    print(f"\nA: {first_faq['full_answer'][:300]}...")
    
    if first_faq.get('files'):
        print(f"\nFiles in this answer: {len(first_faq['files'])}")
        for file in first_faq['files'][:2]:
            print(f"  • {file['name']} ({file.get('size', 'unknown size')})")
    
    if first_faq.get('tables'):
        print(f"\nTables in this answer: {len(first_faq['tables'])}")

def export_readable_text(data, filename="student_accounting_faqs_readable.txt"):
    """Export a human-readable text version of all FAQs"""
    if not data:
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"{'=' * 80}\n")
        f.write(f"{data['page_title']}\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Source: {data['url']}\n")
        f.write(f"Scraped: {data['scrape_date']}\n\n")
        
        if data['contact']['email']:
            f.write(f"Contact: {data['contact']['email']}\n\n")
        
        if data['withdraw_vs_drop']:
            f.write(f"\n{'─' * 80}\n")
            f.write(f"{data['withdraw_vs_drop']['title']}\n")
            f.write(f"{'─' * 80}\n\n")
            if data['withdraw_vs_drop']['description']:
                f.write(f"{data['withdraw_vs_drop']['description']}\n\n")
            
            table = data['withdraw_vs_drop']['table']
            if table:
                # Print table headers
                f.write(f"{table['headers'][0]:<40} | {table['headers'][1]:<40}\n")
                f.write("-" * 81 + "\n")
                # Print table rows
                for row in table['rows']:
                    val1 = list(row.values())[0] if len(row) > 0 else ""
                    val2 = list(row.values())[1] if len(row) > 1 else ""
                    f.write(f"{val1:<40} | {val2:<40}\n")
            f.write("\n")
        
        for i, faq in enumerate(data['faqs'], 1):
            f.write(f"\n{'─' * 80}\n")
            f.write(f"FAQ #{i}: {faq['question']}\n")
            f.write(f"{'─' * 80}\n\n")
            f.write(f"{faq['full_answer']}\n\n")
            
            if faq.get('files'):
                f.write("Files:\n")
                for file in faq['files']:
                    f.write(f"  • {file['name']} - {file['url']}\n")
                f.write("\n")
            
            if faq.get('links'):
                f.write("Related links:\n")
                for link in faq['links']:
                    f.write(f"  • {link['text']}: {link['url']}\n")
                f.write("\n")
    
    print(f"\n✓ Readable text exported to: {filename}")

def export_qa_csv(data, filename="student_accounting_faqs.csv"):
    """Export FAQs to CSV format for easy database import"""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Question', 'Answer', 'Files', 'Links'])
        
        for faq in data['faqs']:
            # Format files as a string
            files_str = "; ".join([f"{f['name']}: {f['url']}" for f in faq.get('files', [])])
            # Format links as a string
            links_str = "; ".join([f"{l['text']}: {l['url']}" for l in faq.get('links', [])])
            
            writer.writerow([
                faq['question'],
                faq['full_answer'],
                files_str,
                links_str
            ])
    
    print(f"\n✓ CSV data exported to: {filename}")

# Main execution
if __name__ == "__main__":
    print("\n🚀 Starting Student Accounting FAQs webpage scraper...")
    print("This will extract ALL content from the page and save it to JSON.\n")
    
    result = scrape_student_accounting_faqs()
    
    if result:
        print_statistics(result)
        show_sample(result)
        
        # Export additional formats for flexibility
        export_readable_text(result)
        export_qa_csv(result)
    
    print("\n✅ Scraping process completed successfully!")