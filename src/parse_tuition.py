import json
import re

with open("iit_mies_ug_tuition_fees.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

sections = raw["sections"]

tuition = []
fees = []

def parse_money(s):
    """
    Extract numeric dollar amount and keep unit text if present.
    Examples:
      "$25,824" -> (25824, None)
      "$50 / per course" -> (50, "per course")
      "$250 / per credit hour" -> (250, "per credit hour")
    """
    m = re.search(r"\$(\d[\d,]*)", s)
    if not m:
        return None, None

    amount = int(m.group(1).replace(",", ""))
    unit = None

    if "/" in s:
        unit = s.split("/", 1)[1].strip()

    return amount, unit

# -------- Parse Tuition Rates --------
items = sections["Tuition Rates 2025–2026"]

i = 0
while i < len(items):
    if items[i].startswith("Admitted"):
        cohort = items[i]
        full_time_amount, _ = parse_money(items[i+1])
        per_credit_amount, _ = parse_money(items[i+2])

        tuition.append({
            "cohort": cohort,
            "full_time_per_semester": full_time_amount,
            "per_credit": per_credit_amount
        })
        i += 3
    else:
        i += 1

# -------- Parse Fees --------
for section_name in ["Mandatory Fees", "Other Fees"]:
    items = sections[section_name]
    i = 0
    while i < len(items) - 1:
        label = items[i]
        value = items[i+1]

        amount, unit = parse_money(value)
        if amount is not None:
            fees.append({
                "fee_name": label,
                "amount": amount,
                "unit": unit,
                "category": section_name
            })
            i += 2
        else:
            i += 1

parsed = {
    "tuition": tuition,
    "fees": fees,
    "source_url": raw["source_url"]
}

with open("iit_mies_ug_tuition_structured.json", "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2)

print("Saved: iit_mies_ug_tuition_structured.json")
print(f"Parsed {len(tuition)} tuition rows and {len(fees)} fees")

