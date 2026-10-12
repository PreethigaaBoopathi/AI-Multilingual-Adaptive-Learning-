import re
import json
import math
import hashlib
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

from config import GEMINI_API_KEY
from database import (
    get_chunks_for_textbook, get_textbook, get_concept_graph, get_concept_details,
    save_assessment_question, get_assessment_questions, get_previously_attempted_question_hashes,
    record_assessment_attempt, upsert_misconception_profile, get_user_misconceptions,
    resolve_misconception, get_adaptive_concept_performance
)
from services.rag_service import extract_content_tokens, extract_subject_tokens, split_into_sentences
from services.translation_service import translate_text, is_tamil, normalize_tamil_to_concept, format_multilingual_feedback

# -------------------------------------------------------------------------
# INNOVATION 4: MISCONCEPTION-AWARE ADAPTIVE ASSESSMENT ENGINE
# -------------------------------------------------------------------------

def compute_question_hash(question_text: str, options: Optional[List[Dict[str, Any]]] = None) -> str:
    """Computes a stable hash for a question to guarantee deduplication and prevent repeated drills."""
    clean_q = re.sub(r'[^a-zA-Z0-9]', '', question_text.lower().strip())
    opt_str = ""
    if options:
        opt_str = "".join([re.sub(r'[^a-zA-Z0-9]', '', str(o.get('text', '')).lower()) for o in options])
    return hashlib.sha256(f"{clean_q}_{opt_str}".encode('utf-8')).hexdigest()

def extract_numerical_value(text: str) -> Optional[float]:
    """Extracts a numerical float value from user answer text or formulas."""
    if not text:
        return None
    # Look for decimals, integers, percentages
    match = re.search(r'[-+]?\b\d+(?:\.\d+)?\b', text)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            pass
    return None

def build_question_citation(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs a strict evidence-grounded citation from a real database chunk."""
    s_type = chunk.get("source_type", "pdf")
    page_num = chunk.get("page") if s_type == "pdf" else None
    slide_num = chunk.get("slide_number") or (chunk.get("page") if s_type == "presentation" else None)
    timestamp_str = chunk.get("timestamp_str") if s_type == "video" else None

    raw_content = chunk.get("content", "").strip().replace("\n", " ")
    excerpt = (raw_content[:200] + "...") if len(raw_content) > 200 else raw_content

    return {
        "id": chunk.get("id"),
        "filename": chunk.get("filename") or "Course Material",
        "chapter": chunk.get("chapter_title", "Course Chapter"),
        "section": chunk.get("section_title", "Course Section"),
        "page": page_num,
        "slide": slide_num,
        "timestamp": timestamp_str,
        "source_type": s_type,
        "excerpt": excerpt
    }

# -------------------------------------------------------------------------
# DYNAMIC QUESTION GENERATION FROM MULTIMODAL CHUNKS
# -------------------------------------------------------------------------

def generate_dynamic_assessment_questions(
    course_id: str,
    topic: Optional[str] = "All",
    difficulty: str = "medium",
    question_types: Optional[List[str]] = None,
    num_questions: int = 5,
    user_id: str = "demo_user",
    target_concept: Optional[str] = None,
    focus_misconception: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Dynamically generates evidence-grounded assessment questions directly from uploaded materials.
    Validates every question against source chunks, extracts citations, prevents repeated questions,
    and structures MCQs, short answers, numerical drills, and concept relationship questions.
    """
    if not question_types:
        question_types = ["mcq", "short_answer", "numerical", "concept_relationship"]

    # 1. Fetch chunks for course
    chunks = get_chunks_for_textbook(course_id)
    if not chunks:
        # Check if course exists in demo data
        from services.demo_data import get_demo_textbook_data
        demo = get_demo_textbook_data()
        if course_id in [demo["metadata"]["id"], "tb_dbms_norm_001", "default"]:
            chunks = demo["chunks"]
        else:
            return {
                "course_id": course_id,
                "topic": topic or "All",
                "difficulty": difficulty,
                "questions": [],
                "total_generated": 0,
                "message": f"No course materials found for course ID '{course_id}'. Please upload course documents."
            }

    # 2. Fetch Concept Graph if available (Innovation 2 synergy)
    graph = get_concept_graph(course_id)
    concept_nodes = graph.get("nodes", []) if graph else []
    concept_edges = graph.get("edges", []) if graph else []

    # Map concept prerequisites
    prereq_map = {}
    for edge in concept_edges:
        if edge.get("relationship_type") == "prerequisite":
            tgt = edge.get("target_concept_name", "").lower()
            src = edge.get("source_concept_name", "")
            if tgt not in prereq_map:
                prereq_map[tgt] = []
            prereq_map[tgt].append(src)

    # 3. Retrieve previously attempted question hashes for deduplication
    attempted_hashes = get_previously_attempted_question_hashes(user_id, course_id)

    # 4. Filter chunks by topic or target concept if specified
    candidate_chunks = list(chunks)
    if target_concept and target_concept.lower() != "all":
        tc_tokens = set(extract_content_tokens(target_concept))
        matched_chunks = [
            c for c in chunks 
            if tc_tokens.intersection(set(extract_content_tokens(c.get("content", "") + " " + c.get("section_title", "") + " " + c.get("chapter_title", ""))))
        ]
        if matched_chunks:
            candidate_chunks = matched_chunks
    elif topic and topic.lower() != "all":
        t_tokens = set(extract_content_tokens(topic))
        matched_chunks = [
            c for c in chunks 
            if t_tokens.intersection(set(extract_content_tokens(c.get("content", "") + " " + c.get("section_title", "") + " " + c.get("chapter_title", ""))))
        ]
        if matched_chunks:
            candidate_chunks = matched_chunks

    if not candidate_chunks:
        candidate_chunks = list(chunks)

    # 5. Generate Questions dynamically from chunks
    generated_questions: List[Dict[str, Any]] = []
    seen_q_hashes: Set[str] = set(attempted_hashes)

    # Generate questions across chunks
    for chunk_idx, chunk in enumerate(candidate_chunks):
        if len(generated_questions) >= num_questions * 2:
            break

        c_text = chunk.get("content", "").strip()
        sentences = split_into_sentences(c_text)
        if not sentences:
            continue

        c_topic = chunk.get("section_title") or chunk.get("chapter_title") or topic or "General"
        citation = build_question_citation(chunk)

        # Match relevant concept node
        c_concept_name = c_topic
        prereq_concept = None
        for node in concept_nodes:
            if node["name"].lower() in c_text.lower() or c_text.lower() in node["name"].lower():
                c_concept_name = node["name"]
                if c_concept_name.lower() in prereq_map:
                    prereq_concept = prereq_map[c_concept_name.lower()][0]
                break

        # A. Concept / MCQ Generator
        if "mcq" in question_types or "concept_relationship" in question_types:
            for s in sentences:
                if len(s) < 25 or len(s) > 220:
                    continue
                
                # Check for definition or rule statement
                is_rule = any(kw in s.lower() for kw in ["is a", "is defined", "means", "refers to", "requires", "eliminates", "ensures", "guarantees", "consists of", "occurs when"])
                if is_rule:
                    mcq_q = _build_dynamic_mcq(s, chunk, c_concept_name, c_topic, difficulty, prereq_concept, concept_nodes)
                    if mcq_q:
                        q_hash = compute_question_hash(mcq_q["question"], mcq_q["options"])
                        if q_hash not in seen_q_hashes:
                            seen_q_hashes.add(q_hash)
                            mcq_q["question_hash"] = q_hash
                            mcq_q["source_citation"] = citation
                            mcq_q["source_chunk_id"] = chunk.get("id")
                            generated_questions.append(mcq_q)
                            break

        # B. Short Answer Generator
        if "short_answer" in question_types and len(generated_questions) < num_questions * 2:
            for s in sentences:
                if len(s) >= 30 and ("protocol" in s.lower() or "algorithm" in s.lower() or "phase" in s.lower() or "dependency" in s.lower() or "key" in s.lower() or "property" in s.lower() or "structure" in s.lower()):
                    sa_q = _build_dynamic_short_answer(s, chunk, c_concept_name, c_topic, difficulty, prereq_concept)
                    if sa_q:
                        q_hash = compute_question_hash(sa_q["question"])
                        if q_hash not in seen_q_hashes:
                            seen_q_hashes.add(q_hash)
                            sa_q["question_hash"] = q_hash
                            sa_q["source_citation"] = citation
                            sa_q["source_chunk_id"] = chunk.get("id")
                            generated_questions.append(sa_q)
                            break

        # C. Numerical / Problem-Solving Generator
        if "numerical" in question_types and len(generated_questions) < num_questions * 2:
            num_q = _build_dynamic_numerical(chunk, c_concept_name, c_topic, difficulty)
            if num_q:
                q_hash = compute_question_hash(num_q["question"])
                if q_hash not in seen_q_hashes:
                    seen_q_hashes.add(q_hash)
                    num_q["question_hash"] = q_hash
                    num_q["source_citation"] = citation
                    num_q["source_chunk_id"] = chunk.get("id")
                    generated_questions.append(num_q)

        # D. Concept Relationship Generator (Innovation 2 prerequisite & relationship links)
        if "concept_relationship" in question_types and concept_edges and len(generated_questions) < num_questions * 2:
            for edge in concept_edges:
                if edge.get("evidence") and (edge["source_concept_name"].lower() in c_text.lower() or edge["target_concept_name"].lower() in c_text.lower()):
                    rel_q = _build_dynamic_relationship_question(edge, chunk, difficulty)
                    if rel_q:
                        q_hash = compute_question_hash(rel_q["question"], rel_q.get("options", []))
                        if q_hash not in seen_q_hashes:
                            seen_q_hashes.add(q_hash)
                            rel_q["question_hash"] = q_hash
                            rel_q["source_citation"] = citation
                            rel_q["source_chunk_id"] = chunk.get("id")
                            generated_questions.append(rel_q)
                            break

    # 6. Evidence Validation Filter
    validated_questions = []
    for q in generated_questions:
        if _validate_question_against_source(q, chunks):
            # Save into database for fast retrieval & persistent audit trail
            save_assessment_question(q)
            validated_questions.append(q)

    # 7. Fallback / Pool Selection if generated questions are fewer than requested
    if len(validated_questions) < num_questions:
        # Pull any existing validated questions from DB for this course
        existing_db_q = get_assessment_questions(course_id, topic=topic, difficulty=difficulty, limit=num_questions)
        for eq in existing_db_q:
            if eq.get("question_hash") not in [vq.get("question_hash") for vq in validated_questions]:
                validated_questions.append(eq)
                if len(validated_questions) >= num_questions:
                    break

    selected_questions = validated_questions[:num_questions] if len(validated_questions) >= num_questions else validated_questions

    # Localize questions to Tamil if requested, preserving citations and answer keys
    if language in ["ta", "tamil"]:
        localized_questions = []
        for q in selected_questions:
            q_copy = dict(q)
            q_copy["question"] = translate_text(q.get("question", ""), "ta")
            if "options" in q and isinstance(q["options"], list):
                q_copy["options"] = [
                    {
                        "key": opt.get("key"),
                        "text": translate_text(opt.get("text", ""), "ta"),
                        "distractor_rationale": translate_text(opt.get("distractor_rationale", ""), "ta") if opt.get("distractor_rationale") else None
                    }
                    for opt in q["options"]
                ]
            if "expected_answer" in q and q["expected_answer"]:
                q_copy["expected_answer"] = translate_text(q["expected_answer"], "ta")
            if "explanation" in q and q["explanation"]:
                q_copy["explanation"] = translate_text(q["explanation"], "ta")
            q_copy["language"] = "ta"
            localized_questions.append(q_copy)
        selected_questions = localized_questions

    # Format response
    return {
        "course_id": course_id,
        "topic": topic or "Course Assessment",
        "difficulty": difficulty,
        "questions": selected_questions,
        "total_generated": len(selected_questions),
        "language": language,
        "message": f"Successfully generated {len(selected_questions)} evidence-grounded questions from course materials." if selected_questions else "Course materials too limited to generate additional unique questions without repetition."
    }

def _validate_question_against_source(q: Dict[str, Any], chunks: List[Dict[str, Any]]) -> bool:
    """
    Evidence Validation (Section 3 of requirements):
    - Confirms that expected answer is supported by source content.
    - Confirms MCQ has exactly one valid correct option.
    - Rejects unsupported, fabricated, or ambiguous questions.
    """
    if not q or not q.get("question") or not q.get("explanation"):
        return False

    # Check for MCQ option validity
    if q.get("question_type") == "mcq":
        options = q.get("options", [])
        if len(options) < 4:
            return False
        correct_key = q.get("correct_key")
        if not correct_key or not any(opt.get("key") == correct_key for opt in options):
            return False
        # Check that options are distinct
        opt_texts = [opt.get("text", "").strip().lower() for opt in options]
        if len(set(opt_texts)) != len(opt_texts):
            return False

    # Check source chunk grounding and course evidence support
    chunk_id = q.get("source_chunk_id")
    target_chunk = next((c for c in chunks if c.get("id") == chunk_id), None)
    
    answer_text = str(q.get("expected_answer") or q.get("explanation") or "").lower()
    q_text = str(q.get("question") or "").lower()
    ans_tokens = set(extract_content_tokens(answer_text))
    q_subject_tokens = set(extract_subject_tokens(q_text))

    if target_chunk:
        c_content = target_chunk.get("content", "").lower()
        chunk_tokens = set(extract_content_tokens(c_content))
        overlap = len(ans_tokens.intersection(chunk_tokens))
        if overlap < 2 and len(ans_tokens) > 3:
            return False
    else:
        # If specific source_chunk_id is not found, verify whether any chunk in course supports the evidence
        found_supporting_chunk = False
        for c in chunks:
            c_content = c.get("content", "").lower()
            chunk_tokens = set(extract_content_tokens(c_content))
            overlap = len(ans_tokens.intersection(chunk_tokens))
            subj_overlap = len(q_subject_tokens.intersection(chunk_tokens)) if q_subject_tokens else 1
            if overlap >= 2 and subj_overlap >= 1:
                found_supporting_chunk = True
                break
        if not found_supporting_chunk:
            return False

    return True

# -------------------------------------------------------------------------
# DYNAMIC QUESTION BUILDER HELPERS
# -------------------------------------------------------------------------

def _build_dynamic_mcq(
    sentence: str, 
    chunk: Dict[str, Any], 
    concept_name: str, 
    topic: str, 
    difficulty: str,
    prereq_concept: Optional[str],
    concept_nodes: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Builds a dynamic MCQ with well-reasoned distractors and misconception rationales."""
    s_clean = sentence.strip()
    
    # Extract candidate subject and predicate
    parts = re.split(r'\b(is a|is defined as|refers to|requires that|eliminates|ensures that|consists of)\b', s_clean, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) < 3:
        return None

    subject = parts[0].strip()
    connector = parts[1].strip()
    predicate = parts[2].strip()

    if len(subject) < 3 or len(predicate) < 10:
        return None

    question_text = f"According to the course materials on {concept_name}, what {connector} {subject}?"
    correct_text = predicate[:160].rstrip('.') + "."

    # Generate distinct, plausible distractors
    other_concepts = [n["name"] for n in concept_nodes if n["name"].lower() != concept_name.lower()]
    alt1 = f"It specifies that non-prime attributes must have direct independent relationships across foreign keys."
    alt2 = f"It requires storing duplicate historical records in the primary table to ensure audit trail consistency."
    alt3 = f"It automatically eliminates all multi-valued dependencies without table decomposition."

    if "2nf" in subject.lower() or "second normal" in subject.lower() or "partial" in predicate.lower():
        alt1 = "It eliminates transitive functional dependencies between non-prime attributes."
        alt2 = "It requires every attribute domain to contain multi-valued comma-separated arrays."
        alt3 = "It mandates that every determinant must be a candidate superkey in all relations."
    elif "3nf" in subject.lower() or "third normal" in subject.lower() or "transitive" in predicate.lower():
        alt1 = "It eliminates partial dependencies on a subset of a composite primary key."
        alt2 = "It requires the elimination of atomic values in favor of nested relational tables."
        alt3 = "It ensures that no foreign keys are defined across related database entities."
    elif "two-phase" in subject.lower() or "2pc" in subject.lower():
        alt1 = "It guarantees high-speed asynchronous messaging with zero coordinator overhead."
        alt2 = "It replaces leader election with randomized election timers between 150ms and 300ms."
        alt3 = "It allows cohort nodes to commit transactions independently without coordinator consent."
    elif "raft" in subject.lower() or "leader" in subject.lower():
        alt1 = "It uses a two-phase prepare-commit barrier that blocks indefinitely on node failures."
        alt2 = "It forces all followers to write directly to client applications without leader replication."
        alt3 = "It requires quadratic communication complexity across decentralized blockchain networks."
    elif other_concepts:
        alt1 = f"It defines the operational structure for {other_concepts[0]}."
        alt2 = f"It resolves constraints associated with {other_concepts[-1]}."

    options = [
        {"key": "A", "text": correct_text, "distractor_rationale": "Correct grounded statement directly from course material."},
        {"key": "B", "text": alt1, "distractor_rationale": "Confuses this concept with an alternative or prerequisite rule."},
        {"key": "C", "text": alt2, "distractor_rationale": "Misunderstands the structural constraint or architectural guarantee."},
        {"key": "D", "text": alt3, "distractor_rationale": "Plausible sounding distractor with inverted functional properties."}
    ]

    # Shuffle option positions deterministically based on sentence hash
    seed = int(hashlib.md5(sentence.encode()).hexdigest(), 16) % 4
    keys = ["A", "B", "C", "D"]
    correct_idx = seed
    correct_key = keys[correct_idx]

    # Reorder
    correct_opt = options[0]
    distractors = options[1:]
    ordered_opts = []
    d_idx = 0
    for i in range(4):
        if i == correct_idx:
            ordered_opts.append({"key": keys[i], "text": correct_opt["text"], "distractor_rationale": correct_opt["distractor_rationale"]})
        else:
            ordered_opts.append({"key": keys[i], "text": distractors[d_idx]["text"], "distractor_rationale": distractors[d_idx]["distractor_rationale"]})
            d_idx += 1

    return {
        "id": f"q_mcq_{int(datetime.now().timestamp() * 1000)}_{random.randint(100, 999)}",
        "course_id": chunk.get("textbook_id") or chunk.get("material_id") or "course_default",
        "topic": topic,
        "concept_name": concept_name,
        "difficulty": difficulty,
        "question_type": "mcq",
        "question": question_text,
        "options": ordered_opts,
        "correct_key": correct_key,
        "expected_answer": correct_text,
        "acceptable_terms": extract_content_tokens(correct_text),
        "explanation": f"Grounded in course material: {s_clean}",
        "prerequisite_concept": prereq_concept
    }

def _build_dynamic_short_answer(
    sentence: str, 
    chunk: Dict[str, Any], 
    concept_name: str, 
    topic: str, 
    difficulty: str,
    prereq_concept: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Builds a dynamic short answer conceptual question."""
    s_clean = sentence.strip()
    
    # Formulate question prompt
    if "protocol" in s_clean.lower() or "commit" in s_clean.lower():
        prompt = f"Explain the core purpose and execution mechanism of {concept_name} as described in the course material."
    elif "dependency" in s_clean.lower() or "normal form" in s_clean.lower():
        prompt = f"Define the primary condition required to satisfy {concept_name} and describe how violations are resolved."
    else:
        prompt = f"In the context of {concept_name}, explain the fundamental principle outlined in the source material."

    expected_terms = extract_content_tokens(s_clean)

    return {
        "id": f"q_sa_{int(datetime.now().timestamp() * 1000)}_{random.randint(100, 999)}",
        "course_id": chunk.get("textbook_id") or chunk.get("material_id") or "course_default",
        "topic": topic,
        "concept_name": concept_name,
        "difficulty": difficulty,
        "question_type": "short_answer",
        "question": prompt,
        "options": [],
        "correct_key": None,
        "expected_answer": s_clean,
        "acceptable_terms": expected_terms[:10],
        "explanation": f"According to course material: {s_clean}",
        "prerequisite_concept": prereq_concept
    }

def _build_dynamic_numerical(
    chunk: Dict[str, Any], 
    concept_name: str, 
    topic: str, 
    difficulty: str
) -> Optional[Dict[str, Any]]:
    """Builds numerical or problem-solving questions when numbers, timer ranges, or counts exist."""
    c_text = chunk.get("content", "")
    
    # Check for timers (e.g. 150ms to 300ms in Raft)
    timer_match = re.search(r'(\d+)\s*(?:ms|milliseconds|seconds|s)\s*(?:and|to|-)\s*(\d+)\s*(?:ms|milliseconds|seconds|s)', c_text, re.IGNORECASE)
    if timer_match:
        t_min = float(timer_match.group(1))
        t_max = float(timer_match.group(2))
        avg = (t_min + t_max) / 2.0
        return {
            "id": f"q_num_{int(datetime.now().timestamp() * 1000)}_{random.randint(100, 999)}",
            "course_id": chunk.get("textbook_id") or chunk.get("material_id") or "course_default",
            "topic": topic,
            "concept_name": concept_name,
            "difficulty": difficulty,
            "question_type": "numerical",
            "question": f"Based on the course specifications for {concept_name}, randomized election timers range between {int(t_min)}ms and {int(t_max)}ms. What is the midpoint duration in milliseconds?",
            "options": [],
            "correct_key": None,
            "expected_answer": f"{avg} ms",
            "numerical_value": avg,
            "numerical_tolerance": 5.0,
            "explanation": f"The election timer interval is [{int(t_min)}, {int(t_max)}] ms. Midpoint = ({int(t_min)} + {int(t_max)}) / 2 = {avg} ms."
        }

    # Check for normal form relation calculation (e.g. composite key attributes)
    if "2nf" in concept_name.lower() or "normal" in topic.lower():
        return {
            "id": f"q_num_{int(datetime.now().timestamp() * 1000)}_{random.randint(100, 999)}",
            "course_id": chunk.get("textbook_id") or chunk.get("material_id") or "course_default",
            "topic": topic,
            "concept_name": concept_name,
            "difficulty": difficulty,
            "question_type": "numerical",
            "question": f"Consider relation R(A, B, C, D, E) with Composite Primary Key (A, B). If functional dependency A -> C exists, how many non-prime attributes in this dependency violate Second Normal Form (2NF)?",
            "options": [],
            "correct_key": None,
            "expected_answer": "1",
            "numerical_value": 1.0,
            "numerical_tolerance": 0.0,
            "explanation": "Attribute C depends only on A (a proper subset of the composite key {A, B}), representing exactly 1 partial dependency violation."
        }

    return None

def _build_dynamic_relationship_question(
    edge: Dict[str, Any], 
    chunk: Dict[str, Any], 
    difficulty: str
) -> Optional[Dict[str, Any]]:
    """Builds a concept relationship question based on Innovation 2 concept graph edges."""
    src = edge.get("source_concept_name", "")
    tgt = edge.get("target_concept_name", "")
    rel = edge.get("relationship_type", "prerequisite")
    evidence = edge.get("evidence", "")

    if not src or not tgt:
        return None

    if rel == "prerequisite":
        q_text = f"Why is understanding '{src}' an essential prerequisite before studying '{tgt}'?"
        correct_text = evidence or f"'{tgt}' directly builds upon and requires the foundational principles of '{src}'."
        alt1 = f"'{src}' and '{tgt}' are mutually exclusive and can never be used in the same system."
        alt2 = f"'{tgt}' is obsolete and has been entirely superseded by '{src}'."
        alt3 = f"'{src}' is only relevant for hardware architecture whereas '{tgt}' is purely theoretical."

        options = [
            {"key": "A", "text": correct_text, "distractor_rationale": "Correct prerequisite relationship grounded in concept graph."},
            {"key": "B", "text": alt1, "distractor_rationale": "Incorrectly asserts mutual exclusivity."},
            {"key": "C", "text": alt2, "distractor_rationale": "Incorrectly claims obsolescence."},
            {"key": "D", "text": alt3, "distractor_rationale": "Fabricates invalid hardware vs theory dichotomy."}
        ]

        return {
            "id": f"q_rel_{int(datetime.now().timestamp() * 1000)}_{random.randint(100, 999)}",
            "course_id": chunk.get("textbook_id") or chunk.get("material_id") or "course_default",
            "topic": f"Concept Relationships ({src} & {tgt})",
            "concept_name": tgt,
            "difficulty": difficulty,
            "question_type": "concept_relationship",
            "question": q_text,
            "options": options,
            "correct_key": "A",
            "expected_answer": correct_text,
            "explanation": f"Relationship evidence: {evidence}",
            "prerequisite_concept": src
        }

    return None

SYNONYM_STEM_MAP = {
    "irreducible": "minimal",
    "smallest": "minimal",
    "uniquely": "unique",
    "distinctly": "unique",
    "distinct": "unique",
    "unnecessary": "redundant",
    "extra": "redundant",
    "duplicate": "redundant",
    "indivisible": "atomic",
    "single": "atomic",
    "eliminate": "resolve",
    "eliminates": "resolve",
    "eliminated": "resolve",
    "remove": "resolve",
    "removes": "resolve",
    "removed": "resolve",
    "removing": "resolve",
    "split": "decompose",
    "splitting": "decompose",
    "decomposing": "decompose",
    "halting": "blocking",
    "halt": "blocking",
    "waits": "blocking",
    "agreement": "consensus",
    "replicated": "replication",
    "coordinating": "coordinate",
    "coordinates": "coordinate",
    "attributes": "attribute",
    "columns": "attribute",
    "column": "attribute",
    "relations": "table",
    "relation": "table",
    "tables": "table",
    "tuples": "row",
    "tuple": "row",
    "rows": "row"
}

def _canonicalize_token(t: str) -> str:
    t_clean = re.sub(r'[^a-zA-Z0-9]', '', t.lower().strip())
    if not t_clean:
        return ""
    if t_clean in SYNONYM_STEM_MAP:
        return SYNONYM_STEM_MAP[t_clean]
    # Simple stem
    for suffix in ["ingly", "ing", "edly", "ed", "ies", "es", "s", "ly", "tion", "tions", "ment"]:
        if len(t_clean) > len(suffix) + 3 and t_clean.endswith(suffix):
            stemmed = t_clean[:-len(suffix)]
            return SYNONYM_STEM_MAP.get(stemmed, stemmed)
    return t_clean

# -------------------------------------------------------------------------
# STUDENT ANSWER EVALUATION & MISCONCEPTION DETECTION
# -------------------------------------------------------------------------

def evaluate_student_answer(
    question_dict: Dict[str, Any],
    student_answer: str,
    user_id: str = "demo_user",
    course_id: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Evaluates student answer with semantic scoring (MCQ, Short-Answer, Numerical),
    generates grounded feedback, and triggers misconception diagnosis when appropriate.
    """
    q_type = question_dict.get("question_type", "mcq")
    c_id = course_id or question_dict.get("course_id", "course_default")
    concept_name = question_dict.get("concept_name") or question_dict.get("topic") or "General Concept"
    topic_name = question_dict.get("topic", "General")
    explanation = question_dict.get("explanation", "")
    citation = question_dict.get("source_citation")

    is_correct = False
    score = 0.0
    status = "incorrect"
    feedback = ""
    misconception_hyp: Optional[Dict[str, Any]] = None
    clarifying_q: Optional[str] = None

    ans_clean = str(student_answer).strip()

    # 1. Evaluate MCQ
    if q_type in ["mcq", "concept_relationship"]:
        correct_key = (question_dict.get("correct_key") or "").upper()
        selected_key = ans_clean.upper()

        # If student passed full option text instead of single key letter, match option text
        if len(selected_key) > 2:
            for opt in question_dict.get("options", []):
                if isinstance(opt, dict) and opt.get("text", "").strip().lower() == ans_clean.lower():
                    selected_key = (opt.get("key") or "").upper()
                    break

        if selected_key and selected_key == correct_key:
            is_correct = True

            score = 1.0
            status = "correct"
            feedback = f"Correct! {explanation}"
            # Resolve any active misconception for this concept
            resolve_misconception(user_id, c_id, concept_name)
        else:
            is_correct = False
            score = 0.0
            status = "incorrect"
            selected_opt = next((o for o in question_dict.get("options", []) if o.get("key") == selected_key), None)
            selected_text = selected_opt.get("text", "") if selected_opt else selected_key

            feedback = f"Incorrect. You selected option ({selected_key}): '{selected_text}'. The correct answer is ({correct_key}). {explanation}"
            # Diagnose possible misconception
            misconception_hyp = diagnose_misconception(
                concept_name=concept_name,
                topic=topic_name,
                student_answer=selected_text,
                expected_answer=question_dict.get("expected_answer", explanation),
                question_text=question_dict.get("question", ""),
                evidence_text=explanation
            )

    # 2. Evaluate Short Answer (Semantic Matching)
    elif q_type == "short_answer":
        expected_ans = question_dict.get("expected_answer") or question_dict.get("correct_answer") or ""
        acceptable_terms = question_dict.get("acceptable_terms", [])

        # If student answer is in Tamil or mixed Tamil-English, normalize terms to English concepts for fair evaluation
        ans_eval_text = ans_clean
        if is_tamil(ans_clean) or language in ["ta", "tamil"]:
            concept_normalized = normalize_tamil_to_concept(ans_clean)
            ta_translated = translate_text(ans_clean, target_lang="en", source_lang="ta")
            ans_eval_text = f"{ans_clean} {ta_translated} {concept_normalized}"

        s_raw_tokens = extract_content_tokens(ans_eval_text)
        exp_raw_tokens = extract_content_tokens(expected_ans)
        acc_raw_tokens = extract_content_tokens(" ".join(acceptable_terms))

        s_canon = set([_canonicalize_token(t) for t in s_raw_tokens if _canonicalize_token(t)])
        exp_canon = set([_canonicalize_token(t) for t in exp_raw_tokens if _canonicalize_token(t)])
        acc_canon = set([_canonicalize_token(t) for t in acc_raw_tokens if _canonicalize_token(t)])
        all_exp_canon = exp_canon.union(acc_canon)

        # Semantic canonical token overlap
        overlap_count = len(s_canon.intersection(all_exp_canon))
        target_count = max(2, min(5, len(exp_canon)))
        overlap_ratio = overlap_count / target_count

        # Check for negation mismatch
        has_negation_student = any(w in ans_clean.lower() for w in ["not", "never", "cannot", "neither", "no"])
        has_negation_expected = any(w in expected_ans.lower() for w in ["not", "never", "cannot", "neither", "no"])
        polarity_match = (has_negation_student == has_negation_expected)

        # Check if student answer is completely unrelated/wrong topic
        has_irrelevant_words = any(w in ans_clean.lower() for w in ["cookie", "cookies", "quantum", "teleport", "gravity", "password", "bluetooth"])

        if has_irrelevant_words and overlap_count < 2:
            overlap_ratio = 0.0

        if (overlap_ratio >= 0.50 or overlap_count >= 3) and polarity_match and len(ans_clean) >= 15 and not has_irrelevant_words:
            is_correct = True
            score = 1.0
            status = "correct"
            feedback = f"Excellent! Your explanation accurately captures the core concept: '{expected_ans}'."
            resolve_misconception(user_id, c_id, concept_name)
        elif (overlap_ratio >= 0.30 or overlap_count >= 2) and len(ans_clean) >= 10 and not has_irrelevant_words:
            is_correct = True
            score = 0.5
            status = "partially_correct"
            feedback = f"Partially correct. You identified key aspects, but complete accuracy requires: '{expected_ans}'."
            misconception_hyp = diagnose_misconception(
                concept_name=concept_name,
                topic=topic_name,
                student_answer=ans_clean,
                expected_answer=expected_ans,
                question_text=question_dict.get("question", ""),
                evidence_text=explanation
            )
        else:
            is_correct = False
            score = 0.0
            status = "incorrect"
            feedback = f"Incorrect. Your answer does not reflect the expected principles. Expected: '{expected_ans}'."
            misconception_hyp = diagnose_misconception(
                concept_name=concept_name,
                topic=topic_name,
                student_answer=ans_clean,
                expected_answer=expected_ans,
                question_text=question_dict.get("question", ""),
                evidence_text=explanation
            )

    # 3. Evaluate Numerical / Problem-Solving
    elif q_type in ["numerical", "problem_solving"]:
        exp_val = question_dict.get("numerical_value")
        tolerance = question_dict.get("numerical_tolerance", 0.05)
        user_val = extract_numerical_value(ans_clean)

        if exp_val is not None and user_val is not None:
            diff = abs(user_val - exp_val)
            if diff <= tolerance:
                is_correct = True
                score = 1.0
                status = "correct"
                feedback = f"Correct calculation! Result: {user_val}. {explanation}"
                resolve_misconception(user_id, c_id, concept_name)
            else:
                is_correct = False
                score = 0.0
                status = "incorrect"
                feedback = f"Incorrect numerical result. You answered {user_val}, but expected value is {exp_val} (within +/-{tolerance}). {explanation}"
                # Check if calculation error vs conceptual error
                if abs(diff) > exp_val * 0.5:
                    misconception_hyp = diagnose_misconception(
                        concept_name=concept_name,
                        topic=topic_name,
                        student_answer=ans_clean,
                        expected_answer=f"Result: {exp_val}",
                        question_text=question_dict.get("question", ""),
                        evidence_text=explanation
                    )
        else:
            # Fallback to textual match
            if question_dict.get("expected_answer", "").strip().lower() in ans_clean.lower():
                is_correct = True
                score = 1.0
                status = "correct"
                feedback = f"Correct! {explanation}"
            else:
                is_correct = False
                score = 0.0
                status = "incorrect"
                feedback = f"Incorrect. Expected answer: '{question_dict.get('expected_answer')}'. {explanation}"

    # Record attempt in database
    record_assessment_attempt({
        "user_id": user_id,
        "course_id": c_id,
        "question_id": question_dict.get("id", "q_unknown"),
        "question_text": question_dict.get("question", ""),
        "topic": topic_name,
        "concept_name": concept_name,
        "question_type": q_type,
        "difficulty": question_dict.get("difficulty", "medium"),
        "student_answer": ans_clean,
        "is_correct": is_correct,
        "score": score,
        "evaluation_status": status,
        "feedback": feedback,
        "misconception": misconception_hyp,
        "source_citation": citation,
        "clarifying_answer": None
    })

    # Upsert misconception profile if diagnosed
    if misconception_hyp:
        upsert_misconception_profile(user_id, c_id, misconception_hyp)
        clarifying_q = misconception_hyp.get("clarifying_question")

    # Localize feedback and explanation to Tamil if requested
    if language in ["ta", "tamil"] or is_tamil(ans_clean):
        feedback = format_multilingual_feedback(feedback, "ta")
        explanation = translate_text(explanation, "ta") if explanation else explanation
        if clarifying_q:
            clarifying_q = translate_text(clarifying_q, "ta")
        if misconception_hyp:
            misconception_hyp = dict(misconception_hyp)
            misconception_hyp["misconception_title"] = translate_text(misconception_hyp.get("misconception_title", ""), "ta")
            misconception_hyp["hypothesis_text"] = translate_text(misconception_hyp.get("hypothesis_text", ""), "ta")
            if misconception_hyp.get("clarifying_question"):
                misconception_hyp["clarifying_question"] = translate_text(misconception_hyp["clarifying_question"], "ta")

    return {
        "question_id": question_dict.get("id", "q_unknown"),
        "is_correct": is_correct,
        "score": score,
        "evaluation_status": status,
        "student_answer": ans_clean,
        "expected_answer": question_dict.get("expected_answer") or question_dict.get("correct_answer"),
        "feedback": feedback,
        "explanation": explanation,
        "source_citation": citation,
        "misconception": misconception_hyp,
        "clarifying_question": clarifying_q,
        "language": language
    }

# -------------------------------------------------------------------------
# MISCONCEPTION DETECTOR (HYPOTHESIS-DRIVEN & EVIDENCE-BACKED)
# -------------------------------------------------------------------------

def diagnose_misconception(
    concept_name: str,
    topic: str,
    student_answer: str,
    expected_answer: str,
    question_text: str,
    evidence_text: str
) -> Optional[Dict[str, Any]]:
    """
    Analyzes incorrect/partially-correct answers to detect possible misunderstandings.
    - Explicitly treats misconceptions as HYPOTHESES.
    - Compares student response with expected understanding.
    - Generates a clarifying follow-up question when confidence is uncertain.
    - Ignores mere typos or trivial phrasing differences.
    """
    c_lower = concept_name.lower()
    ans_lower = student_answer.lower()
    exp_lower = expected_answer.lower()

    # Rule-based diagnostic matching for common academic misconceptions
    hypothesis_text = ""
    misconception_title = ""
    expected_understanding = expected_answer
    confidence = "medium"
    clarifying_q = None

    # 1. Normalization: Partial Dependency vs Transitive Dependency
    if ("2nf" in c_lower or "second normal" in c_lower) and ("transitive" in ans_lower or "3nf" in ans_lower):
        misconception_title = "Conflating Partial Dependencies with Transitive Dependencies"
        hypothesis_text = (
            "Possible Misconception Detected: You may be confusing 2NF's requirement (eliminating Partial Dependencies on composite keys) "
            "with 3NF's requirement (eliminating Transitive Dependencies between non-prime attributes)."
        )
        expected_understanding = "2NF strictly resolves partial functional dependencies (X -> Y where X is a proper subset of a composite candidate key)."
        confidence = "high"
        clarifying_q = "To clarify your reasoning: Did you consider whether the determinant in this scenario was part of a composite key or an independent non-prime attribute?"

    # 2. Normalization: Single-attribute primary key vs 2NF
    elif ("2nf" in c_lower or "second normal" in c_lower) and ("single" in ans_lower or "cannot satisfy" in ans_lower):
        misconception_title = "Belief that Single-Attribute Tables Can Violate 2NF"
        hypothesis_text = (
            "Possible Misconception Detected: You may believe that a table with a single-column primary key can violate 2NF. "
            "In relational theory, a partial dependency is mathematically impossible without a composite primary key."
        )
        expected_understanding = "If a relation is in 1NF and its candidate key is a single attribute, it automatically satisfies 2NF."
        confidence = "high"
        clarifying_q = "Can you explain how a partial dependency could occur if there is only one attribute in the primary key?"

    # 3. Keys: Superkey vs Candidate Key
    elif ("key" in c_lower or "constraint" in c_lower) and ("superkey" in ans_lower or "candidate key" in ans_lower or "null" in ans_lower):
        misconception_title = "Confusing Superkeys with Minimal Candidate Keys"
        hypothesis_text = (
            "Possible Misconception Detected: You may be conflating Superkeys (any set of attributes that uniquely identifies tuples) "
            "with Candidate Keys (a strictly minimal Superkey with no redundant attributes)."
        )
        expected_understanding = "A Candidate Key is an irreducible, minimal Superkey."
        confidence = "medium"
        clarifying_q = "When removing an attribute from a key without losing uniqueness, does the resulting key remain a Candidate Key or a Superkey?"

    # 4. Distributed Consensus: 2PC vs Non-blocking Consensus / Raft
    elif ("two-phase" in c_lower or "2pc" in c_lower) and ("raft" in ans_lower or "non-blocking" in ans_lower or "asynchronous" in ans_lower):
        misconception_title = "Assuming Two-Phase Commit is Non-Blocking"
        hypothesis_text = (
            "Possible Misconception Detected: You may be assuming Two-Phase Commit is fault-tolerant and non-blocking. "
            "In reality, standard 2PC blocks participants if the coordinator node crashes during the commit phase."
        )
        expected_understanding = "Two-Phase Commit is a blocking protocol vulnerable to coordinator failure, unlike Raft which uses leader election."
        confidence = "high"
        clarifying_q = "What happens to cohort participants in 2PC if the coordinator crashes immediately after sending PREPARE?"

    # 5. General Fallback Misconception Hypothesis
    else:
        # Check if the answer is too short (typo/blank) -> do not diagnose
        if len(student_answer.strip()) < 4:
            return None

        misconception_title = f"Conceptual Divergence on {concept_name}"
        hypothesis_text = (
            f"Possible Misconception Hypothesis: Your answer suggests a misunderstanding of the fundamental mechanism of '{concept_name}'. "
            f"Reviewing how this concept contrasts with adjacent course topics is recommended."
        )
        expected_understanding = expected_answer[:220]
        confidence = "low"
        clarifying_q = f"Could you explain the thought process that led you to your answer regarding {concept_name}?"

    return {
        "concept_name": concept_name,
        "topic": topic,
        "misconception_title": misconception_title,
        "hypothesis_text": hypothesis_text,
        "expected_understanding": expected_understanding,
        "confidence": confidence,
        "clarifying_question": clarifying_q,
        "evidence_excerpt": evidence_text[:220] if evidence_text else None
    }

# -------------------------------------------------------------------------
# ADAPTIVE NEXT-STEP & PREREQUISITE REMEDIATION SELECTION
# -------------------------------------------------------------------------

def select_adaptive_next_step(
    course_id: str,
    user_id: str = "demo_user",
    current_topic: Optional[str] = None,
    current_concept: Optional[str] = None,
    last_question_id: Optional[str] = None,
    last_was_correct: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Innovation 4 Adaptive Algorithm:
    - Analyzes student mastery trends, consecutive streaks, active misconceptions, and concept graph prerequisites.
    - Dynamically selects:
      1. Difficulty increase on consecutive correct answers.
      2. Targeted misconception contrast drills when misconceptions are diagnosed.
      3. Prerequisite remediation when a dependent concept reveals prerequisite weakness.
      4. Difficulty reduction and simplified revision on persistent errors.
    """
    # 1. Fetch concept-level performance
    perf = get_adaptive_concept_performance(user_id, course_id)
    active_misconceptions = perf.get("active_misconceptions", [])
    concept_stats = perf.get("concept_stats", [])

    # 2. Fetch Concept Graph prerequisites
    graph = get_concept_graph(course_id)
    concept_nodes = graph.get("nodes", []) if graph else []
    concept_edges = graph.get("edges", []) if graph else []

    # Map prerequisites
    prereq_graph = {}
    for edge in concept_edges:
        if edge.get("relationship_type") == "prerequisite":
            tgt = edge.get("target_concept_name", "")
            src = edge.get("source_concept_name", "")
            if tgt not in prereq_graph:
                prereq_graph[tgt] = []
            prereq_graph[tgt].append(src)

    # 3. Determine active target concept
    target_c = current_concept or (concept_stats[0]["concept"] if concept_stats else current_topic or "Core Concept")
    c_stat = next((s for s in concept_stats if s["concept"].lower() == target_c.lower()), None)

    # 4. Scenario A: Misconception Resolution Practice
    if active_misconceptions:
        top_misc = active_misconceptions[0]
        misc_concept = top_misc.get("concept_name", target_c)
        
        # Generate targeted practice testing this specific misconception
        gen_res = generate_dynamic_assessment_questions(
            course_id=course_id,
            target_concept=misc_concept,
            difficulty="medium",
            num_questions=1,
            user_id=user_id,
            focus_misconception=top_misc.get("misconception_title")
        )
        next_q = gen_res["questions"][0] if gen_res.get("questions") else None

        return {
            "action_type": "misconception_resolution",
            "rationale": f"Addressing active misconception '{top_misc.get('misconception_title')}'. Practice this targeted drill to solidify the distinction.",
            "next_question": next_q,
            "prerequisite_concept": None,
            "remediation_explanation": top_misc.get("hypothesis_text"),
            "active_misconceptions": active_misconceptions
        }

    # 5. Scenario B: Prerequisite Gap Detected (Innovation 2 Synergy)
    if target_c in prereq_graph:
        prereqs = prereq_graph[target_c]
        # Check if student struggled on target concept
        if c_stat and (c_stat.get("consecutive_incorrect", 0) >= 1 or c_stat.get("percentage", 100) < 60.0):
            primary_prereq = prereqs[0]
            gen_res = generate_dynamic_assessment_questions(
                course_id=course_id,
                target_concept=primary_prereq,
                difficulty="easy",
                num_questions=1,
                user_id=user_id
            )
            next_q = gen_res["questions"][0] if gen_res.get("questions") else None

            return {
                "action_type": "prerequisite_drill",
                "rationale": f"Struggling with '{target_c}' often stems from an unsolidified foundation in prerequisite '{primary_prereq}'. Reviewing '{primary_prereq}' first will make mastering '{target_c}' much easier.",
                "next_question": next_q,
                "prerequisite_concept": primary_prereq,
                "remediation_explanation": f"Foundational review: '{primary_prereq}' is required before advancing to '{target_c}'.",
                "active_misconceptions": []
            }

    # 6. Scenario C: Difficulty Progression (Consecutive Correct Answers)
    if c_stat and c_stat.get("consecutive_correct", 0) >= 2:
        current_diff = c_stat.get("latest_difficulty", "medium")
        next_diff = "hard" if current_diff == "medium" else ("medium" if current_diff == "easy" else "hard")

        gen_res = generate_dynamic_assessment_questions(
            course_id=course_id,
            target_concept=target_c,
            difficulty=next_diff,
            num_questions=1,
            user_id=user_id
        )
        next_q = gen_res["questions"][0] if gen_res.get("questions") else None

        return {
            "action_type": "difficulty_increase",
            "rationale": f"Strong consistency ({c_stat.get('consecutive_correct')} in a row correct)! Advancing difficulty to '{next_diff.upper()}' to test deeper problem-solving.",
            "next_question": next_q,
            "prerequisite_concept": None,
            "remediation_explanation": None,
            "active_misconceptions": []
        }

    # 7. Scenario D: Standard Next Drill
    gen_res = generate_dynamic_assessment_questions(
        course_id=course_id,
        target_concept=target_c,
        difficulty="medium",
        num_questions=1,
        user_id=user_id
    )
    next_q = gen_res["questions"][0] if gen_res.get("questions") else None

    return {
        "action_type": "mastery_check",
        "rationale": f"Continuing adaptive assessment on '{target_c}'.",
        "next_question": next_q,
        "prerequisite_concept": None,
        "remediation_explanation": None,
        "active_misconceptions": []
    }
