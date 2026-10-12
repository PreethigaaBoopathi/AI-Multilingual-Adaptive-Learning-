import fitz
import re
import json

doc = fitz.open('data/uploads/22IT402-U1-LM3.pdf')
pages_text = [{"page": i+1, "text": doc[i].get_text()} for i in range(len(doc))]

numbered_heading_pattern = re.compile(r"^(\d+)\.\s*(.*)$")
section_pattern = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?[:\s\-–—]*(.*)$")

chapters_dict = {}
ordered_chapters = []

def get_or_create_chapter(ch_num: int, title: str, p_num: int):
    clean_title = title.strip().title() if title else f"Chapter {ch_num}"
    clean_title = clean_title.rstrip(":-–— ")

    if ch_num in chapters_dict:
        ch = chapters_dict[ch_num]
        # If existing chapter title was generic or very short, and a richer title is found
        cur_len = len(ch["title"].split())
        new_len = len(clean_title.split())
        if (ch["title"].startswith("Chapter ") or ch["title"].startswith("Unit ") or (cur_len <= 1 and new_len > 1)) and title:
            ch["title"] = clean_title
            ch["page_start"] = p_num
        ch["page_end"] = max(ch["page_end"], p_num)
        return ch

    new_ch = {
        "id": f"ch_{ch_num}",
        "number": ch_num,
        "title": clean_title,
        "page_start": p_num,
        "page_end": p_num,
        "sections": []
    }
    chapters_dict[ch_num] = new_ch
    ordered_chapters.append(new_ch)
    return new_ch

non_chapter_words = {
    "start", "recursively", "choose", "if", "it", "no", "let", "this", "the", "here",
    "once", "delete", "add", "given", "when", "then", "where", "for", "while", "using",
    "following", "such", "an", "a", "after", "before", "in", "on", "at", "by", "to",
    "we", "you", "they", "there", "step", "note", "example", "insert", "remove",
    "eliminate", "create", "ensure", "sort", "initialize", "iterate", "terminate",
    "original", "check", "pick", "repeat", "continue", "look", "how", "what", "why",
    "return", "apply", "define", "find", "consider", "assume", "show", "calculate"
}

for p_info in pages_text:
    p_num = p_info["page"]
    text = p_info["text"]
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for line_idx, line in enumerate(lines):
        if re.match(r"^UNIT\s+[0-9IVXLCDM]+", line, re.IGNORECASE) or re.match(r"^[0-9]{2}[A-Za-z]{2,4}[0-9]{3,4}", line):
            continue

        sec_match = section_pattern.match(line)
        if sec_match:
            ch_num = int(sec_match.group(1))
            sec_raw_num = f"{sec_match.group(1)}.{sec_match.group(2)}"
            if sec_match.group(3):
                sec_raw_num += f".{sec_match.group(3)}"
            sec_body = sec_match.group(4).strip().lstrip(".:-–— ").rstrip(":-–— ")

            if not sec_body and line_idx + 1 < len(lines):
                candidate_next = lines[line_idx + 1].strip()
                if candidate_next and not re.match(r"^\d+(\.\d+)*", candidate_next) and len(candidate_next) < 120:
                    if len(candidate_next.split()) <= 15 or candidate_next.endswith("?") or candidate_next.endswith(":"):
                        sec_body = candidate_next.rstrip(":-–— ")

            full_sec_title = f"{sec_raw_num} {sec_body}".strip() if sec_body else sec_raw_num

            parent_ch = get_or_create_chapter(ch_num, f"Chapter {ch_num}", p_num)
            if not any(s["title"] == full_sec_title for s in parent_ch["sections"]):
                sec_count = len(parent_ch["sections"]) + 1
                parent_ch["sections"].append({
                    "id": f"sec_{ch_num}_{sec_count}",
                    "title": full_sec_title,
                    "page_start": p_num,
                    "page_end": p_num,
                    "content": ""
                })
            continue

        num_match = numbered_heading_pattern.match(line)
        if num_match:
            ch_num = int(num_match.group(1))
            cand = num_match.group(2).strip()
            if not cand and line_idx + 1 < len(lines):
                next_l = lines[line_idx + 1].strip()
                if next_l and not re.match(r"^\d+(\.\d+)*", next_l) and len(next_l) < 80:
                    cand = next_l
            if cand:
                first_w = cand.split()[0].lower()
                if first_w not in non_chapter_words and len(cand) < 60:
                    get_or_create_chapter(ch_num, cand, p_num)

print("Extracted Chapters and Sections:")
for ch in ordered_chapters:
    print(f"\n[Chapter {ch['number']}] {ch['title']} (p.{ch['page_start']}-p.{ch['page_end']})")
    for s in ch['sections']:
        print(f"   - {s['title']} (p.{s['page_start']})")
