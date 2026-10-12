import fitz
import re

doc = fitz.open('data/uploads/22IT402-U1-LM3.pdf')
for p_idx, page in enumerate(doc):
    text = page.get_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for idx, l in enumerate(lines):
        # Look for section numbers like 1.1, 1.2, etc.
        m = re.match(r"^(\d+\.\d+(?:\.\d+)?)\s*(.*)$", l)
        if m:
            sec_num = m.group(1)
            rest = m.group(2)
            next_l = lines[idx+1] if idx+1 < len(lines) else ""
            print(f"Page {p_idx+1} | Found: '{sec_num}' | rest: '{rest}' | next: '{next_l}'")
        # Look for chapter numbers like 1., 2., etc.
        m_ch = re.match(r"^(\d+)\.\s*(.*)$", l)
        if m_ch and not m:
            ch_num = m_ch.group(1)
            rest = m_ch.group(2)
            next_l = lines[idx+1] if idx+1 < len(lines) else ""
            print(f"Page {p_idx+1} | CHAPTER: '{ch_num}.' | rest: '{rest}' | next: '{next_l}'")
