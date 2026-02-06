

import pdfplumber
import json

pdf_path = "C:/Users/visma/Downloads/25-26_StudentHandbook_Final_Aug15.pdf"

print("Opening PDF and extracting data...")
with pdfplumber.open(pdf_path) as pdf:
    
    # Get PDF info
    pdf_info = {
        'total_pages': len(pdf.pages),
        'metadata': pdf.metadata
    }
    print(f"Total Pages: {pdf_info['total_pages']}")
    
    # Extract all text from all pages
    print("Extracting text from all pages...")
    text_data = []
    for i, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()
        text_data.append({
            'page_number': i,
            'text': text
        })
    
    # Extract all tables
    print("Extracting tables...")
    tables_data = []
    for i, page in enumerate(pdf.pages, start=1):
        tables = page.extract_tables()
        if tables:
            for j, table in enumerate(tables, start=1):
                tables_data.append({
                    'page_number': i,
                    'table_number': j,
                    'data': table
                })
    
    print(f"Found {len(tables_data)} tables")
    
    # Save everything to JSON
    complete_data = {
        'pdf_info': pdf_info,
        'text_by_page': text_data,
        'tables': tables_data
    }
    
    with open('extracted_data.json', 'w', encoding='utf-8') as f:
        json.dump(complete_data, f, indent=2, ensure_ascii=False)
    
    print("\n✓ Complete! Data saved to extracted_data.json")
