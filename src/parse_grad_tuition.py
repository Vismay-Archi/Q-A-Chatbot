import json
import re

INPUT_FILE = "iit_mies_grad_tuition_fees.json"
OUTPUT_FILE = "iit_mies_grad_tuition_structured.json"

def money_amount_and_unit(s: str):
    """
    "$1,851" -> (1851, None)
    "$2,314 /per course" -> (2314, "per course")
    "$50 / per course" -> (50, "per course")
    """
    m = re.search(r"\$(\d[\d,]*)", s)
    if not m:
        return None, None
    amount = int(m.group(1).replace(",", ""))
    unit = None
    if "/" in s:
        unit = s.split("/", 1)[1].strip()
        # normalize spacing like "per course"
        unit = re.sub(r"\s+", " ", unit)
    return amount, unit

def looks_like_money(s: str) -> bool:
    return bool(re.search(r"\$\s*\d", s))

def looks_like_fee_name(s: str) -> bool:
    # "Activity Fee »", "Student Service Fee »", "UPass Fee »"
    return "Fee" in s

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw = json.load(f)

items = raw["sections"]["Tuition Rates 2025–2026"]

parsed = {
    "source_url": raw["source_url"],
    "page_title": raw.get("page_title"),
    "tuition_rates": [],
    "fees": []
}

# ---- 1) Parse tuition rates ----
# We treat everything before "Per Semester" as tuition-rates territory.
i = 0
tuition_unit_default = None

while i < len(items):
    token = items[i]

    if token == "Per Credit Hour":
        tuition_unit_default = "per credit hour"
        i += 1
        continue

    if token == "Per Semester":
        break  # tuition section ends here

    # Example patterns:
    # "Summer Courses (Summer 2025)", "$1,780"
    # "Fall 2025 ...", "$1,851"
    # "Short Courses", "$2,314 /per course"
    # "CAPS Courses", "$1,851 /per course"
    if i + 1 < len(items) and looks_like_money(items[i + 1]):
        label = token
        money = items[i + 1]
        amount, unit = money_amount_and_unit(money)

        if amount is not None:
            parsed["tuition_rates"].append({
                "label": label,
                "amount": amount,
                "unit": unit if unit else tuition_unit_default
            })
            i += 2
            continue

    i += 1

# ---- 2) Parse fees (Per Semester and beyond) ----
# Now we parse fee blocks. A fee block starts at "<Something> Fee" and continues
# until the next fee name or the end.
current_fee = None
current_rows = []

def flush_fee():
    global current_fee, current_rows
    if current_fee and current_rows:
        parsed["fees"].append({
            "fee_name": current_fee,
            "rows": current_rows
        })
    current_fee = None
    current_rows = []

# Advance i to "Per Semester" marker (if not already there)
while i < len(items) and items[i] != "Per Semester":
    i += 1

# Skip "Per Semester"
if i < len(items) and items[i] == "Per Semester":
    i += 1

# Helper to detect a new fee header token
def is_fee_header(tok: str) -> bool:
    return looks_like_fee_name(tok) and ("Fee" in tok)

while i < len(items):
    tok = items[i]

    # Start of a new fee
    if is_fee_header(tok):
        flush_fee()
        # remove the "»" if present
        current_fee = tok.replace("»", "").strip()
        i += 1
        continue

    # A common pattern inside fee blocks:
    # status/label tokens followed by money token
    # e.g. "Full time", "$125"
    if current_fee and i + 1 < len(items) and looks_like_money(items[i + 1]):
        row_label = tok
        money = items[i + 1]
        amount, unit = money_amount_and_unit(money)

        current_rows.append({
            "label": row_label,
            "amount": amount,
            "unit": unit
        })
        i += 2
        continue

    # Sometimes the money appears later; we just move forward
    i += 1

flush_fee()

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2)

print(f"Saved: {OUTPUT_FILE}")
print(f"Tuition rates parsed: {len(parsed['tuition_rates'])}")
print(f"Fees parsed: {len(parsed['fees'])}")

