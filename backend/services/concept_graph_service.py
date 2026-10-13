import re
import json
import hashlib
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime

from config import GEMINI_API_KEY, is_gemini_available, mark_gemini_quota_exhausted, get_gemini_client, FAST_GEMINI_MODELS
from database import (
    save_concept_graph, get_concept_graph, get_concept_details,
    get_chunks_for_textbook, get_textbook
)

# -------------------------------------------------------------------------
# Dynamic Concept Extraction & Graph Generation Service (Innovation 2)
# -------------------------------------------------------------------------

BOILERPLATE_STOP_WORDS = {
    "reading", "figure", "visual diagram", "diagram", "table", "chart",
    "summary", "conclusion", "key points",
    "review questions", "practice questions", "exercises", "self-assessment",
    "quiz", "index", "references", "appendix", "notes", "slide", "page",
    "chapter", "section", "part", "module", "lecture", "unit", "topic",
    "timeline", "timestamp", "keyframe", "video keyframe", "lecture part",
    "part 1", "part 2", "part 3", "part 4",
    "because", "although", "when", "while", "since", "therefore", "however",
    "furthermore", "moreover", "in addition", "for example", "such as",
    "as a result", "in order to", "note that", "the following", "it is",
    "this is", "these are", "we can", "one must", "to understand", "output system",
    "this", "that", "these", "those", "to achieve", "to convert", "to eliminate",
    "to create", "example decomposition", "step", "steps"
}

TRAILING_STOP_WORDS = {
    "are", "is", "was", "were", "the", "a", "an", "on", "in", "at", "by",
    "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up",
    "down", "of", "off", "over", "under", "again", "further", "then", "once"
}

def sanitize_id(name: str) -> str:
    """Generate a clean slug identifier from name."""
    clean = re.sub(r'[^a-zA-Z0-9_]+', '_', name.lower().strip())
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean or "concept"

def clean_title_prefix(title: str) -> str:
    """Strips common structural prefixes from chapter/slide/section titles without truncating real concept names."""
    if not title:
        return ""
    # Normalize unicode hyphens/dashes and quotation marks
    clean = re.sub(r'[\u2010-\u2015\uff0d\u2212\ufffd]', '-', title.strip())
    # Strip [PDF], [PRESENTATION], [VIDEO] tags
    clean = re.sub(r'\[(PDF|PRESENTATION|VIDEO|PPT|MP4|SLIDES?|LECTURE)\]\s*', '', clean, flags=re.IGNORECASE)
    # Strip course codes like 22AI403, CS101, etc.
    clean = re.sub(r'\b[0-9]{2}[A-Za-z]{2,4}[0-9]{3,4}\b[\s:\-]*', '', clean)
    # Strip (Pages X-Y), (Page X), (Slide Y), (Part Z)
    clean = re.sub(r'\(Pages?\s*\d+[\s\-\–\—\d]*\)', '', clean, flags=re.IGNORECASE)
    # Strip timestamp ranges like (00:00 – 00:44) or (01:20 - 02:13)
    clean = re.sub(r'\(\s*\d{1,2}:\d{2}\s*[\-–—]\s*\d{1,2}:\d{2}\s*\)', '', clean)
    clean = re.sub(r'\(Slides?\s*\d+[\s\-\–\—\d]*\)', '', clean, flags=re.IGNORECASE)
    # Strip Timeline XX:XX - YY:YY or Timestamp XX:XX prefixes
    clean = re.sub(r'^(?:Timeline|Timestamp|Keyframe|Video Keyframe)\s*(?:\d{1,2}:\d{2}(?:\s*[\-–—]\s*\d{1,2}:\d{2})?)?[\s:\-–—]*', '', clean, flags=re.IGNORECASE)
    # Strip [Video Keyframe from ...] tags completely
    clean = re.sub(r'\[(?:Video Keyframe|Keyframe)[^\]]*\]:?\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^(?:Video Keyframe from|Keyframe from|From|What is)\s+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+at\s+\d{1,2}:\d{2}(?::\d{2})?', '', clean, flags=re.IGNORECASE)
    # Strip Chapter X:, Module Y:, Slide Z:, Section N:, Part K:, Unit M:, LP K: at start
    clean = re.sub(r'^(?:Chapter|Module|Lecture|Slide|Section|Topic|Part|Unit|LP)\s*[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*\s*[\s:\-\–\—&]+\s*', '', clean, flags=re.IGNORECASE)
    # Strip leading numeric numbering like 1.1, 2.3, 1., 2)
    clean = re.sub(r'^\d+(?:\.\d+)*\s*[\.\):\-–—]+\s*', '', clean)
    # Strip prefixes like "Definition of", "Introduction to", "Understanding"
    clean = re.sub(r'^(?:definition of|introduction to|understanding|overview of|basics of|principles of)\s+', '', clean, flags=re.IGNORECASE)
    # Strip residual whitespace and trailing punctuation
    clean = re.sub(r'\s+', ' ', clean).strip(' :-–—.,;')
    return clean or title.strip()

def is_valid_concept_name(name: str) -> bool:
    """Validates whether a candidate string is a real educational concept rather than noise or boilerplate."""
    if not name or len(name.strip()) < 3:
        return False
    
    clean_lower = clean_title_prefix(name).lower().strip()
    if not clean_lower or len(clean_lower) < 3:
        return False

    # Check if exact boilerplate match
    if clean_lower in BOILERPLATE_STOP_WORDS:
        return False

    # Reject if starts with boilerplate or conjunction
    for stop_word in BOILERPLATE_STOP_WORDS:
        if clean_lower.startswith(stop_word + " ") or clean_lower.startswith(stop_word + ":") or clean_lower.startswith(stop_word + "-"):
            return False

    # Reject if matches pattern like "Reading (Pages ...)", "Figure 1", "Table 2", "Slide 4", "Timeline 00:00"
    if re.match(r'^(reading|figure|visual diagram|diagram|table|slide|page|module|section|part|chapter|unit|timeline|timestamp|keyframe|lecture part|from)\b', clean_lower, re.IGNORECASE):
        return False

    # Reject pure timestamp patterns (e.g. "00:00", "01:20 - 02:13", "p.1", "p.2")
    if re.search(r'^\d{1,2}:\d{2}', clean_lower) or re.match(r'^p\.\s*\d+$', clean_lower):
        return False

    # Reject if ends with trailing stop words / prepositions (e.g. "Operations on file are")
    words = clean_lower.split()
    if words and words[-1] in TRAILING_STOP_WORDS:
        return False

    # Reject if it's a full narrative sentence or too long (> 6 words)
    if len(words) > 6:
        return False
    
    # Reject if only digits or punctuation
    if not re.search(r'[a-zA-Z]', clean_lower):
        return False

    # Reject phrases that are obviously verbs/predicates
    if re.search(r'\b(is required|can be|cannot be|is used for|must be|should be|will be|is defined|refers to)\b', clean_lower):
        return False

    return True

def normalize_concept_name(name: str) -> str:
    """Standardizes concept names for reliable cross-modal matching and removes duplicated phrases."""
    cleaned = clean_title_prefix(name)
    cleaned = re.sub(r'^(the|a|an|understanding|introduction to|overview of|basics of|principles of)\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' :-–—.,;')
    
    # Remove consecutive duplicate phrases like "Flash Storage Flash Storage" -> "Flash Storage"
    words = cleaned.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        half = len(words) // 2
        if [w.lower() for w in words[:half]] == [w.lower() for w in words[half:]]:
            words = words[:half]
            cleaned = " ".join(words)

    # Trim trailing prepositions/conjunctions
    while words and words[-1].lower() in TRAILING_STOP_WORDS:
        words.pop()
        cleaned = " ".join(words)

    return cleaned.title() if cleaned else name.strip()

def compute_similarity(str1: str, str2: str) -> float:
    """Token-based Jaccard similarity between two strings."""
    tokens1 = set(re.findall(r'\w+', str1.lower()))
    tokens2 = set(re.findall(r'\w+', str2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union

# --- Definition & Prerequisite Pattern Detectors ---
PREREQUISITE_PATTERNS = [
    re.compile(r'(?:before understanding|before learning|prior to|to understand|in order to understand)\s+([^,.]+),\s+(?:one must|you must|it is necessary to|we must|first understand|understand|first learn|learn|master|first master)\s+(?:first\s+)?(?:understand|master|learn|know\s+about|know)?\s*([^,.]+)', re.IGNORECASE),
    re.compile(r'([^,.]+)\s+(?:requires knowledge of|depends on|is built on top of|is based on|assumes knowledge of|requires understanding of|relies upon)\s+([^,.]+)', re.IGNORECASE),
    re.compile(r'([^,.]+)\s+(?:is a prerequisite for|is required for|must be established before|is the foundation for)\s+([^,.]+)', re.IGNORECASE),
    re.compile(r'(?:must already be in|already in|assuming)\s+([^,.]+)(?:,|\s+and)\s+(?:to achieve|for)\s+([^,.]+)', re.IGNORECASE),
    re.compile(r'(?:once|after)\s+([^,.]+)\s+(?:is defined|is understood|is established),\s+(?:we introduce|we can study|we discuss)\s+([^,.]+)', re.IGNORECASE)
]

DEFINITION_PATTERNS = [
    re.compile(r'([A-Z][A-Za-z0-9\s\-]{2,35}?)\s+(?:is defined as|is a|is an|refers to|represents|means)\s+([^.\n]{15,200})', re.IGNORECASE),
    re.compile(r'([A-Z][A-Za-z0-9\s\-]{2,35}?)\s*:\s*([^.\n]{15,200})'),
]

RELATION_PATTERNS = {
    "explains": [
        re.compile(r'([^,.]+)\s+(?:explains|demonstrates|illustrates|details how)\s+([^,.]+)', re.IGNORECASE)
    ],
    "example_of": [
        re.compile(r'([^,.]+)\s+(?:is an example of|is an instance of|exemplifies)\s+([^,.]+)', re.IGNORECASE),
        re.compile(r'(?:example of|for instance,)\s+([^,.]+)\s+(?:is|in)\s+([^,.]+)', re.IGNORECASE)
    ],
    "part_of": [
        re.compile(r'([^,.]+)\s+(?:is a component of|is a part of|consists of|belongs to|is contained within)\s+([^,.]+)', re.IGNORECASE)
    ],
    "contrasts_with": [
        re.compile(r'([^,.]+)\s+(?:differs from|contrasts with|unlike|in contrast to)\s+([^,.]+)', re.IGNORECASE),
        re.compile(r'(?:unlike|contrasting)\s+([^,.]+),\s+([^,.]+)', re.IGNORECASE)
    ]
}


def extract_concepts_and_relationships_dynamic(
    course_id: str,
    chunks: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Dynamic concept, source, and relationship extraction for ANY course content.
    Works independently on whatever chunks are passed in.
    """
    if not chunks:
        return [], [], []

    # 1. First pass: Collect candidate concepts from titles and definitions
    raw_concepts = []
    
    for chunk in chunks:
        ch_title = chunk.get("chapter_title", "").strip() or "General Topic"
        sec_title = chunk.get("section_title", "").strip() or ch_title
        content = chunk.get("content", "").strip()

        # Clean topic & subtopic names
        topic_clean = clean_title_prefix(ch_title)
        subtopic_clean = clean_title_prefix(sec_title)

        # A. Concept from Section/Heading (if valid)
        if subtopic_clean and is_valid_concept_name(subtopic_clean):
            raw_concepts.append({
                "name": subtopic_clean,
                "topic": topic_clean if is_valid_concept_name(topic_clean) else "Core Concepts",
                "subtopic": subtopic_clean,
                "content_preview": content[:250],
                "chunk": chunk
            })
        else:
            # If subtopic was boilerplate (e.g. "Reading (Pages 1-2)"), check content first line for true section header
            first_lines = [l.strip() for l in content.split("\n") if l.strip()]
            for line in first_lines[:3]:
                cand_header = clean_title_prefix(line)
                if is_valid_concept_name(cand_header) and 2 <= len(cand_header.split()) <= 5:
                    raw_concepts.append({
                        "name": cand_header,
                        "topic": topic_clean if is_valid_concept_name(topic_clean) else "Core Concepts",
                        "subtopic": cand_header,
                        "content_preview": content[:250],
                        "chunk": chunk
                    })
                    break

        # B. Concept from Definitions in Content
        for p in DEFINITION_PATTERNS:
            matches = p.findall(content)
            for m in matches:
                cand_name = clean_title_prefix(m[0].strip())
                cand_desc = m[1].strip()
                if is_valid_concept_name(cand_name) and 1 <= len(cand_name.split()) <= 5:
                    raw_concepts.append({
                        "name": cand_name,
                        "topic": topic_clean if is_valid_concept_name(topic_clean) else "Core Concepts",
                        "subtopic": subtopic_clean if is_valid_concept_name(subtopic_clean) else cand_name,
                        "description": cand_desc,
                        "content_preview": content[:250],
                        "chunk": chunk
                    })

        # C. Topic itself as major anchor concept if valid
        if topic_clean and is_valid_concept_name(topic_clean):
            raw_concepts.append({
                "name": topic_clean,
                "topic": topic_clean,
                "subtopic": topic_clean,
                "content_preview": content[:250],
                "chunk": chunk
            })

    # If still empty, create at least fallback from content keywords
    if not raw_concepts:
        for chunk in chunks[:4]:
            sec_title = chunk.get("section_title") or chunk.get("chapter_title") or "Course Concept"
            c_name = clean_title_prefix(sec_title) or "Fundamental Concept"
            raw_concepts.append({
                "name": c_name,
                "topic": "Core Material",
                "subtopic": c_name,
                "content_preview": chunk.get("content", "")[:250],
                "chunk": chunk
            })

    # 2. Concept Clustering & Cross-Modal Canonicalization
    canonical_concepts: Dict[str, Dict[str, Any]] = {}

    for raw in raw_concepts:
        norm_name = normalize_concept_name(raw["name"])
        if not is_valid_concept_name(norm_name):
            continue

        matched_key = None

        # Check if already exists or closely resembles an existing canonical concept
        for key, c_obj in canonical_concepts.items():
            sim = compute_similarity(norm_name, c_obj["name"])
            c_name_l = c_obj["name"].lower()
            norm_name_l = norm_name.lower()
            
            # Match if identical, high Jaccard, or clean substring match
            if sim >= 0.65 or norm_name_l == c_name_l or (len(norm_name_l) > 4 and norm_name_l in c_name_l) or (len(c_name_l) > 4 and c_name_l in norm_name_l):
                matched_key = key
                break

        if not matched_key:
            c_id = f"c_{course_id}_{sanitize_id(norm_name)}_{len(canonical_concepts)+1}"
            matched_key = c_id
            
            # Generate grounded description
            desc = raw.get("description", "")
            if not desc:
                sentences = re.split(r'(?<=[.!?])\s+', raw["content_preview"])
                desc = sentences[0] if sentences else raw["content_preview"]

            canonical_concepts[c_id] = {
                "id": c_id,
                "course_id": course_id,
                "name": norm_name,
                "topic": raw["topic"] if is_valid_concept_name(raw["topic"]) else "Core Concepts",
                "subtopic": raw.get("subtopic", ""),
                "description": desc.strip(),
                "created_at": datetime.now().isoformat()
            }

    concepts_list = list(canonical_concepts.values())

    # 3. Cross-Modal Source Provenance Mapping
    sources_list: List[Dict[str, Any]] = []
    seen_sources: Set[Tuple[str, str, Any, Any, Any]] = set()

    for c in concepts_list:
        c_id = c["id"]
        c_name = c["name"]
        c_tokens = set(re.findall(r'\w+', c_name.lower()))
        
        for chunk in chunks:
            chunk_content = chunk.get("content", "")
            chunk_title = (chunk.get("chapter_title", "") + " " + chunk.get("section_title", "")).lower()
            chunk_full_text = (chunk_title + " " + chunk_content).lower()
            
            # Check if this chunk provides evidence for concept c
            is_relevant = False
            
            # Direct phrase match
            if c_name.lower() in chunk_full_text:
                is_relevant = True
            elif compute_similarity(c_name, chunk_title) >= 0.50:
                is_relevant = True
            elif len(c_tokens) >= 2 and all(tok in chunk_full_text for tok in c_tokens):
                is_relevant = True

            if is_relevant:
                s_type = chunk.get("source_type", "pdf")
                p_num = chunk.get("page")
                s_num = chunk.get("slide_number")
                t_str = chunk.get("timestamp_str")

                source_key = (c_id, s_type, p_num, s_num, t_str)
                if source_key not in seen_sources:
                    seen_sources.add(source_key)
                    s_id = f"src_{c_id}_{chunk.get('id', len(sources_list)+1)}"
                    
                    # Extract best excerpt
                    excerpt = chunk_content[:220]
                    for sentence in re.split(r'(?<=[.!?])\s+', chunk_content):
                        if c_name.lower() in sentence.lower():
                            excerpt = sentence.strip()
                            break

                    sources_list.append({
                        "id": s_id,
                        "concept_id": c_id,
                        "course_id": course_id,
                        "content_unit_id": chunk.get("id"),
                        "source_type": s_type,
                        "filename": chunk.get("filename", ""),
                        "page_number": p_num,
                        "slide_number": s_num,
                        "start_time": chunk.get("start_time"),
                        "end_time": chunk.get("end_time"),
                        "timestamp_str": t_str,
                        "excerpt": excerpt,
                        "media_path": chunk.get("media_path"),
                        "created_at": datetime.now().isoformat()
                    })

    # Ensure every concept has at least one source
    for c in concepts_list:
        has_src = any(s["concept_id"] == c["id"] for s in sources_list)
        if not has_src and chunks:
            chk = chunks[0]
            sources_list.append({
                "id": f"src_{c['id']}_default",
                "concept_id": c["id"],
                "course_id": course_id,
                "content_unit_id": chk.get("id"),
                "source_type": chk.get("source_type", "pdf"),
                "filename": chk.get("filename", ""),
                "page_number": chk.get("page", 1),
                "slide_number": chk.get("slide_number"),
                "start_time": chk.get("start_time"),
                "end_time": chk.get("end_time"),
                "timestamp_str": chk.get("timestamp_str"),
                "excerpt": c["description"][:200],
                "media_path": chk.get("media_path"),
                "created_at": datetime.now().isoformat()
            })

    # 4. Dynamic Relationship & Prerequisite Inference
    relationships_list: List[Dict[str, Any]] = []
    created_pairs: Set[Tuple[str, str, str]] = set()

    # A. Search for explicit prerequisite and relational phrases in all chunks
    for chunk in chunks:
        content = chunk.get("content", "")
        
        # Check prerequisite patterns
        for pat in PREREQUISITE_PATTERNS:
            for match in pat.findall(content):
                phrase_a, phrase_b = match[0].strip(), match[1].strip()
                matched_a = _find_best_matching_concept(phrase_a, concepts_list)
                matched_b = _find_best_matching_concept(phrase_b, concepts_list)
                
                if matched_a and matched_b and matched_a["id"] != matched_b["id"]:
                    is_b_prereq = (
                        "before understanding" in pat.pattern or 
                        "to understand" in pat.pattern or 
                        "requires knowledge of" in pat.pattern or
                        "depends on" in pat.pattern or
                        "is built on top of" in pat.pattern or
                        "is based on" in pat.pattern or
                        "assumes knowledge of" in pat.pattern or
                        "requires understanding of" in pat.pattern or
                        "relies upon" in pat.pattern
                    )
                    src_c = matched_b if is_b_prereq else matched_a
                    tgt_c = matched_a if is_b_prereq else matched_b
                    
                    pair_key = (src_c["id"], tgt_c["id"], "prerequisite")
                    if pair_key not in created_pairs:
                        created_pairs.add(pair_key)
                        relationships_list.append({
                            "id": f"rel_{course_id}_{len(relationships_list)+1}",
                            "course_id": course_id,
                            "source_concept_id": src_c["id"],
                            "target_concept_id": tgt_c["id"],
                            "source_concept_name": src_c["name"],
                            "target_concept_name": tgt_c["name"],
                            "relationship_type": "prerequisite",
                            "confidence": 0.95,
                            "evidence": f"Explicitly stated in course material: '{content[:200]}...'",
                            "created_at": datetime.now().isoformat()
                        })

        # Check other explicit relationship patterns
        for rel_type, patterns in RELATION_PATTERNS.items():
            for pat in patterns:
                for match in pat.findall(content):
                    p_a, p_b = match[0].strip(), match[1].strip()
                    m_a = _find_best_matching_concept(p_a, concepts_list)
                    m_b = _find_best_matching_concept(p_b, concepts_list)
                    if m_a and m_b and m_a["id"] != m_b["id"]:
                        pair_key = (m_a["id"], m_b["id"], rel_type)
                        if pair_key not in created_pairs:
                            created_pairs.add(pair_key)
                            relationships_list.append({
                                "id": f"rel_{course_id}_{len(relationships_list)+1}",
                                "course_id": course_id,
                                "source_concept_id": m_a["id"],
                                "target_concept_id": m_b["id"],
                                "source_concept_name": m_a["name"],
                                "target_concept_name": m_b["name"],
                                "relationship_type": rel_type,
                                "confidence": 0.90,
                                "evidence": f"Evidence from course content: '{content[:180]}...'",
                                "created_at": datetime.now().isoformat()
                            })

    # B. Definition dependency analysis:
    # If Concept B's definition or description explicitly requires / mentions Concept A
    for i, c_a in enumerate(concepts_list):
        for j, c_b in enumerate(concepts_list):
            if i == j:
                continue
            
            b_sources = [s for s in sources_list if s["concept_id"] == c_b["id"]]
            b_text = c_b["description"] + " " + " ".join([s["excerpt"] for s in b_sources])
            
            # If Concept A is a distinct term found in B's explanation
            if len(c_a["name"]) > 3 and re.search(r'\b' + re.escape(c_a["name"].lower()) + r'\b', b_text.lower()):
                a_page = min([s.get("page_number") or s.get("slide_number") or 1 for s in sources_list if s["concept_id"] == c_a["id"]] or [1])
                b_page = min([s.get("page_number") or s.get("slide_number") or 1 for s in b_sources] or [1])
                
                if a_page <= b_page:
                    pair_key = (c_a["id"], c_b["id"], "prerequisite")
                    if pair_key not in created_pairs:
                        created_pairs.add(pair_key)
                        relationships_list.append({
                            "id": f"rel_{course_id}_{len(relationships_list)+1}",
                            "course_id": course_id,
                            "source_concept_id": c_a["id"],
                            "target_concept_id": c_b["id"],
                            "source_concept_name": c_a["name"],
                            "target_concept_name": c_b["name"],
                            "relationship_type": "prerequisite",
                            "confidence": 0.88,
                            "evidence": f"'{c_b['name']}' directly relies upon and references '{c_a['name']}' in its core definition.",
                            "created_at": datetime.now().isoformat()
                        })

    return concepts_list, sources_list, relationships_list


def _find_best_matching_concept(phrase: str, concepts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Helper to match a phrase from text to one of our extracted concepts."""
    phrase_clean = phrase.strip().lower()
    if len(phrase_clean) < 2:
        return None

    best_c = None
    best_score = 0.0

    for c in concepts:
        c_name = c["name"].lower()
        if phrase_clean == c_name:
            return c
        if phrase_clean in c_name or c_name in phrase_clean:
            score = len(c_name) / max(len(phrase_clean), 1)
            if score > best_score:
                best_score = score
                best_c = c
        else:
            sim = compute_similarity(phrase_clean, c_name)
            if sim > 0.60 and sim > best_score:
                best_score = sim
                best_c = c

    return best_c if best_score > 0.40 else None


def extract_concepts_with_llm(
    course_id: str,
    chunks: List[Dict[str, Any]]
) -> Optional[Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]]:
    """
    Uses Gemini LLM for structured, high-accuracy concept graph extraction when valid API key is present.
    """
    if not is_gemini_available():
        return None

    def _call_gemini():
        client = get_gemini_client()
        if not client:
            return None

        context_items = []
        for idx, ch in enumerate(chunks[:20]):
            s_label = f"[{ch.get('source_type', 'pdf').upper()} Page/Slide {ch.get('page') or ch.get('slide_number') or ch.get('timestamp_str')}]"
            context_items.append(f"Chunk {idx+1} {s_label} (Topic: {ch.get('chapter_title')}): {ch.get('content')}")

        context_str = "\n\n".join(context_items)
        prompt = f"""You are an advanced educational knowledge graph builder.
Analyze the following multimodal course material chunks and extract:
1. Dynamic Topics and Key Concepts with concise definitions (EXCLUDE boilerplate labels like 'Reading', 'Figure', 'Table', 'Exercises', 'Summary').
2. Cross-modal source mappings (which chunk IDs / pages / slides support each concept).
3. Directed Prerequisite relationships (Concept A is prerequisite for Concept B) with explicit grounded evidence/reasoning.
4. Related concept relationships ('related_to', 'part_of', 'explains', 'example_of', 'contrasts_with') with evidence.

Strict Rules:
- Extract concepts dynamically ONLY from the provided course text.
- Do NOT hard-code concepts.
- Prerequisite Direction: 'source_concept' MUST be learned BEFORE 'target_concept'.
- Only include a prerequisite if there is sufficient grounded evidence. If not confident, do not create one.
- Evidence MUST reference actual course facts or definitions.

Textbook/Course Context:
{context_str}

Return JSON with exact structure:
{{
  "concepts": [
    {{
      "name": "Concept Name",
      "topic": "Topic Name",
      "subtopic": "Subtopic Name",
      "description": "Clear concise definition grounded in content",
      "chunk_indices": [1, 2]
    }}
  ],
  "relationships": [
    {{
      "source_concept": "Prerequisite Concept Name",
      "target_concept": "Dependent Concept Name",
      "relationship_type": "prerequisite",
      "confidence": 0.95,
      "evidence": "Why source is needed before target based on material"
    }}
  ]
}}
"""
        for model_cand in FAST_GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_cand,
                    contents=prompt
                )
                clean_res = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_res)
            except Exception:
                continue
        return None

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_gemini)
            data = future.result(timeout=4.0)

        concepts_raw = data.get("concepts", [])
        relationships_raw = data.get("relationships", [])

        if not concepts_raw:
            return None

        concepts_list = []
        sources_list = []
        concept_name_to_id = {}

        now_iso = datetime.now().isoformat()

        for idx, c in enumerate(concepts_raw):
            c_name = normalize_concept_name(c["name"])
            if not is_valid_concept_name(c_name):
                continue
            c_id = f"c_{course_id}_{sanitize_id(c_name)}_{idx+1}"
            concept_name_to_id[c_name.lower()] = c_id
            
            c_obj = {
                "id": c_id,
                "course_id": course_id,
                "name": c_name,
                "topic": c.get("topic", "General"),
                "subtopic": c.get("subtopic", ""),
                "description": c.get("description", ""),
                "created_at": now_iso
            }
            concepts_list.append(c_obj)

            # Map chunk indices to sources
            chunk_indices = c.get("chunk_indices", [])
            for c_idx in chunk_indices:
                if 1 <= c_idx <= len(chunks):
                    chk = chunks[c_idx - 1]
                    s_id = f"src_{c_id}_{chk.get('id', c_idx)}"
                    sources_list.append({
                        "id": s_id,
                        "concept_id": c_id,
                        "course_id": course_id,
                        "content_unit_id": chk.get("id"),
                        "source_type": chk.get("source_type", "pdf"),
                        "filename": chk.get("filename", ""),
                        "page_number": chk.get("page"),
                        "slide_number": chk.get("slide_number"),
                        "start_time": chk.get("start_time"),
                        "end_time": chk.get("end_time"),
                        "timestamp_str": chk.get("timestamp_str"),
                        "excerpt": chk.get("content", "")[:200],
                        "media_path": chk.get("media_path"),
                        "created_at": now_iso
                    })

        # Process relationships
        relationships_list = []
        created_rel_keys = set()

        for idx, r in enumerate(relationships_raw):
            src_name = r.get("source_concept", "").strip()
            tgt_name = r.get("target_concept", "").strip()
            rel_type = r.get("relationship_type", "prerequisite")
            
            src_id = concept_name_to_id.get(src_name.lower()) or concept_name_to_id.get(normalize_concept_name(src_name).lower())
            tgt_id = concept_name_to_id.get(tgt_name.lower()) or concept_name_to_id.get(normalize_concept_name(tgt_name).lower())

            if not src_id:
                m = _find_best_matching_concept(src_name, concepts_list)
                src_id = m["id"] if m else None
            if not tgt_id:
                m = _find_best_matching_concept(tgt_name, concepts_list)
                tgt_id = m["id"] if m else None

            if src_id and tgt_id and src_id != tgt_id:
                pair_key = (src_id, tgt_id, rel_type)
                if pair_key not in created_rel_keys:
                    created_rel_keys.add(pair_key)
                    relationships_list.append({
                        "id": f"rel_{course_id}_{len(relationships_list)+1}",
                        "course_id": course_id,
                        "source_concept_id": src_id,
                        "target_concept_id": tgt_id,
                        "source_concept_name": src_name,
                        "target_concept_name": tgt_name,
                        "relationship_type": rel_type,
                        "confidence": float(r.get("confidence", 0.90)),
                        "evidence": r.get("evidence", "Identified by grounded AI course analysis."),
                        "created_at": now_iso
                    })

        return concepts_list, sources_list, relationships_list

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            mark_gemini_quota_exhausted()
        return None


def generate_course_concept_graph(
    course_id: str,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Main entry point: Generates and persists the complete concept and prerequisite graph
    for a given course or textbook ID.
    """
    # 1. Check if graph is already cached in database
    if not force_regenerate:
        cached_graph = get_concept_graph(course_id)
        if cached_graph and cached_graph["nodes"]:
            # Check if cached graph contains boilerplate names that need cleanup
            has_junk = any(not is_valid_concept_name(n["name"]) for n in cached_graph["nodes"])
            if not has_junk:
                cached_graph["learning_paths"] = compute_learning_paths(cached_graph)
                return cached_graph

    # 2. Fetch chunks from database for this course
    chunks = get_chunks_for_textbook(course_id)

    if not chunks:
        from services.demo_data import get_demo_textbook_data
        demo = get_demo_textbook_data()
        chunks = demo["chunks"]

    # 3. Attempt LLM structured extraction first, fallback to dynamic semantic engine
    extracted = extract_concepts_with_llm(course_id, chunks)
    if not extracted or not extracted[0]:
        extracted = extract_concepts_and_relationships_dynamic(course_id, chunks)

    concepts, sources, relationships = extracted

    # 4. Save to database
    save_concept_graph(course_id, concepts, sources, relationships)

    # 5. Fetch fresh graph from DB to ensure schema consistency
    graph = get_concept_graph(course_id)
    if not graph:
        raise ValueError(f"Failed to generate concept graph for course {course_id}")

    graph["learning_paths"] = compute_learning_paths(graph)
    return graph


def compute_learning_paths(graph: Dict[str, Any]) -> List[List[str]]:
    """
    Computes topological learning pathways based on directed prerequisite chains.
    Prerequisite edges: Source -> Target (meaning Source must be learned before Target).
    """
    nodes = graph.get("nodes", [])
    edges = [e for e in graph.get("edges", []) if e.get("relationship_type") == "prerequisite"]
    
    if not edges:
        return [[n["name"] for n in nodes[:5]]] if nodes else []

    # Build adjacency list: node_id -> [children that depend on this node]
    adj = {n["id"]: [] for n in nodes}
    in_degree = {n["id"]: 0 for n in nodes}
    id_to_name = {n["id"]: n["name"] for n in nodes}

    for e in edges:
        src = e["source_concept_id"]
        tgt = e["target_concept_id"]
        if src in adj and tgt in in_degree:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    # Find root concepts (no prerequisites)
    roots = [n_id for n_id, deg in in_degree.items() if deg == 0 and len(adj[n_id]) > 0]
    if not roots:
        roots = [nodes[0]["id"]] if nodes else []

    paths = []
    
    # Trace top prerequisite paths
    def dfs(current_id, current_path, visited):
        if len(current_path) >= 5 or not adj[current_id]:
            paths.append(list(current_path))
            return
        
        has_next = False
        for child_id in adj[current_id]:
            if child_id not in visited:
                visited.add(child_id)
                current_path.append(id_to_name.get(child_id, child_id))
                dfs(child_id, current_path, visited)
                current_path.pop()
                visited.remove(child_id)
                has_next = True
        
        if not has_next:
            paths.append(list(current_path))

    for r in roots[:4]:
        dfs(r, [id_to_name.get(r, r)], {r})

    # Deduplicate and sort by path length
    unique_paths = []
    seen = set()
    for p in sorted(paths, key=lambda x: len(x), reverse=True):
        p_tuple = tuple(p)
        if p_tuple not in seen and len(p) > 1:
            seen.add(p_tuple)
            unique_paths.append(p)

    return unique_paths[:3] or [[n["name"] for n in nodes[:4]]]
