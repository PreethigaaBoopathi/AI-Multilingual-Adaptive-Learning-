import re
from pathlib import Path
import fitz

doc = fitz.open('data/uploads/22IT402-U1-LM3.pdf')
pages_text = [page.get_text() for page in doc]
all_text = "\n".join(pages_text)

# Test cleaning noise
clean_lines = []
for l in all_text.split('\n'):
    l_str = l.strip()
    if not l_str:
        continue
    if re.match(r"^[0-9]{2}[A-Za-z]{2,4}[0-9]{3,4}", l_str, re.IGNORECASE):
        continue
    if re.match(r"^UNIT\s+[0-9IVXLCDM]+", l_str, re.IGNORECASE):
        continue
    if re.match(r"^Page\s+\d+", l_str, re.IGNORECASE):
        continue
    clean_lines.append(l_str)

print("Total cleaned lines:", len(clean_lines))
print("Sample cleaned lines (first 10):")
for l in clean_lines[:10]:
    print(" -", l)
