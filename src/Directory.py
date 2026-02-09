
import requests
from bs4 import BeautifulSoup
import json
import time
import re

base_url = "https://www.iit.edu/directory/people"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def extract_person_from_article(article):
    """Extract complete person data from listing page"""
    try:
        person = {}
        
        # Get name and profile link
        name_link = article.find('h3', class_='arrow-link')
        if not name_link:
            name_link = article.find('h2')
        if not name_link:
            name_link = article.find('a', href=re.compile(r'/directory/people/'))
        
        if name_link:
            link_tag = name_link.find('a') if name_link.name != 'a' else name_link
            if link_tag:
                person['name'] = link_tag.get_text(strip=True)
                person['profile_url'] = 'https://www.iit.edu' + link_tag.get('href') if link_tag.get('href', '').startswith('/') else link_tag.get('href')
        
        if not person.get('name'):
            return None
        
        # Get tags (Faculty/Staff)
        tags = article.find_all('a', href=re.compile(r'profile_type='))
        person['tags'] = [tag.get_text(strip=True) for tag in tags] if tags else []
        
        # Get positions - THIS IS THE KEY FIX!
        positions_list = article.find('span', class_='positions-list')
        if positions_list:
            position_items = positions_list.find_all('li')
            person['positions'] = [li.get_text(strip=True) for li in position_items if li.get_text(strip=True)]
        else:
            person['positions'] = []
        
        # Get email
        email_link = article.find('a', href=re.compile(r'mailto:'))
        if email_link:
            person['email'] = email_link.get('href').replace('mailto:', '')
            # Try to extract phone from same container
            email_container = email_link.parent
            if email_container:
                email_text = email_container.get_text()
                phone_match = re.search(r'(\d{3}[\.\-]?\d{3}[\.\-]?\d{4})', email_text)
                if phone_match:
                    person['phone'] = phone_match.group(1)
                else:
                    person['phone'] = ""
            else:
                person['phone'] = ""
        else:
            person['email'] = ""
            person['phone'] = ""
        
        return person
    except Exception as e:
        return None

def scrape_all_people():
    """Scrape all people from listing pages"""
    all_people = []
    page_num = 0
    max_pages = 200
    no_results_count = 0
    
    print("IIT People Directory Scraper - FIXED VERSION")
    print("=" * 60)
    print("Scraping all people with positions from listing pages")
    print("=" * 60)
    
    while page_num < max_pages:
        url = f"{base_url}?page={page_num}"
        print(f"\nPage {page_num}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"  ✗ Error: Status code {response.status_code}")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('article', class_='profile-item')
            
            if not articles:
                no_results_count += 1
                print(f"  ✗ No articles found")
                if no_results_count >= 3:
                    print(f"\n  No results for {no_results_count} consecutive pages. Stopping.")
                    break
                page_num += 1
                time.sleep(1)
                continue
            
            no_results_count = 0
            print(f"  Found {len(articles)} articles")
            
            page_people = []
            for article in articles:
                person = extract_person_from_article(article)
                if person:
                    page_people.append(person)
            
            # Count how many have positions
            with_positions = len([p for p in page_people if p.get('positions')])
            
            print(f"  ✓ Extracted {len(page_people)} people ({with_positions} with positions)")
            all_people.extend(page_people)
            print(f"  Total so far: {len(all_people)} people")
            
            page_num += 1
            time.sleep(0.5)  # Be nice to the server
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            no_results_count += 1
            if no_results_count >= 3:
                break
            page_num += 1
            time.sleep(2)
            continue
    
    # Remove duplicates
    seen_urls = set()
    unique_people = []
    for person in all_people:
        url = person.get('profile_url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_people.append(person)
    
    print(f"\n{'=' * 60}")
    print(f"Scraping complete!")
    print(f"{'=' * 60}")
    
    return unique_people

# Main execution
all_people = scrape_all_people()

# Save results
output_data = {
    'url': base_url,
    'scrape_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    'total_people': len(all_people),
    'people': all_people
}

with open('iit_people_complete.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

print(f"\n✓ Data saved to iit_people_complete.json")

# Statistics
with_positions = len([p for p in all_people if p.get('positions')])
faculty = len([p for p in all_people if 'Faculty' in p.get('tags', [])])
staff = len([p for p in all_people if 'Staff' in p.get('tags', [])])

print(f"\nStatistics:")
print(f"  Total People: {len(all_people)}")
print(f"  Faculty: {faculty}")
print(f"  Staff: {staff}")
print(f"  With Positions: {with_positions}")
print(f"  With Email: {len([p for p in all_people if p.get('email')])}")
print(f"  With Phone: {len([p for p in all_people if p.get('phone')])}")

# Show a sample
if all_people:
    print(f"\nSample entry:")
    sample = next((p for p in all_people if p.get('positions')), all_people[0])
    print(json.dumps(sample, indent=2))

print("\nDone!")
