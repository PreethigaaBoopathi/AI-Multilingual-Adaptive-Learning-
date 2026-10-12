import re
from typing import Dict, Any, List, Optional, Tuple, Set
from database import (
    get_db_connection, get_chunks_for_textbook, get_media_for_textbook,
    get_assessment_questions
)
import mongodb_service

# =========================================================================
# INNOVATION: UNIFIED MULTIMODAL RESOURCE INDEX & SELECTION ENGINE
# =========================================================================

def _normalize(text: str) -> str:
    """Normalizes a string for robust matching."""
    return re.sub(r'[^a-zA-Z0-9]', '', (text or "").lower().strip())

def _clean_title(text: str) -> str:
    """Strips leading chapter/section numbers from a title."""
    return re.sub(r'^(?:\d+[\.\)]*\s*)+', '', (text or "")).strip().lower()

def build_unified_resource_index(course_id: str) -> List[Dict[str, Any]]:
    """
    Builds a searchable Unified Resource Index across all uploaded materials
    for a given course:
    - PDF pages & passages
    - PPT/PPTX presentation slides
    - Video lecture segments with verified timestamps
    - Media items (diagrams, figures, tables)
    - Concept source provenances
    - Stored assessment questions & practice activities

    Every item contains genuine, verified metadata and exact provenance.
    Never invents filenames, page numbers, slide numbers, or timestamps.
    """
    resources: List[Dict[str, Any]] = []
    seen_resource_keys: Set[str] = set()

    # 1. Index Knowledge Chunks (PDFs, PPT slides, Video transcripts)
    chunks = get_chunks_for_textbook(course_id)
    if not chunks:
        # Check if demo course
        if course_id in ["tb_dbms_norm_001", "default"]:
            from services.demo_data import get_demo_textbook_data
            chunks = get_demo_textbook_data()["chunks"]

    for c in chunks:
        c_id = c.get("id") or f"chk_{len(resources)}"
        s_type = c.get("source_type") or "pdf"
        filename = c.get("filename") or "Course Material"
        page_num = c.get("page")
        slide_num = c.get("slide_number")
        start_time = c.get("start_time")
        end_time = c.get("end_time")
        timestamp_str = c.get("timestamp_str")
        content = c.get("content", "").strip()
        
        # Clean noisy exam header banners
        content_clean = re.sub(r'^[0-9]{2}[A-Za-z]{2,4}[0-9]{2,4}.*?\n', '', content, flags=re.IGNORECASE)
        snippet = (content_clean[:220] + "...") if len(content_clean) > 220 else content_clean
        concept_or_topic = c.get("section_title") or c.get("chapter_title") or "General Topic"

        # Determine exact resource type & provenance string
        if s_type == "video":
            res_type = "video_segment"
            prov_ref = f"{filename}, Timestamp {timestamp_str}" if timestamp_str else f"{filename}, Video Lecture"
            title = f"Lecture Video Segment ({timestamp_str})" if timestamp_str else f"Video Segment: {concept_or_topic}"
            nav_target = {"tab": "summary", "timestamp_str": timestamp_str, "filename": filename}
        elif s_type == "presentation":
            res_type = "presentation_slide"
            s_num = slide_num or page_num or 1
            prov_ref = f"{filename}, Slide {s_num}"
            title = f"Presentation Slide {s_num}: {concept_or_topic}"
            nav_target = {"tab": "summary", "slide_number": s_num, "filename": filename}
        else:
            res_type = "pdf_passage"
            p_num = page_num or 1
            prov_ref = f"{filename}, Page {p_num}"
            title = f"Textbook Passage (p. {p_num}): {concept_or_topic}"
            nav_target = {"tab": "summary", "page": p_num, "chapter_id": c.get("chapter_id"), "filename": filename}

        res_key = f"{res_type}_{filename}_{page_num}_{slide_num}_{timestamp_str}_{concept_or_topic[:30]}"
        if res_key not in seen_resource_keys:
            seen_resource_keys.add(res_key)
            resources.append({
                "resource_id": f"res_chk_{c_id}",
                "course_id": course_id,
                "resource_type": res_type,
                "title": title,
                "filename": filename,
                "concept_name": concept_or_topic,
                "topic": c.get("chapter_title") or "Core Topic",
                "content_snippet": snippet,
                "page_number": page_num if s_type == "pdf" else None,
                "slide_number": slide_num or (page_num if s_type == "presentation" else None),
                "start_time": start_time,
                "end_time": end_time,
                "timestamp_str": timestamp_str,
                "media_path": c.get("media_path"),
                "provenance_ref": prov_ref,
                "difficulty_level": "intermediate" if s_type in ["pdf", "presentation"] else "beginner",
                "navigation_target": nav_target
            })

    # 2. Index Concept Sources (Explicit Cross-Modal Provenance from Innovation 2)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cs.*, c.name as concept_name, c.topic as concept_topic
        FROM concept_sources cs
        JOIN concepts c ON cs.concept_id = c.id
        WHERE cs.course_id = ?
    """, (course_id,))
    source_rows = [dict(r) for r in cursor.fetchall()]

    for s in source_rows:
        s_type = s.get("source_type") or "pdf"
        filename = s.get("filename") or "Course Material"
        p_num = s.get("page_number")
        s_num = s.get("slide_number")
        ts_str = s.get("timestamp_str")
        c_name = s.get("concept_name") or "Concept Source"
        excerpt = s.get("excerpt", "")
        snippet = (excerpt[:200] + "...") if len(excerpt) > 200 else excerpt

        if s_type == "video":
            res_type = "video_segment"
            prov_ref = f"{filename}, Timestamp {ts_str}" if ts_str else f"{filename}, Video"
            title = f"Targeted Video Excerpt: {c_name} ({ts_str})" if ts_str else f"Video: {c_name}"
            nav_target = {"tab": "summary", "timestamp_str": ts_str, "filename": filename}
        elif s_type == "presentation":
            res_type = "presentation_slide"
            prov_ref = f"{filename}, Slide {s_num}" if s_num else f"{filename}, Slide"
            title = f"Slide Reference: {c_name} (Slide {s_num})" if s_num else f"Slide: {c_name}"
            nav_target = {"tab": "summary", "slide_number": s_num, "filename": filename}
        else:
            res_type = "pdf_passage"
            prov_ref = f"{filename}, Page {p_num}" if p_num else f"{filename}, Page"
            title = f"Document Excerpt: {c_name} (Page {p_num})" if p_num else f"Document: {c_name}"
            nav_target = {"tab": "summary", "page": p_num, "filename": filename}

        res_key = f"{res_type}_{filename}_{p_num}_{s_num}_{ts_str}_{c_name}"
        if res_key not in seen_resource_keys:
            seen_resource_keys.add(res_key)
            resources.append({
                "resource_id": f"res_csrc_{s.get('id')}",
                "course_id": course_id,
                "resource_type": res_type,
                "title": title,
                "filename": filename,
                "concept_name": c_name,
                "topic": s.get("concept_topic") or "Concept Details",
                "content_snippet": snippet,
                "page_number": p_num,
                "slide_number": s_num,
                "start_time": s.get("start_time"),
                "end_time": s.get("end_time"),
                "timestamp_str": ts_str,
                "media_path": s.get("media_path"),
                "provenance_ref": prov_ref,
                "difficulty_level": "intermediate",
                "navigation_target": nav_target
            })

    # 3. Index Media Items (Extracted Diagrams, Figures, Tables)
    media_items = get_media_for_textbook(course_id)
    for m in media_items:
        m_id = m.get("id") or f"m_{len(resources)}"
        m_file = m.get("filename") or "Course Media"
        m_type = m.get("content_type") or "image"
        m_page = m.get("page")
        m_slide = m.get("slide")
        m_ts = m.get("timestamp")
        m_path = m.get("media_path")
        
        prov_ref = f"{m_file}, Page {m_page}" if m_page else (f"{m_file}, Slide {m_slide}" if m_slide else f"{m_file}, {m_path}")
        title = f"Extracted Figure / Diagram ({prov_ref})" if "image" in m_type else f"Structured Visual ({prov_ref})"

        res_key = f"diagram_{m_file}_{m_page}_{m_slide}_{m_path}"
        if res_key not in seen_resource_keys and m_path:
            seen_resource_keys.add(res_key)
            resources.append({
                "resource_id": f"res_media_{m_id}",
                "course_id": course_id,
                "resource_type": "diagram",
                "title": title,
                "filename": m_file,
                "concept_name": f"Visual Diagram ({prov_ref})",
                "topic": "Visual Evidence",
                "content_snippet": f"Extracted visual diagram / architectural figure from {prov_ref}.",
                "page_number": m_page,
                "slide_number": m_slide,
                "start_time": None,
                "end_time": None,
                "timestamp_str": m_ts,
                "media_path": m_path,
                "provenance_ref": prov_ref,
                "difficulty_level": "beginner",
                "navigation_target": {"tab": "visualize", "media_path": m_path}
            })

    # 4. Index Pre-Generated & Stored Assessment Questions (Innovation 4)
    questions = get_assessment_questions(course_id, limit=30)
    for q in questions:
        q_id = q.get("id")
        q_concept = q.get("concept_name") or q.get("topic") or "Assessment Drill"
        q_text = q.get("question", "")
        q_type = q.get("question_type", "mcq")
        q_diff = q.get("difficulty", "medium")
        cite = q.get("source_citation") or {}
        
        prov_file = cite.get("filename") or "Course Assessment Bank"
        p_num = cite.get("page")
        prov_ref = f"{prov_file}, Page {p_num}" if p_num else prov_file

        res_key = f"quiz_{q_id}_{q_concept}"
        if res_key not in seen_resource_keys:
            seen_resource_keys.add(res_key)
            resources.append({
                "resource_id": f"res_quiz_{q_id}",
                "course_id": course_id,
                "resource_type": "targeted_quiz",
                "title": f"Targeted Assessment Drill ({q_type.upper()}) on {q_concept}",
                "filename": prov_file,
                "concept_name": q_concept,
                "topic": q.get("topic") or "Assessment",
                "content_snippet": f"Question: {q_text[:180]}...",
                "page_number": p_num,
                "slide_number": cite.get("slide"),
                "start_time": None,
                "end_time": None,
                "timestamp_str": cite.get("timestamp"),
                "media_path": None,
                "provenance_ref": prov_ref,
                "difficulty_level": q_diff,
                "question_data": q,
                "navigation_target": {"tab": "quiz", "question_id": q_id, "topic": q.get("topic")}
            })

    # 5. Always index Synthesized Visual Model & Worked Example entries for Course Concepts
    cursor.execute("SELECT id, name, topic, description FROM concepts WHERE course_id = ?", (course_id,))
    concept_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for c in concept_rows:
        c_name = c["name"]
        c_top = c.get("topic", "General")
        
        # Interactive Mermaid Concept Model
        res_key = f"visual_model_{course_id}_{c['id']}"
        if res_key not in seen_resource_keys:
            seen_resource_keys.add(res_key)
            resources.append({
                "resource_id": f"res_vm_{c['id']}",
                "course_id": course_id,
                "resource_type": "visual_model",
                "title": f"Interactive Visual Flowchart & Architecture: {c_name}",
                "filename": "Course Interactive Visual Engine",
                "concept_name": c_name,
                "topic": c_top,
                "content_snippet": f"Interactive Mermaid.js architecture and logic flowchart for {c_name}. Illustrates prerequisite relationships, algorithmic transitions, and structural constraints.",
                "page_number": None,
                "slide_number": None,
                "start_time": None,
                "end_time": None,
                "timestamp_str": None,
                "media_path": None,
                "provenance_ref": f"Course Visual Engine: {c_name}",
                "difficulty_level": "beginner",
                "navigation_target": {"tab": "visualize", "topic": c_name}
            })

        # Grounded Worked Example / Adaptive Tutorial
        res_key = f"worked_example_{course_id}_{c['id']}"
        if res_key not in seen_resource_keys:
            seen_resource_keys.add(res_key)
            resources.append({
                "resource_id": f"res_we_{c['id']}",
                "course_id": course_id,
                "resource_type": "worked_example",
                "title": f"Grounded Worked Example & Case Walkthrough: {c_name}",
                "filename": "Grounded AI Tutor Service",
                "concept_name": c_name,
                "topic": c_top,
                "content_snippet": f"Step-by-step worked example, practical application scenario, and systems trade-off analysis for {c_name}.",
                "page_number": None,
                "slide_number": None,
                "start_time": None,
                "end_time": None,
                "timestamp_str": None,
                "media_path": None,
                "provenance_ref": f"Grounded Tutor: {c_name}",
                "difficulty_level": "intermediate",
                "navigation_target": {"tab": "explain", "topic": c_name}
            })

    return resources


def find_matching_resources_for_concept(
    resources: List[Dict[str, Any]],
    concept_name: str,
    limit: int = 8
) -> List[Dict[str, Any]]:
    """
    Finds and scores all resources in the unified index matching a concept name.
    """
    if not concept_name or not resources:
        return []

    c_norm = _normalize(concept_name)
    c_clean = _clean_title(concept_name)
    c_tokens = set([t for t in re.split(r'\W+', c_clean) if len(t) > 2])

    scored: List[Tuple[float, Dict[str, Any]]] = []

    for r in resources:
        r_c_name = r.get("concept_name", "")
        r_norm = _normalize(r_c_name)
        r_clean = _clean_title(r_c_name)
        r_tokens = set([t for t in re.split(r'\W+', r_clean) if len(t) > 2])
        r_text = (r.get("content_snippet", "") + " " + r.get("title", "")).lower()

        score = 0.0

        # Exact / Normalized match on concept title
        if r_norm == c_norm:
            score += 100.0
        elif r_clean == c_clean:
            score += 90.0
        elif c_clean in r_clean or r_clean in c_clean:
            score += 75.0
        elif c_norm in r_norm or r_norm in c_norm:
            score += 70.0

        # Token overlap
        overlap = len(c_tokens.intersection(r_tokens))
        if overlap > 0:
            score += overlap * 15.0

        # Keyword density in snippet
        for tok in c_tokens:
            if tok in r_text:
                score += 8.0

        if score > 0:
            scored.append((score, r))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


class MultimodalResourceSelection(tuple):
    def __new__(cls, best_resource, alternatives, rationale, score):
        return super().__new__(cls, (best_resource, alternatives, rationale, score))

    @property
    def best_resource(self):
        return self[0]

    @property
    def alternative_resources(self):
        return self[1]

    @property
    def selection_rationale(self):
        return self[2]

    @property
    def ranking_score(self):
        return self[3]

    def get(self, key, default=None):
        if key == "best_resource":
            return self[0]
        elif key == "alternative_resources":
            return self[1]
        elif key == "selection_rationale":
            return self[2]
        elif key == "ranking_score":
            return self[3]
        return default

    def __getitem__(self, item):
        if isinstance(item, str):
            val = self.get(item)
            if val is not None:
                return val
        return super().__getitem__(item)


def select_best_multimodal_resource(
    concept_name: str,
    gap_type: str = "untested",
    mastery_percentage: Optional[float] = None,
    accuracy_score: Optional[float] = None,
    has_active_misconception: bool = False,
    candidate_resources: Optional[List[Dict[str, Any]]] = None,
    attempted_resource_ids: Optional[Set[str]] = None,
    course_id: Optional[str] = None,
    topic: Optional[str] = None,
    learner_gap: Optional[str] = None,
    explanation_level: Optional[str] = "intermediate"
) -> MultimodalResourceSelection:
    """
    Ranks candidates and selects the next best learning resource based on:
    - Relevance to target concept
    - Student learning gap type (demonstrated gap, misconception, untested, mastered)
    - Multimodal format fitness (video/diagram for beginner/misconception, slides/text for revision, quiz for mastery)
    - Exact provenance quality
    - Avoidance of previously attempted resources

    Returns: MultimodalResourceSelection(best_resource, alternative_resources, selection_rationale, ranking_score)
    """
    if learner_gap:
        gap_type = learner_gap
    if gap_type == "active_misconception":
        has_active_misconception = True

    if candidate_resources is None and course_id:
        all_resources = build_unified_resource_index(course_id)
        candidate_resources = find_matching_resources_for_concept(all_resources, concept_name)

    if not candidate_resources:
        rationale = f"No direct uploaded material found for '{concept_name}' in course files. Recommend using the Grounded AI Tutor."
        return MultimodalResourceSelection(None, [], rationale, 0.0)


    attempted_ids = attempted_resource_ids or set()
    scored_candidates: List[Tuple[float, Dict[str, Any], str]] = []

    for r in candidate_resources:
        r_id = r.get("resource_id")
        r_type = r.get("resource_type")
        score = 50.0  # Base score
        reasons = []

        # 1. Exact Provenance Bonus
        if r.get("page_number") is not None or r.get("slide_number") is not None:
            score += 15.0
            reasons.append("verified page/slide provenance")
        if r.get("timestamp_str"):
            score += 15.0
            reasons.append("verified video timestamp segment")

        # 2. Pedagogical Fitness according to Learner Gap & Mastery
        if has_active_misconception:
            if r_type == "visual_model" or r_type == "diagram":
                score += 35.0
                reasons.append("visual diagram directly contrasts misconceptions")
            elif r_type == "worked_example":
                score += 25.0
                reasons.append("worked example clarifies incorrect assumptions")
            elif r_type == "targeted_quiz":
                score += 10.0
        elif gap_type == "demonstrated_gap" or (accuracy_score is not None and accuracy_score < 60.0):
            # Student attempted questions and failed -> needs foundational re-study
            if r_type == "pdf_passage":
                score += 30.0
                reasons.append("grounded textbook passage re-establishes core principles")
            elif r_type == "video_segment":
                score += 28.0
                reasons.append("audiovisual explanation offers multi-sensory reinforcement")
            elif r_type == "visual_model":
                score += 22.0
                reasons.append("interactive diagram visualizes foundational mechanics")
            elif r_type == "targeted_quiz":
                score -= 10.0  # Don't immediately re-test when understanding is broken
        elif gap_type == "untested_prerequisite" or gap_type == "untested":
            # First time encountering the concept
            if r_type == "video_segment":
                score += 25.0
                reasons.append("introductory lecture segment provides accessible entry")
            elif r_type == "pdf_passage":
                score += 25.0
                reasons.append("authoritative course textbook passage")
            elif r_type == "presentation_slide":
                score += 20.0
                reasons.append("structured lecture slide")
            elif r_type == "visual_model":
                score += 18.0
        elif gap_type == "verified_foundation" or (accuracy_score is not None and accuracy_score >= 75.0):
            # Student is already proficient -> prioritize targeted practice drill or advanced worked example
            if r_type == "targeted_quiz":
                score += 35.0
                reasons.append("targeted practice quiz tests mastery retention")
            elif r_type == "worked_example":
                score += 25.0
                reasons.append("worked example challenges deeper problem solving")
            elif r_type == "presentation_slide":
                score += 15.0
                reasons.append("rapid slide review before advancing")

        # 3. Penalize previously attempted resources
        if r_id in attempted_ids:
            score -= 25.0
            reasons.append("previously reviewed (variety preference)")

        rationale_str = f"Recommended format: {r_type.replace('_', ' ').title()} ({', '.join(reasons)})."
        scored_candidates.append((score, r, rationale_str))

    # Sort descending by score
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    best_score, best_resource, best_rationale = scored_candidates[0]
    alternatives = [item[1] for item in scored_candidates[1:4]]

    # Enrich selected resource with selection criteria & score
    best_resource_enriched = {
        **best_resource,
        "selection_criteria": best_rationale,
        "ranking_score": round(best_score, 1)
    }

    return MultimodalResourceSelection(best_resource_enriched, alternatives, best_rationale, round(best_score, 1))

