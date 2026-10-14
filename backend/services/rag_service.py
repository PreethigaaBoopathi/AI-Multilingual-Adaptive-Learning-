import re
import math
from typing import Dict, Any, List, Optional, Tuple, Set
from config import GEMINI_API_KEY, get_gemini_client, FAST_GEMINI_MODELS, is_gemini_available, mark_gemini_quota_exhausted
from services.translation_service import translate_text, is_tamil, normalize_tamil_to_concept
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import get_chunks_for_textbook, get_concept_graph, get_concept_details

# Common conversational and generic stop words
ENGLISH_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
    "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves", "tell", "explain", "describe", "discuss", "define",
    "give", "please", "detail", "details", "briefly", "summary", "summarize", "notes", "write", "know",
    "show", "teach", "answer", "question", "questions", "meaning", "mean", "means", "info", "information"
}

# Meta-query keywords that specify location, structure, or framing rather than domain subjects
META_QUERY_WORDS = {
    "uploaded", "materials", "material", "textbook", "textbooks", "course", "courses",
    "notes", "syllabus", "lecture", "lectures", "slide", "slides", "pdf", "video", "videos",
    "covered", "uncovered", "outside", "inside", "mention", "mentioned", "contain", "contained",
    "provide", "provided", "include", "included", "available", "file", "files", "document", "documents",
    "passage", "passages", "section", "sections", "chapter", "chapters", "page", "pages",
    "topic", "topics", "subject", "subjects", "concept", "concepts", "something", "anything", "thing",
    "segment", "segments", "chunk", "chunks", "part", "parts", "unit", "units", "portion", "portions",
    "clip", "clips", "timestamp", "timestamps", "transcript", "transcripts"
}

# Broad category words
GENERIC_CATEGORY_TERMS = {
    "algorithm", "protocol", "system", "systems", "process", "processes", "model", "models",
    "structure", "structures", "method", "methods", "function", "functions", "property", "properties",
    "table", "tables", "level", "levels", "type", "types", "design", "approach", "technique",
    "techniques", "theory", "problem", "solution", "framework", "analysis", "overview", "application",
    "applications", "mechanism", "mechanisms", "rule", "rules", "definition", "phase", "phases",
    "step", "steps", "component", "components", "architecture"
}

# Common action verbs, generic adjectives, and auxiliary database terms
COMMON_ACTION_TERMS = {
    "query", "queries", "range", "ranges", "operation", "operations", "value", "values",
    "data", "set", "sets", "item", "items", "number", "numbers", "state", "states",
    "time", "times", "case", "cases", "example", "examples", "result", "results",
    "order", "orders", "read", "write", "call", "send", "receive", "check", "need",
    "use", "used", "using", "work", "works", "working", "different", "difference",
    "differences", "comparison", "compare", "main", "major", "basic", "simple", "complex",
    "good", "bad", "high", "low", "minimum", "minimums", "maximum", "maximums", "mean", "means",
    "first", "second", "third", "initial", "final"
}

def extract_content_tokens(text: str) -> List[str]:
    """Extract lowercase alphanumeric tokens excluding generic English stop words."""
    if not text:
        return []
    words = re.findall(r'\b[a-zA-Z0-9_\-\.]+\b', text.lower())
    return [w for w in words if w not in ENGLISH_STOP_WORDS and len(w) > 1]

def extract_subject_tokens(query: str) -> List[str]:
    """Extract core domain subject tokens excluding meta-query framing, category nouns, and generic actions."""
    tokens = extract_content_tokens(query)
    # 1. Filter out meta words (e.g. uploaded, materials, covered, segment, page)
    non_meta = [t for t in tokens if t not in META_QUERY_WORDS]
    # 2. Filter out generic category terms and common action verbs/adjectives
    core = [t for t in non_meta if t not in GENERIC_CATEGORY_TERMS and t not in COMMON_ACTION_TERMS]
    if core:
        return core
    # 3. If all tokens were action/category terms, fallback to category terms
    category_fallback = [t for t in non_meta if t not in GENERIC_CATEGORY_TERMS]
    if category_fallback:
        return category_fallback
    return non_meta

def split_into_sentences(text: str) -> List[str]:
    """Split text into individual sentences for claim-level validation."""
    if not text:
        return []
    # Split on sentence terminals
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9\-\*\"\(])|\n+', text)
    cleaned = []
    for s in raw_sentences:
        s_clean = s.strip()
        # Clean bullet indicators and numbers
        s_clean = re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', s_clean).strip()
        if len(s_clean) >= 12 and not s_clean.startswith("[Source"):
            cleaned.append(s_clean)
    return cleaned

def get_concept_graph_boosts(query: str, course_id: Optional[str]) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """
    Leverages Innovation 2 Concept Graph (if available) to identify related concepts
    and compute relevance boosts for chunks connected to matched concepts.
    """
    if not course_id:
        return {}, []

    try:
        graph = get_concept_graph(course_id)
        if not graph or not graph.get("nodes"):
            return {}, []

        subject_tokens = set(extract_subject_tokens(query))
        query_tokens = set(extract_content_tokens(query))
        tokens_to_match = subject_tokens if subject_tokens else query_tokens

        matched_concepts = []
        chunk_boosts: Dict[str, float] = {}

        for node in graph["nodes"]:
            c_name = node["name"].lower()
            c_tokens = set(extract_content_tokens(c_name))
            
            # Direct or token overlap match
            is_match = (
                (bool(tokens_to_match) and c_name in query.lower()) or 
                (bool(tokens_to_match) and query.lower() in c_name) or 
                (c_tokens and tokens_to_match and len(tokens_to_match.intersection(c_tokens)) >= max(1, len(c_tokens) * 0.4))
            )

            if is_match:
                matched_concepts.append(node)
                # Boost chunks linked directly in sources
                for src in node.get("sources", []):
                    cu_id = src.get("content_unit_id")
                    if cu_id:
                        chunk_boosts[cu_id] = 1.0

        # Also find related/prerequisite concepts for matched concepts
        related_concept_list = []
        seen_concept_ids = set()

        for mc in matched_concepts:
            cid = mc["id"]
            if cid not in seen_concept_ids:
                seen_concept_ids.add(cid)
                related_concept_list.append({
                    "id": cid,
                    "name": mc["name"],
                    "topic": mc.get("topic", "Core Concepts"),
                    "relationship_type": "matched_concept",
                    "source_types": mc.get("source_types", [])
                })

            # Check edges for prerequisites and related concepts
            for edge in graph.get("edges", []):
                if edge["target_concept_id"] == cid:
                    src_id = edge["source_concept_id"]
                    if src_id not in seen_concept_ids:
                        seen_concept_ids.add(src_id)
                        related_concept_list.append({
                            "id": src_id,
                            "name": edge["source_concept_name"],
                            "topic": mc.get("topic", "Related Topics"),
                            "relationship_type": edge.get("relationship_type", "prerequisite"),
                            "source_types": []
                        })
                elif edge["source_concept_id"] == cid:
                    tgt_id = edge["target_concept_id"]
                    if tgt_id not in seen_concept_ids:
                        seen_concept_ids.add(tgt_id)
                        related_concept_list.append({
                            "id": tgt_id,
                            "name": edge["target_concept_name"],
                            "topic": mc.get("topic", "Related Topics"),
                            "relationship_type": edge.get("relationship_type", "dependent"),
                            "source_types": []
                        })

        return chunk_boosts, related_concept_list[:6]
    except Exception as e:
        print(f"Concept graph enhancement note: {e}")
        return {}, []

def retrieve_relevant_chunks(
    chunks: List[Dict[str, Any]], 
    query: str, 
    course_id: Optional[str] = None,
    top_k: int = 5
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Performs multimodal TF-IDF, N-Gram, and Concept-Graph enriched retrieval across chunks.
    Preserves exact provenance (PDF page, PPT slide, MP4 timestamp, and media).
    """
    if not chunks:
        if course_id:
            chunks = get_chunks_for_textbook(course_id)
        if not chunks:
            return [], []

    # Get Innovation 2 Concept Graph boosts & related concept list
    chunk_boosts, related_concepts = get_concept_graph_boosts(query, course_id)

    query_tokens = extract_content_tokens(query)
    subject_tokens = extract_subject_tokens(query)
    tokens_for_scoring = subject_tokens if subject_tokens else query_tokens
    q_lower = query.lower()

    # Pre-score via TF-IDF & Cosine Similarity
    corpus = [f"{c.get('chapter_title', '')} {c.get('section_title', '')} {c.get('content', '')}" for c in chunks]
    tfidf_scores = [0.0] * len(chunks)
    
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
        tfidf_matrix = vectorizer.fit_transform(corpus)
        query_vec = vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        tfidf_scores = [float(s) for s in similarities]
    except Exception:
        tfidf_scores = [0.0] * len(chunks)

    scored_chunks = []
    for idx, c in enumerate(chunks):
        c_content = c.get("content", "")
        c_lower = c_content.lower()
        c_tokens = set(extract_content_tokens(c_content + " " + c.get("chapter_title", "") + " " + c.get("section_title", "")))

        # 1. TF-IDF Score
        tf_score = tfidf_scores[idx] if idx < len(tfidf_scores) else 0.0

        # 2. Token Overlap Score (prioritizing subject tokens)
        token_overlap = len(set(tokens_for_scoring).intersection(c_tokens)) if tokens_for_scoring else 0
        overlap_score = token_overlap / max(1, len(tokens_for_scoring)) if tokens_for_scoring else 0.0

        # 3. Exact Phrase Match Boost
        phrase_boost = 0.0
        if len(tokens_for_scoring) >= 2:
            for n in range(2, min(4, len(tokens_for_scoring) + 1)):
                for i in range(len(tokens_for_scoring) - n + 1):
                    subphrase = " ".join(tokens_for_scoring[i:i+n])
                    if subphrase in c_lower:
                        phrase_boost += 0.40 * n

        # 4. Innovation 2 Concept Graph Boost
        c_id = c.get("id", "")
        cg_boost = chunk_boosts.get(c_id, 0.0)

        # 5. Source-type intent boost if query mentions video, lecture, slide, etc.
        source_boost = 0.0
        st = c.get("source_type", "pdf")
        if any(w in q_lower for w in ["video", "lecture", "transcript", "timestamp"]) and st == "video":
            source_boost = 0.25
        elif any(w in q_lower for w in ["slide", "slides", "presentation", "powerpoint", "pptx"]) and st == "presentation":
            source_boost = 0.20
        elif any(w in q_lower for w in ["book", "textbook", "page", "pdf"]) and st == "pdf":
            source_boost = 0.10

        # Composite relevance score
        final_score = (0.35 * tf_score) + (0.35 * overlap_score) + (0.15 * min(1.0, phrase_boost)) + (0.15 * cg_boost) + source_boost

        scored_chunks.append({
            **c,
            "score": float(final_score),
            "tf_score": float(tf_score),
            "overlap_score": float(overlap_score),
            "matched_terms_count": token_overlap
        })

    # Sort descending by final score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    
    # Filter out completely irrelevant chunks (score < 0.04)
    filtered = [c for c in scored_chunks if c["score"] >= 0.04]
    return (filtered[:top_k] if filtered else scored_chunks[:top_k]), related_concepts

def validate_claims_against_evidence(
    claims: List[str], 
    evidence_chunks: List[Dict[str, Any]],
    subject_tokens: List[str]
) -> Tuple[List[Dict[str, Any]], float, List[str]]:
    """
    Performs claim-level factual verification against retrieved multimodal evidence.
    Returns:
    - validated_claims: list of {claim, is_supported, evidence_snippet, citation_index}
    - support_ratio: float between 0.0 and 1.0
    - unsupported_claims: list of unsupported claim strings
    """
    if not claims or not evidence_chunks:
        return [], 0.0, claims or []

    validated_claims = []
    unsupported_claims = []

    # Combined evidence corpus
    evidence_items = []
    for idx, chunk in enumerate(evidence_chunks):
        c_text = chunk.get("content", "")
        c_tokens = set(extract_content_tokens(c_text))
        evidence_items.append({
            "index": idx,
            "chunk": chunk,
            "text": c_text,
            "tokens": c_tokens,
            "lower": c_text.lower()
        })

    for claim in claims:
        claim_clean = claim.strip()
        claim_lower = claim_clean.lower()
        claim_tokens = extract_content_tokens(claim_clean)
        if not claim_tokens:
            continue

        best_support_score = 0.0
        best_evidence_idx = None
        best_snippet = None

        for ev in evidence_items:
            # 1. Exact match / containment
            if claim_lower in ev["lower"]:
                best_support_score = 1.0
                best_evidence_idx = ev["index"]
                best_snippet = ev["text"][:220]
                break

            # 2. Contiguous phrase containment
            if len(claim_tokens) >= 2:
                for n in range(min(5, len(claim_tokens)), 1, -1):
                    for i in range(len(claim_tokens) - n + 1):
                        subp = " ".join(claim_tokens[i:i+n])
                        if subp in ev["lower"]:
                            best_support_score = max(best_support_score, 0.6 + (0.08 * n))

            # 3. Key entity & token overlap
            overlap = len(set(claim_tokens).intersection(ev["tokens"]))
            overlap_ratio = overlap / max(1, len(claim_tokens))
            
            score = max(best_support_score, overlap_ratio)
            if score > best_support_score:
                best_support_score = score
                best_evidence_idx = ev["index"]
                best_snippet = ev["text"][:220]

        # A claim is supported if key terms are sufficiently grounded in the evidence
        is_supported = best_support_score >= 0.35 and best_evidence_idx is not None

        val_obj = {
            "claim": claim,
            "is_supported": is_supported,
            "evidence_snippet": best_snippet if is_supported else None,
            "citation_index": best_evidence_idx if is_supported else None
        }
        validated_claims.append(val_obj)

        if not is_supported:
            unsupported_claims.append(claim)

    supported_count = sum(1 for c in validated_claims if c["is_supported"])
    total_count = len(validated_claims)
    support_ratio = (supported_count / total_count) if total_count > 0 else 0.0

    return validated_claims, support_ratio, unsupported_claims

def build_accurate_citations(
    chunks: List[Dict[str, Any]], 
    supported_citation_indices: Optional[Set[int]] = None
) -> List[Dict[str, Any]]:
    """
    Constructs accurate, dynamic citations referencing real stored content units.
    Never invents page numbers, slide numbers, timestamps, filenames, or links.
    """
    citations = []
    seen_locations = set()

    for idx, c in enumerate(chunks):
        if supported_citation_indices is not None and idx not in supported_citation_indices:
            continue

        s_type = c.get("source_type", "pdf")
        page_num = c.get("page") if s_type == "pdf" else None
        slide_num = c.get("slide_number") or (c.get("page") if s_type == "presentation" else None)
        timestamp_str = c.get("timestamp_str") if s_type == "video" else None

        loc_key = f"{c.get('filename')}_{s_type}_{page_num}_{slide_num}_{timestamp_str}"
        if loc_key in seen_locations:
            continue
        seen_locations.add(loc_key)

        # Truncate clean excerpt
        raw_excerpt = c.get("content", "").strip().replace("\n", " ")
        excerpt = (raw_excerpt[:200] + "...") if len(raw_excerpt) > 200 else raw_excerpt

        citations.append({
            "id": c.get("id"),
            "filename": c.get("filename") or "Course Material",
            "chapter": c.get("chapter_title", "Course Chapter"),
            "section": c.get("section_title", "Course Section"),
            "page": page_num,
            "slide": slide_num,
            "timestamp": timestamp_str,
            "source_type": s_type,
            "excerpt": excerpt,
            "media_url": c.get("media_path"),
            "relevance_score": round(c.get("score", 0.0), 3)
        })

    return citations

def synthesize_dynamic_grounded_answer(
    chunks: List[Dict[str, Any]], 
    query: str, 
    subject_tokens: List[str]
) -> Tuple[str, List[str]]:
    """
    Deterministically synthesizes an evidence-grounded answer directly from the top retrieved chunks.
    Extracts ONLY sentences that genuinely address the query's subject tokens.
    Never returns arbitrary unrelated fallback passages.
    """
    if not chunks or not subject_tokens:
        return "", []

    extracted_claims = []
    structured_sections = []
    top_score = chunks[0].get("score", 1.0) if chunks else 1.0

    for idx, chunk in enumerate(chunks[:4]):
        # Only take chunks that have meaningful relevance to the query
        if chunk.get("score", 0) < max(0.06, top_score * 0.40):
            continue

        content = chunk.get("content", "").strip()
        ch_title = chunk.get("chapter_title", "")
        sec_title = chunk.get("section_title", "")
        s_type = chunk.get("source_type", "pdf")

        # Source location descriptor
        if s_type == "pdf":
            loc_label = f"Page {chunk.get('page', 1)}"
        elif s_type == "presentation":
            loc_label = f"Slide {chunk.get('slide_number') or chunk.get('page', 1)}"
        elif s_type == "video":
            loc_label = f"Timestamp {chunk.get('timestamp_str', '00:00')}"
        else:
            loc_label = "Source"

        # Split content into meaningful sentences
        sentences = split_into_sentences(content)
        relevant_sentences = []
        for s in sentences:
            s_tokens = set(extract_content_tokens(s))
            if set(subject_tokens).intersection(s_tokens):
                relevant_sentences.append(s)
                extracted_claims.append(s)

        if relevant_sentences:
            sec_text = " ".join(relevant_sentences)
            structured_sections.append(f"According to {ch_title} ({loc_label}):\n{sec_text}")

    if not structured_sections or not extracted_claims:
        # No relevant sentences found that address the subject tokens
        return "", []

    full_answer = "\n\n".join(structured_sections)
    return full_answer, extracted_claims

def generate_outside_knowledge_answer(query: str) -> str:
    """
    Generates general knowledge answer when explicitly requested by user.
    Clearly demarcated to avoid implying it came from course materials.
    """
    if GEMINI_API_KEY:
        try:
            client = get_gemini_client()
            if not client:
                raise ValueError("Gemini client unavailable")
            prompt = f"""You are a helpful academic AI assistant providing outside general knowledge.
Answer the following student question accurately using broad, established academic knowledge.
Do not fabricate course references or cite specific page numbers.

Question: {query}
"""
            for model_candidate in FAST_GEMINI_MODELS:
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=prompt
                    )
                    return response.text.strip()
                except Exception:
                    continue
        except Exception as e:
            print(f"Gemini outside knowledge generation note: {e}")

    # Deterministic academic explanation fallback for outside knowledge
    return (
        f"General Knowledge Overview for '{query}':\n"
        f"This subject encompasses general theoretical concepts not contained within the uploaded course materials. "
        f"In standard computer science and engineering literature, this topic is analyzed in terms of its core definitions, "
        f"operating mechanisms, and practical applications in computing systems."
    )

def answer_textbook_query(
    chunks: List[Dict[str, Any]], 
    query: str, 
    language: str = "en",
    course_id: Optional[str] = None,
    enable_outside_knowledge: bool = False,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Innovation 3 Master Pipeline:
    1. Multimodal Evidence Retrieval & Course Isolation
    2. Concept Graph Enrichment (Innovation 2 Synergy)
    3. Sufficiency & Anti-Hallucination Evaluation
    4. Candidate Answer Synthesis (Gemini / Deterministic)
    5. Claim-Level Evidence Validation
    6. Evidence Status Determination (fully_grounded / partially_grounded / unsupported / outside_knowledge)
    7. Accurate Citations Construction (with verified provenance)
    8. Outside Knowledge Support (when explicitly enabled)
    """
    query_str = query.strip()
    
    # Bilingual retrieval query alignment using Google Gemini:
    # If the student's question contains Tamil or mixed Tamil-English, translate to English
    # so TF-IDF and keyword retrieval accurately locate original course excerpts.
    retrieval_query = query_str
    if is_tamil(query_str):
        translated_en_query = translate_text(query_str, target_lang="en", source_lang="ta")
        concept_hint = normalize_tamil_to_concept(query_str)
        if translated_en_query and translated_en_query.strip() and translated_en_query.strip() != query_str:
            retrieval_query = f"{translated_en_query.strip()} {concept_hint}".strip()
        elif concept_hint:
            retrieval_query = f"{query_str} {concept_hint}".strip()

    query_tokens = extract_content_tokens(retrieval_query)
    subject_tokens = extract_subject_tokens(retrieval_query)

    # 1. Multimodal retrieval
    top_chunks, related_concepts = retrieve_relevant_chunks(
        chunks=chunks, 
        query=retrieval_query, 
        course_id=course_id, 
        top_k=5
    )

    # If course is completely empty (no chunks at all)
    if not chunks and not top_chunks:
        refusal_en = "I couldn't find sufficient information about this question in your uploaded course material."
        if enable_outside_knowledge:
            outside_text = generate_outside_knowledge_answer(query_str)
            full_ans = (
                f"{refusal_en}\n\n"
                f"[Outside Knowledge (General AI Knowledge - Not from course materials)]\n"
                f"{outside_text}"
            )
            if language in ["ta", "tamil"]:
                full_ans = translate_text(full_ans, "ta")
            return {
                "query": query_str,
                "answer": full_ans,
                "evidence_status": "outside_knowledge",
                "is_grounded": False,
                "confidence": 0.5,
                "citations": [],
                "validated_claims": [],
                "unsupported_claims": [query_str],
                "related_concepts": [],
                "outside_knowledge_used": True,
                "outside_knowledge_content": outside_text,
                "course_id": course_id,
                "language": language
            }
        
        refusal = translate_text(refusal_en, "ta") if language in ["ta", "tamil"] else refusal_en
        return {
            "query": query_str,
            "answer": refusal,
            "evidence_status": "unsupported",
            "is_grounded": False,
            "confidence": 0.0,
            "citations": [],
            "validated_claims": [],
            "unsupported_claims": [query_str],
            "related_concepts": [],
            "outside_knowledge_used": False,
            "course_id": course_id,
            "language": language
        }

    # 2. Sufficiency Check
    max_score = top_chunks[0]["score"] if top_chunks else 0.0
    matched_term_count = top_chunks[0].get("matched_terms_count", 0) if top_chunks else 0
    query_coverage = (matched_term_count / max(1, len(subject_tokens))) if subject_tokens else 0.0

    # Extract domain-specific query tokens in top chunks
    subject_overlap_count = 0
    max_chunk_subject_overlap = 0
    if subject_tokens and top_chunks:
        all_top_tokens = set()
        for tc in top_chunks[:3]:
            chunk_tokens = set(extract_content_tokens(tc.get("content", "") + " " + tc.get("chapter_title", "") + " " + tc.get("section_title", "")))
            all_top_tokens.update(chunk_tokens)
            c_overlap = len(set(subject_tokens).intersection(chunk_tokens))
            if c_overlap > max_chunk_subject_overlap:
                max_chunk_subject_overlap = c_overlap
        subject_overlap_count = len(set(subject_tokens).intersection(all_top_tokens))

    # Determine if question is unsupported by the retrieved material:
    # 1. The query has no identifiable subject tokens (e.g. "Explain a topic that is not covered in my uploaded materials")
    # 2. Or the core subject tokens have 0 presence in the retrieved chunks
    # 3. Or for multi-token queries, no individual chunk contains any of the subject tokens
    # 4. Or retrieval relevance is below minimum grounding threshold
    is_insufficient = (
        (not subject_tokens) or
        (subject_overlap_count == 0) or
        (len(subject_tokens) >= 2 and max_chunk_subject_overlap < 1) or
        (len(subject_tokens) >= 3 and max_chunk_subject_overlap < 2 and max_score < 0.20) or
        (max_score < 0.08 and query_coverage < 0.25)
    )

    if is_insufficient:
        refusal_en = "I couldn't find sufficient information about this question in your uploaded course material."
        
        if enable_outside_knowledge:
            outside_text = generate_outside_knowledge_answer(query_str)
            full_ans = (
                f"{refusal_en}\n\n"
                f"[Outside Knowledge (General AI Knowledge - Not from course materials)]\n"
                f"{outside_text}"
            )
            if language in ["ta", "tamil"]:
                full_ans = translate_text(full_ans, "ta")
            return {
                "query": query_str,
                "answer": full_ans,
                "evidence_status": "outside_knowledge",
                "is_grounded": False,
                "confidence": 0.5,
                "citations": [],
                "validated_claims": [],
                "unsupported_claims": [query_str],
                "related_concepts": related_concepts,
                "outside_knowledge_used": True,
                "outside_knowledge_content": outside_text,
                "course_id": course_id,
                "language": language
            }

        refusal = translate_text(refusal_en, "ta") if language in ["ta", "tamil"] else refusal_en
        return {
            "query": query_str,
            "answer": refusal,
            "evidence_status": "unsupported",
            "is_grounded": False,
            "confidence": 0.0,
            "citations": [],
            "validated_claims": [],
            "unsupported_claims": [query_str],
            "related_concepts": related_concepts,
            "outside_knowledge_used": False,
            "course_id": course_id,
            "language": language
        }

    # 3. Candidate Answer Generation
    candidate_answer = None
    candidate_claims = []

    # Attempt Gemini API synthesis if key is present
    if is_gemini_available():
        try:
            client = get_gemini_client()
            if not client:
                raise ValueError("Gemini client unavailable")
            
            context_blocks = []
            for i, c in enumerate(top_chunks[:4]):
                st = c.get("source_type", "pdf")
                fname = c.get("filename", "material")
                loc = f"Page {c.get('page', 1)}" if st == "pdf" else (f"Slide {c.get('slide_number') or c.get('page', 1)}" if st == "presentation" else f"Timestamp {c.get('timestamp_str', '00:00')}")
                context_blocks.append(f"[Source {i+1}: {fname} | {c.get('chapter_title', '')} | {loc}]\n{c.get('content', '')}")
            
            context_text = "\n\n".join(context_blocks)
            
            prompt = f"""You are an Evidence-Grounded Course AI Tutor with strict Anti-Hallucination rules.
Answer the following student question using ONLY the facts explicitly stated in the provided course excerpts.

Rules:
1. Every factual statement in your answer MUST be directly supported by the provided course excerpts.
2. If the excerpts only partially answer the question, state what is known from the source and clearly mention what is missing.
3. If the excerpts do not contain the answer, respond with: 'I couldn't find sufficient information about this question in your uploaded course material.'
4. Do NOT hallucinate outside facts, numbers, or theories.

Question: {query_str}

Course Material Excerpts:
{context_text}
"""
            llm_text = None
            for model_candidate in FAST_GEMINI_MODELS:
                try:
                    response = client.models.generate_content(
                        model=model_candidate,
                        contents=prompt
                    )
                    llm_text = response.text.strip()
                    if llm_text:
                        break
                except Exception:
                    continue
                    
            if llm_text:
                if "I couldn't find sufficient information" in llm_text and len(llm_text) < 120:
                    candidate_answer = llm_text
                    candidate_claims = []
                else:
                    candidate_answer = llm_text
                    candidate_claims = split_into_sentences(llm_text)
        except Exception as e:
            print(f"Gemini grounded generation fallback: {e}")

    # Deterministic synthesis if Gemini is not available or failed
    if not candidate_answer:
        candidate_answer, candidate_claims = synthesize_dynamic_grounded_answer(top_chunks, query_str, subject_tokens)

    # If no candidate answer could be constructed from relevant sentences
    if not candidate_answer or candidate_answer.strip() == "" or "I couldn't find sufficient information" in candidate_answer:
        refusal_en = "I couldn't find sufficient information about this question in your uploaded course material."
        if enable_outside_knowledge:
            outside_text = generate_outside_knowledge_answer(query_str)
            full_ans = (
                f"{refusal_en}\n\n"
                f"[Outside Knowledge (General AI Knowledge - Not from course materials)]\n"
                f"{outside_text}"
            )
            if language in ["ta", "tamil"]:
                full_ans = translate_text(full_ans, "ta")
            return {
                "query": query_str,
                "answer": full_ans,
                "evidence_status": "outside_knowledge",
                "is_grounded": False,
                "confidence": 0.5,
                "citations": [],
                "validated_claims": [],
                "unsupported_claims": [query_str],
                "related_concepts": related_concepts,
                "outside_knowledge_used": True,
                "outside_knowledge_content": outside_text,
                "course_id": course_id,
                "language": language
            }
        
        refusal = translate_text(refusal_en, "ta") if language in ["ta", "tamil"] else refusal_en
        return {
            "query": query_str,
            "answer": refusal,
            "evidence_status": "unsupported",
            "is_grounded": False,
            "confidence": 0.0,
            "citations": [],
            "validated_claims": [],
            "unsupported_claims": [query_str],
            "related_concepts": related_concepts,
            "outside_knowledge_used": False,
            "course_id": course_id,
            "language": language
        }

    # Check topical alignment: Did the answer address the actual subject tokens?
    answer_tokens = set(extract_content_tokens(candidate_answer))
    if subject_tokens:
        subject_in_answer = len(set(subject_tokens).intersection(answer_tokens))
        subject_coverage_ratio = subject_in_answer / len(subject_tokens)
    else:
        subject_coverage_ratio = 0.0

    if subject_tokens and subject_coverage_ratio == 0.0:
        # Off-topic response that does not answer the user's actual question
        refusal_en = "I couldn't find sufficient information about this question in your uploaded course material."
        if enable_outside_knowledge:
            outside_text = generate_outside_knowledge_answer(query_str)
            full_ans = (
                f"{refusal_en}\n\n"
                f"[Outside Knowledge (General AI Knowledge - Not from course materials)]\n"
                f"{outside_text}"
            )
            if language in ["ta", "tamil"]:
                full_ans = translate_text(full_ans, "ta")
            return {
                "query": query_str,
                "answer": full_ans,
                "evidence_status": "outside_knowledge",
                "is_grounded": False,
                "confidence": 0.5,
                "citations": [],
                "validated_claims": [],
                "unsupported_claims": [query_str],
                "related_concepts": related_concepts,
                "outside_knowledge_used": True,
                "outside_knowledge_content": outside_text,
                "course_id": course_id,
                "language": language
            }

        refusal = translate_text(refusal_en, "ta") if language in ["ta", "tamil"] else refusal_en
        return {
            "query": query_str,
            "answer": refusal,
            "evidence_status": "unsupported",
            "is_grounded": False,
            "confidence": 0.0,
            "citations": [],
            "validated_claims": [],
            "unsupported_claims": [query_str],
            "related_concepts": related_concepts,
            "outside_knowledge_used": False,
            "course_id": course_id,
            "language": language
        }

    # 4. Claim-Level Evidence Validation
    validated_claims, support_ratio, unsupported_claims = validate_claims_against_evidence(
        claims=candidate_claims,
        evidence_chunks=top_chunks[:4],
        subject_tokens=subject_tokens
    )

    # 5. Evidence Status Determination
    supported_indices = set()
    for vc in validated_claims:
        if vc["is_supported"] and vc["citation_index"] is not None:
            supported_indices.add(vc["citation_index"])

    if not validated_claims or support_ratio < 0.20 or len(supported_indices) == 0:
        # Unsupported
        evidence_status = "unsupported"
        is_grounded = False
        final_answer = "I couldn't find sufficient information about this question in your uploaded course material."
        citations = []
        
        if enable_outside_knowledge:
            outside_text = generate_outside_knowledge_answer(query_str)
            final_answer = (
                f"{final_answer}\n\n"
                f"[Outside Knowledge (General AI Knowledge - Not from course materials)]\n"
                f"{outside_text}"
            )
            evidence_status = "outside_knowledge"
            outside_knowledge_used = True
        else:
            outside_knowledge_used = False
            
    elif support_ratio >= 0.75 and subject_coverage_ratio >= 0.50:
        # Fully Grounded
        evidence_status = "fully_grounded"
        is_grounded = True
        final_answer = candidate_answer
        citations = build_accurate_citations(top_chunks[:4], supported_indices)
        outside_knowledge_used = False
        
    else:
        # Partially Grounded (Some claims supported, but available evidence does not support the complete answer)
        evidence_status = "partially_grounded"
        is_grounded = True
        
        # Keep verified supported statements
        supported_claim_texts = [vc["claim"] for vc in validated_claims if vc["is_supported"]]
        base_grounded = " ".join(supported_claim_texts) if supported_claim_texts else candidate_answer
        
        unsupported_note = (
            f"\n\nNote: The uploaded course material covers the above details, but does not contain sufficient information to verify other aspects of your question."
        )
        
        if enable_outside_knowledge:
            outside_text = generate_outside_knowledge_answer(query_str)
            final_answer = (
                f"{base_grounded}{unsupported_note}\n\n"
                f"[Outside Knowledge (General AI Knowledge - Not from course materials)]\n"
                f"{outside_text}"
            )
            outside_knowledge_used = True
        else:
            final_answer = f"{base_grounded}{unsupported_note}"
            outside_knowledge_used = False

        citations = build_accurate_citations(top_chunks[:4], supported_indices)

    # 6. Tamil translation if requested
    if language in ["ta", "tamil"]:
        final_answer = translate_text(final_answer, "ta")

    return {
        "query": query_str,
        "answer": final_answer,
        "evidence_status": evidence_status,
        "is_grounded": is_grounded,
        "confidence": round(min(0.99, max_score * 0.5 + support_ratio * 0.5), 2) if is_grounded else 0.0,
        "citations": citations,
        "validated_claims": validated_claims,
        "unsupported_claims": unsupported_claims,
        "related_concepts": related_concepts,
        "outside_knowledge_used": outside_knowledge_used,
        "outside_knowledge_content": generate_outside_knowledge_answer(query_str) if outside_knowledge_used else None,
        "course_id": course_id,
        "language": language
    }
        "outside_knowledge_used": outside_knowledge_used,
        "outside_knowledge_content": generate_outside_knowledge_answer(query_str) if outside_knowledge_used else None,
        "course_id": course_id,
        "language": language
    }
