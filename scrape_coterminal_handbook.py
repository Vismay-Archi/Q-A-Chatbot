import requests
import pdfplumber
import json
import re
from io import BytesIO

PDF_URL = "https://webmaster.iit.edu/files/graduate-academic-affairs/co-terminal-student-handbook.pdf"
OUTPUT_JSON = "coterminal_handbook.json"

SECTION_HEADER_RE = re.compile(
    r"^(?P<num>[IVXLC]+)\.\s+(?P<title>.+)$",
    re.IGNORECASE
)

SENTENCE_END_RE = re.compile(r'[\.?!][)"\]]?$')

def download_pdf(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return BytesIO(resp.content)

def extract_sections(pdf_fileobj):
    sections = []
    current_section = None
    buffer = []  # accumulate pieces of a sentence/paragraph

    def flush_buffer(target_section):
        nonlocal buffer
        if target_section is None:
            buffer = []
            return
        if not buffer:
            return
        text = " ".join(buffer).strip()
        if text:
            target_section["paragraphs"].append(text)
            if target_section["full_text"]:
                target_section["full_text"] += " "
            target_section["full_text"] += text
        buffer = []

    with pdfplumber.open(pdf_fileobj) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            lines = [l.strip() for l in page_text.splitlines() if l.strip()]

            for line in lines:
                # Check for section header
                m = SECTION_HEADER_RE.match(line)
                if m:
                    # finish any in-progress sentence/paragraph for the previous section
                    flush_buffer(current_section)

                    if current_section:
                        sections.append(current_section)

                    title = f"{m.group('num').upper()}. {m.group('title').strip()}"
                    current_section = {
                        "section_id": m.group('num').upper(),
                        "title": title,
                        "start_page": page_index + 1,
                        "paragraphs": [],
                        "full_text": ""
                    }
                    continue

                if current_section is None:
                    # ignore text before the first detected section
                    continue

                # Add this line to the buffer (sentence builder)
                buffer.append(line)

                # If this line *ends* with a sentence terminator, flush as one paragraph entry
                if SENTENCE_END_RE.search(line):
                    flush_buffer(current_section)

        # end of document
        flush_buffer(current_section)
        if current_section:
            sections.append(current_section)

    return sections

def build_corpus(sections):
    return {
        "source": "Illinois Tech Co-Terminal Student Handbook",
        "version": "Updated September 2020",
        "sections": sections
    }

def main():
    pdf_fileobj = download_pdf(PDF_URL)
    sections = extract_sections(pdf_fileobj)
    corpus = build_corpus(sections)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print("✓ Saved to coterminal_handbook.json")

if __name__ == "__main__":
    main()

