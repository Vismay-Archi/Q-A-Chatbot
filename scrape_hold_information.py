import json
import re
import pandas as pd

URL = "https://www.iit.edu/registrar/registration/hold-information"

def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip()
    # remove weird non-breaking spaces etc.
    s = s.replace("\xa0", " ")
    return s

def to_bool_checkmark(cell: str) -> bool:
    # IIT table sometimes renders ✓ or blank
    c = clean_text(cell)
    return "✓" in c

# Pull all HTML tables from the page
tables = pd.read_html(URL)

# Find the table that contains "Hold Description"
target = None
for df in tables:
    cols = [clean_text(c).lower() for c in df.columns]
    if any("hold description" in c for c in cols):
        target = df
        break

if target is None:
    raise RuntimeError("Couldn't find the hold table. The page structure may have changed.")

# Normalize column names
target.columns = [clean_text(c) for c in target.columns]

# Expected columns (based on page content):
# Hold Description | Registration Prohibited | Transcript Withheld | Responsible Office/Originator | Contact Information
# Some versions may merge office+contact; we handle both.

rows = []
for _, r in target.iterrows():
    row = {k: clean_text(v) for k, v in r.to_dict().items()}

    hold_desc = row.get("Hold Description", "")
    reg_prohib = row.get("Registration Prohibited", "")
    transcript = row.get("Transcript Withheld", "")
    office = row.get("Responsible Office/Originator", "")
    contact = row.get("Contact Information", "")

    # If the site merged office+contact into one column, fall back
    if not office and "Responsible" not in " ".join(target.columns):
        # try best-effort: any extra columns
        pass

    # Some rows have "OR ..." in office/contact; keep as a list
    def split_or(s: str):
        parts = [p.strip(" ,") for p in re.split(r"\bOR\b", s) if p.strip()]
        return parts if len(parts) > 1 else [s] if s else []

    rows.append({
        "hold_description": hold_desc,
        "registration_prohibited": to_bool_checkmark(reg_prohib),
        "transcript_withheld": to_bool_checkmark(transcript),
        "responsible_office": split_or(office),
        "contact_info": split_or(contact),
        "source_url": URL
    })

out = {
    "source_url": URL,
    "records": rows
}

print("Hold records extracted:", len(rows))
print("Sample:", rows[:3])

with open("iit_hold_information.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("Saved: iit_hold_information.json")

