import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import fitz  # PyMuPDF
from config import MEDIA_DIR

def extract_from_pdf(pdf_path: Path, filename: str, custom_id: Optional[str] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts text, chapters, sections, embedded images/figures, tables, and metadata 
    from any PDF textbook dynamically.
    Preserves exact page-level provenance for every content unit.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        raise ValueError(f"Unable to read or parse PDF file: {str(e)}")

    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValueError("The uploaded PDF document is empty (0 pages).")

    file_size_bytes = pdf_path.stat().st_size
    file_id = custom_id or f"pdf_{abs(hash(filename + str(file_size_bytes))) % 1000000}"
    media_dir = MEDIA_DIR / file_id
    media_dir.mkdir(parents=True, exist_ok=True)

    # Document-level metadata
    doc_meta = doc.metadata or {}
    pdf_doc_title = doc_meta.get("title")
    if pdf_doc_title and pdf_doc_title.strip().lower() in ("untitled", "document", "microsoft word", "powerpoint presentation", "presentation", ""):
        pdf_doc_title = None
    clean_title = (pdf_doc_title.strip() if pdf_doc_title and pdf_doc_title.strip() else None) or \
                  filename.replace(".pdf", "").replace(".PDF", "").replace("_", " ").replace("-", " ").title()

    pages_text = []
    media_items = []
    extracted_tables = []

    # 1. Page-by-page extraction of text, images, and tables
    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]

        # Extract text
        text = page.get_text("text").strip()
        pages_text.append({"page": page_num, "text": text})

        # Extract embedded images / figures
        try:
            image_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                base_img = doc.extract_image(xref)
                if not base_img:
                    continue
                image_bytes = base_img.get("image")
                image_ext = base_img.get("ext", "png")
                width = base_img.get("width", 0)
                height = base_img.get("height", 0)

                # Filter out tiny icon noise (e.g. < 40px)
                if width < 40 and height < 40:
                    continue

                img_filename = f"page_{page_num}_img_{img_idx + 1}.{image_ext}"
                img_path = media_dir / img_filename
                with open(img_path, "wb") as f_img:
                    f_img.write(image_bytes)

                media_url = f"/media/{file_id}/{img_filename}"
                media_item = {
                    "id": f"med_{file_id}_p{page_num}_{img_idx + 1}",
                    "file_id": file_id,
                    "filename": filename,
                    "source_type": "pdf",
                    "content_type": "image",
                    "page": page_num,
                    "slide": None,
                    "timestamp": None,
                    "media_path": media_url,
                    "media_filename": img_filename,
                    "width": width,
                    "height": height,
                    "format": image_ext,
                    "description": f"Embedded figure/diagram extracted from page {page_num} of {filename}"
                }
                media_items.append(media_item)
        except Exception as img_err:
            # Continue text extraction even if a specific image format is corrupt
            pass

        # Extract structured tables if available in PyMuPDF
        try:
            if hasattr(page, "find_tables"):
                tabs = page.find_tables()
                for t_idx, tab in enumerate(tabs):
                    df = tab.extract()
                    if df and len(df) > 1:
                        table_lines = []
                        header = " | ".join([str(c or "").strip() for c in df[0]])
                        table_lines.append(header)
                        table_lines.append(" | ".join(["---"] * len(df[0])))
                        for row in df[1:]:
                            table_lines.append(" | ".join([str(c or "").strip() for c in row]))
                        table_str = "\n".join(table_lines)
                        extracted_tables.append({
                            "page": page_num,
                            "table_index": t_idx + 1,
                            "content": f"Table (Page {page_num}):\n{table_str}"
                        })
        except Exception:
            pass

    # Extract native TOC before closing document
    toc = doc.get_toc() if hasattr(doc, "get_toc") else []

    doc.close()

    # Check for empty document text
    has_text = any(p["text"] for p in pages_text)
    if not has_text and not media_items:
        raise ValueError("Unable to extract content from this PDF. The document contains no readable text or images.")

    # 2. Dynamic chapter and section hierarchy detection
    chapters = []

    # 2a. Use native PDF bookmarks/outline if available and comprehensive
    if toc and len(toc) >= 2:
        curr_ch = None
        for item in toc:
            level, toc_title, p_num = item[0], item[1].strip(), item[2]
            if not toc_title:
                continue
            if level == 1:
                ch_idx = len(chapters) + 1
                curr_ch = {
                    "id": f"ch_{ch_idx}",
                    "number": ch_idx,
                    "title": toc_title,
                    "page_start": p_num,
                    "page_end": p_num,
                    "sections": []
                }
                chapters.append(curr_ch)
            elif level >= 2 and curr_ch:
                sec_idx = len(curr_ch["sections"]) + 1
                curr_ch["sections"].append({
                    "id": f"sec_{curr_ch['number']}_{sec_idx}",
                    "title": toc_title,
                    "page_start": p_num,
                    "page_end": p_num,
                    "content": ""
                })

    # 2b. If no native TOC, use smart text pattern analysis
    if not chapters:
        explicit_ch_pattern = re.compile(
            r"^(?:Chapter|Module|Topic)\s+([0-9IVXLCDM]+)[\s:\-–—]+(.*)$",
            re.IGNORECASE
        )
        numbered_heading_pattern = re.compile(r"^(\d+)\.\s*(.*)$")
        section_pattern = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?[:\s\-–—]*(.*)$")
        explicit_sec_pattern = re.compile(r"^Section:\s+(.*)$", re.IGNORECASE)

        non_chapter_words = {
            "start", "recursively", "choose", "if", "it", "no", "let", "this", "the", "here",
            "once", "delete", "deletion", "add", "given", "when", "then", "where", "for", "while", "using",
            "following", "such", "an", "a", "after", "before", "in", "on", "at", "by", "to",
            "we", "you", "they", "there", "step", "note", "example", "insert", "insertion", "remove",
            "eliminate", "create", "ensure", "sort", "initialize", "iterate", "terminate",
            "original", "check", "pick", "repeat", "continue", "look", "how", "what", "why",
            "return", "apply", "define", "find", "consider", "assume", "show", "calculate",
            "search", "operation", "operations", "traversal", "method", "methods"
        }
        sentence_phrases = [
            "from the", "of the", "in the", "to be", "that we", "is used", "are used",
            "will be", "in order to", "based on", "due to", "according to", "can be",
            "should be", "equal to", "same as", "take a", "takes a", "takes constant",
            "by using", "so now", "have a look", "as shown", "with the", "over the",
            "points to", "steps for", "for each"
        ]

        chapters_dict = {}
        ordered_chapters = []

        def get_or_create_chapter(ch_num: int, title: str, p_num: int):
            clean_title = title.strip().title() if title else f"Chapter {ch_num}"
            clean_title = clean_title.rstrip(":-–— ")

            if ch_num in chapters_dict:
                ch = chapters_dict[ch_num]
                cur_len = len(ch["title"].split())
                new_len = len(clean_title.split())
                # If existing chapter title was generic ("Chapter 1", "Unit 1") or single-word, upgrade when richer title is discovered
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

        current_ch = None

        for p_info in pages_text:
            p_num = p_info["page"]
            text = p_info["text"]
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            for line_idx, line in enumerate(lines):
                # Filter out unit lesson plan curriculum header lines (e.g., 'UNIT V & LP 1 ...' or '22IT402 - DATA STRUCTURES II')
                if re.match(r"^UNIT\s+[0-9IVXLCDM]+", line, re.IGNORECASE) or re.match(r"^[0-9]{2}[A-Za-z]{2,4}[0-9]{2,4}\b", line, re.IGNORECASE):
                    continue

                # Check Explicit Section: 'Section: Candidate Keys...'
                exp_sec = explicit_sec_pattern.match(line)
                if exp_sec:
                    sec_title = exp_sec.group(1).strip()
                    sec_title = re.sub(r"\(Pages\s+\d+[\-–—\d]*\)", "", sec_title).strip().rstrip(":-–— ")
                    if not current_ch:
                        current_ch = get_or_create_chapter(1, "Core Concepts", p_num)
                    sec_id = f"sec_{current_ch['number']}_{len(current_ch['sections']) + 1}"
                    if not any(s["title"] == sec_title for s in current_ch["sections"]):
                        current_ch["sections"].append({
                            "id": sec_id,
                            "title": sec_title,
                            "page_start": p_num,
                            "page_end": p_num,
                            "content": ""
                        })
                    continue

                # Check Section Pattern: '1.1 Types of Operations' or multi-line '1.1\nNeed for Trie Data Structure?'
                sec_match = section_pattern.match(line)
                if sec_match:
                    ch_num = int(sec_match.group(1))
                    sec_raw_num = f"{sec_match.group(1)}.{sec_match.group(2)}"
                    if sec_match.group(3):
                        sec_raw_num += f".{sec_match.group(3)}"
                    sec_body = sec_match.group(4).strip().lstrip(".:-–— ").rstrip(":-–— ")

                    # Lookahead: if section number was on its own line, inspect the next line for the title
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
                    current_ch = parent_ch
                    continue

                # Check Explicit Chapter: 'Chapter 1: ...'
                exp_ch = explicit_ch_pattern.match(line)
                if exp_ch:
                    raw_num = exp_ch.group(1)
                    try:
                        ch_num = int(raw_num)
                    except ValueError:
                        roman_map = {'I':1, 'II':2, 'III':3, 'IV':4, 'V':5, 'VI':6, 'VII':7, 'VIII':8, 'IX':9, 'X':10}
                        ch_num = roman_map.get(raw_num.upper(), len(ordered_chapters) + 1)
                    title = exp_ch.group(2).strip().rstrip(":-–— ")
                    current_ch = get_or_create_chapter(ch_num, title, p_num)
                    continue

                # Check Numbered Headings: '1. PREFIX BASED SEARCH' or '1.\nPREFIX BASED SEARCH'
                num_match = numbered_heading_pattern.match(line)
                if num_match:
                    ch_num = int(num_match.group(1))
                    candidate_title = num_match.group(2).strip()

                    # Lookahead: if number was alone on the line, look at the next line
                    if not candidate_title and line_idx + 1 < len(lines):
                        next_line = lines[line_idx + 1].strip()
                        if next_line and not re.match(r"^\d+(\.\d+)*", next_line) and len(next_line) < 80:
                            candidate_title = next_line

                    if candidate_title:
                        candidate_title = candidate_title.strip().rstrip(":-–— ")
                        first_word = candidate_title.split()[0].lower() if candidate_title else ""
                        prev_line = lines[line_idx - 1] if line_idx > 0 else ""
                        is_sublist = prev_line.endswith(":")

                        is_sentence = (
                            first_word in non_chapter_words or
                            is_sublist or
                            any(phrase in candidate_title.lower() for phrase in sentence_phrases) or
                            len(candidate_title) > 70 or
                            candidate_title.endswith((".", ";", "?"))
                        )

                        if not is_sentence:
                            current_ch = get_or_create_chapter(ch_num, candidate_title, p_num)
                            continue

        chapters = ordered_chapters

    # If no explicit chapter headings found, partition logically into topic blocks
    if not chapters:
        pages_per_ch = max(1, (total_pages + 3) // 4)
        for i in range(0, total_pages, pages_per_ch):
            ch_n = (i // pages_per_ch) + 1
            p_st = i + 1
            p_en = min(i + pages_per_ch, total_pages)
            chapters.append({
                "id": f"ch_{ch_n}",
                "number": ch_n,
                "title": f"Section {ch_n}: Core Content (Pages {p_st}–{p_en})",
                "page_start": p_st,
                "page_end": p_en,
                "sections": [{
                    "id": f"sec_{ch_n}_1",
                    "title": f"Reading (Pages {p_st}–{p_en})",
                    "page_start": p_st,
                    "page_end": p_en,
                    "content": ""
                }]
            })

    # Ensure clean page boundaries for all chapters and sections
    for i, ch in enumerate(chapters):
        if i < len(chapters) - 1:
            next_start = chapters[i + 1]["page_start"]
            ch["page_end"] = max(ch["page_start"], next_start - 1 if next_start > ch["page_start"] else ch["page_start"])
        else:
            ch["page_end"] = total_pages

        # Fix section boundaries within chapter
        for s_idx, sec in enumerate(ch["sections"]):
            if s_idx < len(ch["sections"]) - 1:
                next_sec_start = ch["sections"][s_idx + 1]["page_start"]
                sec["page_end"] = max(sec["page_start"], next_sec_start if next_sec_start >= sec["page_start"] else sec["page_start"])
            else:
                sec["page_end"] = ch["page_end"]

    # 3. Create unified knowledge chunks with exact page provenance
    chunks = []
    chunk_counter = 1

    for p_info in pages_text:
        p_num = p_info["page"]
        text = p_info["text"]
        if not text:
            continue

        matched_ch = chapters[0]
        for ch in chapters:
            if ch["page_start"] <= p_num <= ch["page_end"]:
                matched_ch = ch
                break

        raw_paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
        if not raw_paras:
            raw_paras = [text]

        # Clean noise banners (e.g. '22IT402 - DATA STRUCTURES II', 'UNIT I & LP 3') from paragraphs
        cleaned_paras = []
        for raw_p in raw_paras:
            lines = [l.strip() for l in raw_p.split("\n") if l.strip()]
            filtered_lines = []
            for l in lines:
                if re.match(r"^[0-9]{2}[A-Za-z]{2,4}[0-9]{2,4}\b", l, re.IGNORECASE):
                    continue
                if re.match(r"^UNIT\s+[0-9IVXLCDM]+\b(?:\s*&\s*LP\s*\d+)?", l, re.IGNORECASE):
                    continue
                filtered_lines.append(l)
            clean_p = "\n".join(filtered_lines).strip()
            if len(clean_p) > 20:
                cleaned_paras.append(clean_p)
        if not cleaned_paras:
            cleaned_paras = [text]

        for para in cleaned_paras:
            matched_sec_title = "General Content"
            matched_sec_id = "sec_gen"

            if matched_ch["sections"]:
                matched_sec = matched_ch["sections"][0]
                # Check if paragraph explicitly begins with or contains a section's title/number
                found_sec = None
                for sec in matched_ch["sections"]:
                    sec_num_match = re.match(r"^(\d+\.\d+(?:\.\d+)*)", sec["title"])
                    if sec_num_match and (para.startswith(sec_num_match.group(1)) or sec["title"] in para):
                        found_sec = sec
                        break
                if found_sec:
                    matched_sec = found_sec
                else:
                    for sec in matched_ch["sections"]:
                        if sec["page_start"] <= p_num <= sec["page_end"]:
                            matched_sec = sec
                            break
                matched_sec_title = matched_sec["title"]
                matched_sec_id = matched_sec["id"]

            chunk_id = f"chk_{file_id}_{chunk_counter}"
            chunks.append({
                "id": chunk_id,
                "textbook_id": file_id,
                "material_id": file_id,
                "source_type": "pdf",
                "filename": filename,
                "chapter_id": matched_ch["id"],
                "chapter_title": matched_ch["title"],
                "section_id": matched_sec_id,
                "section_title": matched_sec_title,
                "page": p_num,
                "slide_number": None,
                "start_time": None,
                "end_time": None,
                "timestamp_str": None,
                "content_type": "text",
                "content": para,
                "media_path": None,
                "metadata": {
                    "source": "pdf_page_text",
                    "page_number": p_num,
                    "filename": filename
                }
            })
            chunk_counter += 1

    # Add extracted tables as structured chunks
    for tbl in extracted_tables:
        t_page = tbl["page"]
        matched_ch = chapters[0]
        for ch in chapters:
            if ch["page_start"] <= t_page <= ch["page_end"]:
                matched_ch = ch
                break

        chunks.append({
            "id": f"chk_{file_id}_tbl_{chunk_counter}",
            "textbook_id": file_id,
            "material_id": file_id,
            "source_type": "pdf",
            "filename": filename,
            "chapter_id": matched_ch["id"],
            "chapter_title": matched_ch["title"],
            "section_id": "sec_table",
            "section_title": f"Structured Table (Page {t_page})",
            "page": t_page,
            "slide_number": None,
            "start_time": None,
            "end_time": None,
            "timestamp_str": None,
            "content_type": "table",
            "content": tbl["content"],
            "media_path": None,
            "metadata": {
                "source": "pdf_table",
                "page_number": t_page,
                "filename": filename
            }
        })
        chunk_counter += 1

    # Add embedded image references as content units
    for img_item in media_items:
        i_page = img_item["page"]
        matched_ch = chapters[0]
        for ch in chapters:
            if ch["page_start"] <= i_page <= ch["page_end"]:
                matched_ch = ch
                break

        chunks.append({
            "id": f"chk_{file_id}_img_{chunk_counter}",
            "textbook_id": file_id,
            "material_id": file_id,
            "source_type": "pdf",
            "filename": filename,
            "chapter_id": matched_ch["id"],
            "chapter_title": matched_ch["title"],
            "section_id": "sec_figure",
            "section_title": f"Figure / Visual Diagram (Page {i_page})",
            "page": i_page,
            "slide_number": None,
            "start_time": None,
            "end_time": None,
            "timestamp_str": None,
            "content_type": "image",
            "content": f"[Embedded Visual Diagram / Image from Page {i_page} of {filename}]",
            "media_path": img_item["media_path"],
            "metadata": {
                "source": "pdf_embedded_image",
                "page_number": i_page,
                "filename": filename,
                "image_url": img_item["media_path"],
                "width": img_item.get("width"),
                "height": img_item.get("height")
            }
        })
        chunk_counter += 1

    metadata = {
        "id": file_id,
        "title": clean_title,
        "filename": filename,
        "source_type": "pdf",
        "total_pages": total_pages,
        "total_slides": None,
        "duration_seconds": None,
        "file_size_bytes": file_size_bytes,
        "extracted_images_count": len(media_items),
        "extracted_transcripts_count": 0,
        "extracted_tables_count": len(extracted_tables),
        "media_items": media_items,
        "chapters": chapters,
        "created_at": datetime.now().isoformat()
    }

    return metadata, chunks, media_items
