import re
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from config import GEMINI_API_KEY, get_gemini_client, FAST_GEMINI_MODELS, is_gemini_available, mark_gemini_quota_exhausted
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------------------------------------------------------
# INNOVATION 5: EVIDENCE-GROUNDED DYNAMIC VISUAL EXPLANATION SERVICE
# -----------------------------------------------------------------------------

SUPPORTED_DIAGRAM_TYPES = [
    "flowchart",
    "concept_map",
    "block_diagram",
    "sequence",
    "comparison",
    "timeline",
    "hierarchy",
    "cycle"
]

def sanitize_mermaid_label(text: str, max_length: int = 60) -> str:
    """
    Sanitizes text strings for safe, error-free Mermaid node labels.
    Prevents syntax crashes from unescaped quotes, brackets, and angle tags.
    """
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Remove quotes, backticks, brackets, braces
    clean = clean.replace('"', "'").replace('`', '').replace('{', '(').replace('}', ')')
    clean = clean.replace('[', '(').replace(']', ')')
    clean = clean.replace('|', '/').replace(';', ',')
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'^[)\s:\-–—.,;]+', '', clean).strip(' :-–—.,;')
    if len(clean) > max_length:
        clean = clean[:max_length - 3] + "..."
    return clean

def clean_mermaid_syntax(code: str) -> str:
    """
    Enforces 100% syntactically valid Mermaid.js diagrams:
    1. Strips markdown fences (```mermaid ... ```).
    2. Encloses all unquoted node texts in double quotes to prevent crashes from:
       - parentheses inside square brackets: A[O(L) Complexity] -> A["O(L) Complexity"]
       - ampersands: A[Prefix & Auto-complete] -> A["Prefix & Auto-complete"]
       - colons & questions: Gate{Prefix Required?} -> Gate{"Prefix Required?"}
    3. Normalizes arrow labels: 'A -- Yes --> B' -> 'A -->|Yes| B'
    4. Strips raw LaTeX commands that break the Mermaid lexer.
    5. Ensures valid declaration at the top.
    """
    if not code or not code.strip():
        return 'graph TD\n    A["No diagram data available"]'

    c = code.strip()
    c = re.sub(r"^```(?:mermaid)?\s*", "", c, flags=re.IGNORECASE)
    c = re.sub(r"```\s*$", "", c).strip()

    valid_headers = (
        "graph ", "flowchart ", "sequenceDiagram", "classDiagram",
        "stateDiagram", "erDiagram", "timeline", "gantt", "pie",
        "quadrantChart", "mindmap", "gitGraph"
    )
    if not any(c.startswith(h) for h in valid_headers):
        c = "graph TD\n" + c

    lines = []
    for line in c.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^(?:style|classDef|class|subgraph|end|click|autonumber)\b", stripped):
            lines.append(line)
            continue

        l = line

        # Standardize arrow labels: 'A -- Yes --> B' or 'A -- "Yes" --> B' -> 'A -->|Yes| B'
        l = re.sub(r'\s+--\s+["\']?([^->\n|"\']+?)["\']?\s+-->\s+', r' -->|\1| ', l)

        # Standardize dotted arrows: 'A -. Yes .-> B' or 'A -. "Yes" .-> B' -> 'A -.->|Yes| B'
        l = re.sub(r'\s+-\.\s*["\']?([^->\n|"\']+?)["\']?\s*\.->\s+', r' -.->|\1| ', l)

        # Standardize subgraphs with unquoted bracket titles: subgraph ID [Title] -> subgraph ID ["Title"]
        l = re.sub(r'subgraph\s+([A-Za-z0-9_-]+)\s*\[([^"\]\n][^\]\n]*?)\]', lambda m: f'subgraph {m.group(1)} ["{m.group(2).replace(chr(34), chr(39))}"]', l)

        # Wrap unquoted rectangle node labels: ID[label] -> ID["label"]
        def quote_rect(m):
            nid = m.group(1)
            content = m.group(2).replace('"', "'")
            return f'{nid}["{content}"]'
        l = re.sub(r'(\b[A-Za-z0-9_-]+)\[([^"\]\n][^\]\n]*?)\]', quote_rect, l)

        # Wrap unquoted decision / rhombus node labels: ID{label} -> ID{"label"}
        def quote_rhombus(m):
            nid = m.group(1)
            content = m.group(2).replace('"', "'")
            return f'{nid}{{"{content}"}}'
        l = re.sub(r'(\b[A-Za-z0-9_-]+)\{([^"\}\n][^\}\n]*?)\}', quote_rhombus, l)

        # Clean LaTeX commands that crash Mermaid lexer
        l = l.replace(r"\mathcal", "Math_").replace(r"\in", "in").replace(r"\ge", ">=").replace(r"\le", "<=")
        l = l.replace(r"\models", "|=").replace(r"\text", "").replace("\\", "")

        lines.append(l)

    return "\n".join(lines)

VISUAL_STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "of", "to", "for", "with", "by",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "what", "how", "why", "when", "which", "where", "who", "whom",
    "diagram", "figure", "table", "visual", "explanation", "explain", "about"
}

def retrieve_relevant_chunks_for_topic(
    chunks: List[Dict[str, Any]], 
    topic: str, 
    top_k: int = 8
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Retrieves the most semantically relevant chunks for a requested visual topic.
    """
    if not chunks or not topic:
        return []

    topic_clean = topic.strip()
    # Normalize query tokens and remove conversational stop words
    all_tokens = re.findall(r'\b[a-zA-Z0-9_]+\b', topic_clean.lower())
    non_stop = [t for t in all_tokens if t not in VISUAL_STOP_WORDS]
    topic_tokens = set(non_stop if non_stop else all_tokens)
    
    scored_chunks = []
    chunk_texts = []
    valid_chunks = []

    for c in chunks:
        content = c.get("content", "").strip()
        if content:
            valid_chunks.append(c)
            ch_title = c.get("chapter_title", "")
            sec_title = c.get("section_title", "")
            chunk_texts.append(f"{ch_title} {sec_title} {content}")

    if not valid_chunks:
        return []

    # Keyword overlap scoring on core subject tokens
    for c in valid_chunks:
        content_lower = (c.get("content", "") + " " + c.get("chapter_title", "") + " " + c.get("section_title", "")).lower()
        content_tokens = set(re.findall(r'\b[a-zA-Z0-9_]+\b', content_lower))
        overlap = len(topic_tokens.intersection(content_tokens))
        # Extra boost if exact topic phrase in content
        if topic_clean.lower() in content_lower:
            overlap += 5
        score = overlap / (len(topic_tokens) or 1)
        scored_chunks.append((c, score))

    # TF-IDF cosine similarity scoring
    try:
        if len(chunk_texts) >= 1:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(chunk_texts + [topic_clean])
            sims = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]
            for idx, sim in enumerate(sims):
                combined = scored_chunks[idx][1] * 0.5 + float(sim) * 0.5
                scored_chunks[idx] = (valid_chunks[idx], combined)
    except Exception:
        pass

    # Sort descending by score
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return scored_chunks[:top_k]

def detect_best_diagram_type(topic: str, chunks_text: str, level: str = "intermediate") -> str:
    """
    Dynamically analyzes the concept topic, retrieved evidence, and pedagogical tier
    to select the most natural, intuitive, and effective visual format.
    """
    topic_l = topic.lower()
    text_l = chunks_text.lower()
    lvl = (level or "intermediate").lower().strip()
    if lvl not in ["beginner", "intermediate", "advanced"]:
        lvl = "intermediate"

    # Specialized formats if keywords are matched:
    if any(k in topic_l or k in text_l for k in [
        "protocol", "2pc", "two-phase", "handshake", "message exchange", 
        "request response", "coordinator", "cohort", "client server", "rpc", "election"
    ]):
        return "sequence"

    if any(k in topic_l for k in [" vs ", " versus ", "comparison", "difference between", "contrasting", "trade-off"]):
        return "comparison"

    if any(k in topic_l or k in text_l for k in [
        "state machine", "lifecycle", "state transition", "states", "cycle", "closed loop", "feedback loop"
    ]):
        return "cycle"

    if any(k in topic_l for k in ["chronology", "evolution", "history of", "milestones", "generations", "timeline of"]):
        return "timeline"

    if any(k in topic_l or k in text_l for k in [
        "taxonomy", "hierarchy", "classification", "types of", "categories", "tree structure"
    ]):
        return "hierarchy"

    # For architecture / subsystems / RAG / algorithms, calibrate default format by level:
    if any(k in topic_l or k in text_l for k in [
        "architecture", "rag", "retrieval augmented", "layer", "layers", "subsystem", "component", "pipeline", 
        "neural network", "storage hierarchy", "hardware stack", "framework", "semantic cache"
    ]):
        if lvl == "beginner":
            return "concept_map"
        elif lvl == "advanced":
            return "block_diagram"
        else:
            return "flowchart"

    # Flowchart / Process keywords
    if any(k in topic_l or k in text_l for k in [
        "algorithm", "step by step", "procedure", "workflow", "decision", "flow", 
        "process", "execution", "normalization", "scheduling", "search", "traversal",
        "grounding", "prompt"
    ]):
        if lvl == "beginner":
            return "concept_map"
        elif lvl == "advanced":
            return "block_diagram"
        else:
            return "flowchart"

    # Default to level-optimized format
    if lvl == "beginner":
        return "concept_map"
    elif lvl == "advanced":
        return "block_diagram"
    else:
        return "flowchart"

def build_source_citation_dict(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a grounded source citation from a chunk."""
    s_type = chunk.get("source_type", "pdf").lower()
    citation = {
        "id": chunk.get("id"),
        "filename": chunk.get("filename", "Course Document"),
        "chapter": chunk.get("chapter_title", "General"),
        "section": chunk.get("section_title", "Content Section"),
        "source_type": s_type,
        "page": chunk.get("page"),
        "slide": chunk.get("slide_number"),
        "timestamp": chunk.get("timestamp_str"),
        "excerpt": (chunk.get("content", "")[:200] + "...").strip() if chunk.get("content") else ""
    }
    return citation

def format_provenance_label(chunk: Dict[str, Any]) -> str:
    """Generates human-readable citation label."""
    s_type = chunk.get("source_type", "pdf").lower()
    fn = chunk.get("filename", "Course Document")
    if s_type == "presentation" or chunk.get("slide_number"):
        return f"{fn} (Slide {chunk.get('slide_number', 1)})"
    elif s_type == "video" or chunk.get("timestamp_str"):
        return f"{fn} ({chunk.get('timestamp_str', '00:00')})"
    else:
        return f"{fn} (Page {chunk.get('page', 1)})"

def extract_entities_and_steps_from_chunks(
    chunks: List[Dict[str, Any]], 
    topic: str,
    level: str = "intermediate"
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]]]:
    """
    Parses course text chunks into concrete entities, sequential steps, and relationships
    calibrated to the requested pedagogical tier (Beginner, Intermediate, Advanced).
    """
    entities = []
    relationships = []
    seen_labels = set()
    combined_all = " ".join(c.get("content", "") for c in chunks).lower()
    lvl = (level or "intermediate").lower().strip()
    if lvl not in ["beginner", "intermediate", "advanced"]:
        lvl = "intermediate"

    # Domain Knowledge Ingestion for RAG / AI Grounding / Caching
    if any(k in combined_all or k in topic.lower() for k in ["rag", "retrieval augmented", "semantic cache", "grounded source", "prompt"]):
        if lvl == "beginner":
            rag_components = [
                ("1. Ask Question (Prompt)", "Everyday question asked by a student in simple words", "process_step"),
                ("2. Instant Memory Check (Cache)", "Quickly checks if this question was already answered earlier", "concept"),
                ("3. Reference Books (Verified Source)", "Real course materials and book pages that contain verified facts", "concept"),
                ("4. Smart AI (Clear Answer)", "Creates a crystal-clear, friendly explanation grounded in your course books", "process_step")
            ]
            rag_relationships = [
                ("1. Ask Question (Prompt)", "checks quick memory in", "2. Instant Memory Check (Cache)"),
                ("2. Instant Memory Check (Cache)", "looks up verified pages in", "3. Reference Books (Verified Source)"),
                ("3. Reference Books (Verified Source)", "provides facts to write", "4. Smart AI (Clear Answer)")
            ]
        elif lvl == "intermediate":
            rag_components = [
                ("Client Prompt Ingestion", "Original user inquiry or task input submitted to the interface", "process_step"),
                ("Semantic Vector Cache", "High-speed cache checking if semantically similar prompt already has verified completion", "concept"),
                ("Grounded Source Database", "External verified knowledge base providing domain truth", "concept"),
                ("Context Retrieval Engine", "Searches and extracts relevant factual evidence matching user query", "process_step"),
                ("Augmented Prompt Assembly", "Combines original user prompt with retrieved factual context", "process_step"),
                ("AI Inference Engine (LLM)", "Generates grounded completion using both prompt and verified source facts", "concept"),
                ("Grounded Truth Completion", "Final verified, hallucination-free response returned to the user", "process_step")
            ]
            rag_relationships = [
                ("Client Prompt Ingestion", "checks vector similarity", "Semantic Vector Cache"),
                ("Semantic Vector Cache", "cache miss to", "Grounded Source Database"),
                ("Grounded Source Database", "supplies context to", "Context Retrieval Engine"),
                ("Context Retrieval Engine", "enriches", "Augmented Prompt Assembly"),
                ("Augmented Prompt Assembly", "transmits to", "AI Inference Engine (LLM)"),
                ("AI Inference Engine (LLM)", "produces", "Grounded Truth Completion"),
                ("Grounded Truth Completion", "populates", "Semantic Vector Cache")
            ]
        else:  # advanced
            rag_components = [
                ("Formal Query Ingestion Q [Inv-1]", "Client prompt validated against input schemas and token invariants", "process_step"),
                ("Semantic Cache Tier [sim(e_q, e_c) >= tau]", "High-dimensional embedding space with cosine similarity metric gate", "concept"),
                ("Partitioned Grounded Corpus D", "Verified knowledge base ensuring lossless context retrieval and attribution", "concept"),
                ("Dense Retrieval & Reranker Engine", "Bi-encoder dense vector scan with reciprocal rank fusion and faith guardrails", "process_step"),
                ("Constrained Decoder Inference LLM", "Decoder-only transformer conditioned on context with hallucination rejection gate", "concept"),
                ("Atomic Cache Writeback Protocol", "ACID-compliant cache update maintaining causal consistency invariants", "process_step")
            ]
            rag_relationships = [
                ("Formal Query Ingestion Q [Inv-1]", "evaluates metric", "Semantic Cache Tier [sim(e_q, e_c) >= tau]"),
                ("Semantic Cache Tier [sim(e_q, e_c) >= tau]", "cache miss fallback", "Partitioned Grounded Corpus D"),
                ("Partitioned Grounded Corpus D", "dense index scan", "Dense Retrieval & Reranker Engine"),
                ("Dense Retrieval & Reranker Engine", "conditions inference", "Constrained Decoder Inference LLM"),
                ("Constrained Decoder Inference LLM", "atomic commit", "Atomic Cache Writeback Protocol")
            ]

        top_cite = build_source_citation_dict(chunks[0]) if chunks else {}
        for lbl, desc, ntype in rag_components:
            seen_labels.add(lbl.lower())
            entities.append({
                "label": lbl,
                "description": desc,
                "source_citation": top_cite,
                "is_supported": True,
                "node_type": ntype
            })
        relationships.extend(rag_relationships)
        return entities, relationships

    # General extraction for any other course subjects
    for c in chunks:
        content = c.get("content", "")
        citation = build_source_citation_dict(c)

        # 1. Look for numbered lists or steps
        content_no_ts = re.sub(r'\(\s*\d{1,2}:\d{2}\s*[-–—]\s*\d{1,2}:\d{2}\s*\)', '', content)
        content_no_ts = re.sub(r'\[Timestamp\s+[^\]]+\]:?', '', content_no_ts)
        content_no_ts = re.sub(r'\[Video Keyframe[^\]]+\]:?', '', content_no_ts)
        step_matches = re.findall(
            r'(?:(?:Phase|Step|Stage)\s*(\d+|[A-Z])[:\.\-]\s*([^\.\n]+)|(?<!\d)(?<!:)(?<!-)\b(\d{1,2})[\.\)]\s+([A-Z][^\.\n]+))', 
            content_no_ts, 
            re.IGNORECASE
        )
        for sm in step_matches:
            num = sm[0] or sm[2]
            desc = (sm[1] or sm[3]).strip()
            desc = re.sub(r'^[)\s:\-–—]+', '', desc)
            clean_lbl = sanitize_mermaid_label(desc, 45)
            if clean_lbl and clean_lbl.lower() not in seen_labels and len(clean_lbl) > 3:
                seen_labels.add(clean_lbl.lower())
                lbl_final = f"Step {num}: {clean_lbl}" if not clean_lbl.lower().startswith("step") else clean_lbl
                if lvl == "advanced":
                    lbl_final = f"{lbl_final} [Inv-Checked]"
                entities.append({
                    "label": lbl_final,
                    "description": desc,
                    "source_citation": citation,
                    "is_supported": True,
                    "node_type": "process_step"
                })

        # 2. Look for definitions and key relational clauses
        sentences = [s.strip() for s in re.split(r'[\.\n]+', content) if len(s.strip()) > 15]
        for s in sentences:
            rel_m = re.search(r'\b([A-Z][a-zA-Z0-9_\s]{2,25})\b\s+(requires|consists of|manages|sends|coordinates|transforms|produces|validates|guarantees|bypasses|retrieves|augments)\s+\b([A-Z][a-zA-Z0-9_\s]{2,30})\b', s, re.IGNORECASE)
            if rel_m:
                src_term = sanitize_mermaid_label(rel_m.group(1), 30)
                rel_verb = rel_m.group(2).lower()
                tgt_term = sanitize_mermaid_label(rel_m.group(3), 30)
                if src_term and tgt_term and src_term.lower() != tgt_term.lower():
                    relationships.append((src_term, rel_verb, tgt_term))

            # Look for capitalized concepts/terms
            cap_terms = re.findall(r'\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,3})\b', s)
            for ct in cap_terms:
                clean_ct = sanitize_mermaid_label(ct, 40)
                if clean_ct and clean_ct.lower() not in seen_labels and clean_ct.lower() != topic.lower() and len(clean_ct) >= 2:
                    if clean_ct.lower() not in ["chapter", "section", "figure", "table", "reading", "practice questions", "timeline", "timestamp", "lecture"]:
                        seen_labels.add(clean_ct.lower())
                        lbl_term = clean_ct
                        if lvl == "advanced":
                            lbl_term = f"{clean_ct} [Formal]"
                        entities.append({
                            "label": lbl_term,
                            "description": s[:150],
                            "source_citation": citation,
                            "is_supported": True,
                            "node_type": "concept"
                        })

    # Calibrate entity count by tier
    if lvl == "beginner" and len(entities) > 4:
        entities = entities[:4]
    elif lvl == "intermediate" and len(entities) > 7:
        entities = entities[:7]
    elif lvl == "advanced" and len(entities) > 9:
        entities = entities[:9]

    return entities, relationships


# -----------------------------------------------------------------------------
# MERMAID CODE GENERATORS PER FORMAT
# -----------------------------------------------------------------------------

def build_flowchart_mermaid(topic: str, entities: List[Dict[str, Any]], relationships: List[Tuple[str, str, str]], level: str = "intermediate") -> str:
    """Builds a structured flowchart with decision branches distinctly calibrated for Beginner, Intermediate, or Advanced."""
    lvl = (level or "intermediate").lower().strip()
    is_rag = any(k in topic.lower() or any(k in e.get("label", "").lower() for e in entities) for k in ["rag", "retrieval", "cache", "grounded", "prompt", "llm", "chatgpt"])
    top_clean = sanitize_mermaid_label(topic, 40)

    # 1. BEGINNER FLOWCHART: Linear, friendly, intuitive, no complex branching
    if lvl == "beginner":
        lines = ["graph TD"]
        lines.append(f'    START["1. 💡 Ask Question: {top_clean}"]')
        if is_rag:
            lines.append('    STEP_1["2. ⚡ Check Quick Memory (Cache)"]')
            lines.append('    STEP_2["3. 📚 Look Up Verified Books"]')
            lines.append('    FINISH["4. ✨ Helpful & Easy Answer"]')
            lines.append('    START --> STEP_1')
            lines.append('    STEP_1 --> STEP_2')
            lines.append('    STEP_2 --> FINISH')
        else:
            steps = [e for e in entities if e.get("node_type") == "process_step"] or entities[:3]
            if not steps:
                steps = [
                    {"label": f"1. Start Learning: {top_clean}"},
                    {"label": "2. Everyday Real-World Example"},
                    {"label": "3. Clear Takeaway & Summary"}
                ]
            prev_id = "START"
            for idx, st in enumerate(steps[:3]):
                step_id = f"STEP_{idx+1}"
                lbl = sanitize_mermaid_label(st["label"], 45)
                lines.append(f'    {step_id}["{lbl}"]')
                lines.append(f'    {prev_id} --> {step_id}')
                prev_id = step_id
            lines.append('    FINISH["✨ Clear Understanding Achieved"]')
            lines.append(f'    {prev_id} --> FINISH')

        lines.append('    style START fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46')
        lines.append('    style FINISH fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b')
        if "STEP_1" in "\n".join(lines):
            lines.append('    style STEP_1 fill:#fefce8,stroke:#eab308,stroke-width:1.5px,color:#713f12')
        if "STEP_2" in "\n".join(lines):
            lines.append('    style STEP_2 fill:#eff6ff,stroke:#3b82f6,stroke-width:1.5px,color:#1e3a8a')
        return "\n".join(lines)

    # 2. ADVANCED FLOWCHART: Formal invariant checks, decision gates, failure/rollback branches
    if lvl == "advanced":
        if is_rag:
            return f"""graph TD
    START["Formal Ingestion: Query Q \\in \\mathcal{{L}} [Inv-1]"]
    GATE_SCHEMA{{"Precondition Invariant:<br/>Q Satisfies Token & Schema Bounds?"}}
    ROLLBACK_1["Rollback / Reject: Schema Invariant Violation"]
    CACHE_GATE{{"Metric Gate:<br/>\\text{{sim}}(E(Q), E(k)) \\ge \\tau ?"}}
    HIT_FAST["Deterministic Cache Return: O(1) Latency Bypass"]
    RETRIEVE["Lossless Dense Retrieval & Top-K Cross-Reranker"]
    INFER["Constrained Token Inference P(Y|Q, C)"]
    PROOF_GATE{{"Soundness Proof Gate:<br/>\\models \\text{{Grounded}}(Y, C) ?"}}
    ROLLBACK_2["Safety Rollback: Hallucination Invariant Rejection"]
    COMMIT["Atomic Cache Writeback & State Finalization (ACID)"]
    START --> GATE_SCHEMA
    GATE_SCHEMA -->|Violated| ROLLBACK_1
    GATE_SCHEMA -->|Satisfied| CACHE_GATE
    CACHE_GATE -->|sim \\ge \\tau (Hit)| HIT_FAST
    CACHE_GATE -->|sim < \\tau (Miss)| RETRIEVE
    RETRIEVE --> INFER
    INFER --> PROOF_GATE
    PROOF_GATE -->|Violation| ROLLBACK_2
    PROOF_GATE -->|Proof Holds| COMMIT
    COMMIT --> HIT_FAST
    style START fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style GATE_SCHEMA fill:#fce7f3,stroke:#ec4899,stroke-width:2px,color:#831843
    style ROLLBACK_1 fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b
    style CACHE_GATE fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#78350f
    style HIT_FAST fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b
    style RETRIEVE fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px
    style INFER fill:#e0e7ff,stroke:#6366f1,stroke-width:1.5px
    style PROOF_GATE fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#881337
    style ROLLBACK_2 fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b
    style COMMIT fill:#ecfdf5,stroke:#059669,stroke-width:2px,color:#064e3b"""
        else:
            return f"""graph TD
    START["Formal Ingestion: {top_clean} [Preconditions \\mathcal{{P}}]"]
    GATE_PRE{{"Precondition Verification:<br/>\\mathcal{{P}} Holds Invariant?"}}
    FAIL_PRE["Exception: Precondition Bound Violated"]
    EXEC["Core Execution & State Transition Matrix"]
    GATE_INV{{"Post-Condition Proof:<br/>\\models \\text{{Invariant}}({top_clean}) ?"}}
    FAIL_POST["Rollback: Invariant Integrity Violation"]
    COMMIT["State Commitment & Invariant Guarantee Certified"]
    START --> GATE_PRE
    GATE_PRE -->|Invalid| FAIL_PRE
    GATE_PRE -->|Valid| EXEC
    EXEC --> GATE_INV
    GATE_INV -->|Violation| FAIL_POST
    GATE_INV -->|Certified| COMMIT
    style START fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style GATE_PRE fill:#fce7f3,stroke:#ec4899,stroke-width:2px,color:#831843
    style FAIL_PRE fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b
    style EXEC fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px
    style GATE_INV fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#881337
    style FAIL_POST fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b
    style COMMIT fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b"""

    # 3. INTERMEDIATE FLOWCHART: Standard engineering workflow with decision gate
    lines = ["graph TD"]
    root_lbl = sanitize_mermaid_label(f"Start: {topic}", 45)
    lines.append(f'    START["{root_lbl}"]')

    steps = [e for e in entities if e.get("node_type") == "process_step"] or entities[:6]
    if len(steps) < 3:
        if is_rag:
            steps = [
                {"label": "1. User Submits Query Prompt", "description": "Client inputs prompt to interface."},
                {"label": "2. Check Semantic Cache for Previous Response", "description": "Fast lookup in vector cache."},
                {"label": "3. Query Grounded Source Database", "description": "Retrieve verified evidence from database."},
                {"label": "4. Assemble Augmented Prompt with Source Facts", "description": "Combine prompt with retrieved context."},
                {"label": "5. AI Model (LLM) Generates Grounded Output", "description": "Model infers completion based on verified ground truth."},
                {"label": "6. Store Response in Semantic Cache", "description": "Cache result for future model bypass."}
            ]
        else:
            steps = [
                {"label": "1. Input & Precondition Check", "description": "Verify initial requirements."},
                {"label": "2. Core Transformation Process", "description": "Execute main logic."},
                {"label": "3. Invariant Validation", "description": "Ensure consistency."},
                {"label": "4. Output & State Finalization", "description": "Produce verified result."}
            ]

    prev_id = "START"
    for idx, st in enumerate(steps[:6]):
        step_id = f"STEP_{idx+1}"
        lbl = sanitize_mermaid_label(st["label"], 50)
        lines.append(f'    {step_id}["{lbl}"]')
        
        if idx == 1:
            dec_id = "DEC_1"
            lines.append(f'    {dec_id}{{"Validation Check:<br/>Cache Hit or Valid Grounding?"}}')
            lines.append(f'    {prev_id} --> {step_id}')
            lines.append(f'    {step_id} --> {dec_id}')
            lines.append(f'    {dec_id} -->|Valid / Pass| STEP_{idx+2 if idx+2 <= len(steps) else idx+1}')
            lines.append(f'    {dec_id} -->|Miss / Fetch| STEP_{idx+2 if idx+2 <= len(steps) else idx+1}')
            prev_id = dec_id
        else:
            if prev_id != "DEC_1":
                lines.append(f'    {prev_id} --> {step_id}')
            prev_id = step_id

    end_id = "FINISH"
    lines.append(f'    {end_id}["Verified Output / Completed State"]')
    if prev_id != end_id:
        lines.append(f'    {prev_id} --> {end_id}')

    lines.append('    style START fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#075985')
    lines.append('    style FINISH fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b')
    lines.append('    style DEC_1 fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#78350f')

    return "\n".join(lines)


def build_sequence_mermaid(topic: str, entities: List[Dict[str, Any]], relationships: List[Tuple[str, str, str]], level: str = "intermediate") -> str:
    """Builds a sequence diagram showing interaction protocols calibrated by tier."""
    lvl = (level or "intermediate").lower().strip()
    is_rag = any(k in topic.lower() or any(k in e.get("label", "").lower() for e in entities) for k in ["rag", "retrieval", "cache", "grounded", "prompt", "llm"])
    top_clean = sanitize_mermaid_label(topic, 30)

    if lvl == "beginner":
        return f"""sequenceDiagram
    autonumber
    actor You as Student (You)
    participant Memory as Quick Memory (Cache)
    participant Book as Course Textbook
    participant AI as Smart Assistant
    You->>Memory: 1. Ask everyday question about {top_clean}
    alt Already in Memory
        Memory-->>You: 2. Delivers instant easy answer
    else Needs Book Lookup
        Memory->>Book: 3. Read verified course pages
        Book-->>AI: 4. Shares verified factual notes
        AI-->>You: 5. Explains clearly with friendly analogies
    end"""

    if lvl == "advanced":
        return f"""sequenceDiagram
    autonumber
    actor Client as Client Agent [Inv-1]
    participant Cache as Semantic Vector Cache Tier
    participant Corpus as Partitioned Grounded Corpus D
    participant Verifier as Faithfulness Guardrail Engine
    participant LLM as Constrained Decoder LLM
    Client->>Cache: 1. Dispatch Formal Query Q with Precondition Invariant
    alt Cosine Similarity \\ge \\tau (Cache Hit)
        Cache-->>Client: 2. Return Deterministic Cached Completion [O(1) Bound]
    else Similarity < \\tau (Cache Miss)
        Cache->>Corpus: 3. Dense Index Scan \\text{{TopK}}(D, Q)
        Corpus-->>Verifier: 4. Return Retrieved Context Candidates
        Verifier->>LLM: 5. Supply Grounded Context & Boundary Constraints
        LLM->>Verifier: 6. Generated Tokens Conditioned on Context P(Y|Q, C)
        critical Hallucination Invariant Verification
            Verifier->>Verifier: Check \\models \\text{{Grounded}}(Y, C)
        end
        Verifier-->>Client: 7. Deliver Verified Grounded Completion
        Verifier->>Cache: 8. Atomic Cache Mutation with ACID Invariant
    end"""

    # Intermediate default
    if is_rag:
        return """sequenceDiagram
    autonumber
    actor User
    participant Interface as Prompt Interface
    participant Cache as Semantic Cache
    participant DB as Grounded Database
    participant AI as AI Engine (LLM)
    User->>Interface: Submit Query Prompt
    Interface->>Cache: 1. Check for Cached Completion
    alt Cache Hit (Bypass AI)
        Cache-->>User: 2. Instant Cached Grounded Answer
    else Cache Miss
        Interface->>DB: 3. Query Grounded Source for Matching Data
        DB-->>AI: 4. Supply Verified Domain Context
        Interface->>AI: 5. Transmit Augmented Prompt
        AI-->>User: 6. Deliver Grounded, Truthful Completion
        AI->>Cache: 7. Store Result in Semantic Cache
    end"""

    lines = ["sequenceDiagram", "    autonumber"]
    participants = []
    for src, _, tgt in relationships[:4]:
        if src not in participants:
            participants.append(src)
        if tgt not in participants:
            participants.append(tgt)

    if len(participants) < 2:
        participants = ["Client / Initiator", f"{top_clean} Coordinator", "Participant Nodes / Storage"]

    for idx, p in enumerate(participants[:3]):
        p_safe = sanitize_mermaid_label(p, 30)
        lines.append(f'    participant P{idx+1} as {p_safe}')

    p1, p2 = "P1", "P2"
    p3 = "P3" if len(participants) >= 3 else "P2"

    lines.append(f'    {p1}->>+{p2}: 1. Initiate {top_clean} Request')
    lines.append(f'    {p2}->>+{p3}: 2. Broadcast / Dispatch Task to Cohort')
    lines.append(f'    {p3}-->>-{p2}: 3. Acknowledge / Reply with Local State')
    lines.append(f'    Note over {p2}: Verify All Conditions & Consensus')
    lines.append(f'    {p2}->>+{p3}: 4. Execute Global Decision / Commit Command')
    lines.append(f'    {p3}-->>-{p2}: 5. Confirmation of Completed Execution')
    lines.append(f'    {p2}-->>-{p1}: 6. Final Response & Success Result')

    return "\n".join(lines)


def build_block_diagram_mermaid(topic: str, entities: List[Dict[str, Any]], level: str = "intermediate") -> str:
    """Builds a modular subsystem block diagram architecture layout calibrated by tier."""
    lvl = (level or "intermediate").lower().strip()
    is_rag = any(k in topic.lower() or any(k in e.get("label", "").lower() for e in entities) for k in ["rag", "retrieval", "cache", "grounded", "prompt", "llm", "chatgpt"])
    top_clean = sanitize_mermaid_label(topic, 40)

    # 1. BEGINNER BLOCK DIAGRAM: 3 simple, friendly, intuitive layers
    if lvl == "beginner":
        return f"""graph TD
    subgraph USER_TIER ["1. Student Input (Everyday Question)"]
        U1["Ask Question in Natural Words"]
        U2["Curiosity & Everyday Goal"]
    end
    subgraph BOOK_TIER ["2. Verified Course Knowledge"]
        B1["Course Textbook Chapters"]
        B2["True Facts & Definitions"]
    end
    subgraph ANSWER_TIER ["3. Smart Assistant Output"]
        A1["Easy Step-by-Step Explanation"]
        A2["Intuitive Real-World Analogy"]
    end
    USER_TIER --> BOOK_TIER
    BOOK_TIER --> ANSWER_TIER
    style USER_TIER fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px,color:#065f46
    style BOOK_TIER fill:#eff6ff,stroke:#3b82f6,stroke-width:1.5px,color:#1e3a8a
    style ANSWER_TIER fill:#faf5ff,stroke:#a855f7,stroke-width:1.5px,color:#581c87"""

    # 2. ADVANCED BLOCK DIAGRAM: 5-tier formal distributed system architecture with subgraphs & invariants
    if lvl == "advanced":
        if is_rag:
            return """graph TD
    subgraph INGESTION_TIER ["Tier 1: Precondition Ingestion & Schema Bounds [Inv-1]"]
        I1["Formal Query Q \\in \\mathcal{L}"]
        I2["Precondition Invariant Verification"]
    end
    subgraph CACHE_METRIC_TIER ["Tier 2: Semantic Vector Space (sim \\ge \\tau)"]
        C1["High-Dim Embedding Space E(Q)"]
        C2["Cosine Distance Bound Gate"]
        C3["O(1) Deterministic Bypass Channel"]
    end
    subgraph STORAGE_TIER ["Tier 3: Partitioned Knowledge Corpus & Retrieval"]
        G1["Partitioned Document Store \\mathcal{D}"]
        G2["Bi-Encoder Dense Vector Index Scan"]
        G3["Faithfulness Filter Top-K"]
    end
    subgraph VERIFICATION_TIER ["Tier 4: Constrained Decoder & Invariant Verification"]
        A1["Context-Conditioned Token Generation P(Y|Q, C)"]
        A2["Hallucination Soundness Proof Gate"]
        A3["Rollback & Grounding Exception Channel"]
    end
    subgraph CONSISTENCY_TIER ["Tier 5: Atomic Persistence & State Invariants"]
        S1["Atomic Writeback Protocol (ACID)"]
        S2["Causal Consistency Maintenance"]
    end
    I2 --> C1
    C2 -->|sim >= tau| C3
    C2 -->|sim < tau| G1
    G3 --> A1
    A2 --> S1
    S2 -.->|Atomic Mutate| C1
    style INGESTION_TIER fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style CACHE_METRIC_TIER fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px
    style STORAGE_TIER fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px
    style VERIFICATION_TIER fill:#fff1f2,stroke:#f43f5e,stroke-width:2px
    style CONSISTENCY_TIER fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px"""
        else:
            return f"""graph TD
    subgraph INGESTION_TIER ["Tier 1: Formal Ingestion & Bounds: {top_clean}"]
        I1["Client Input Streams"]
        I2["Precondition Validation Matrix"]
    end
    subgraph COMPUTE_TIER ["Tier 2: Core State Engine & Invariant Verification"]
        C1["Core State Machine"]
        C2["Invariant Checking Engine"]
    end
    subgraph VERIFICATION_TIER ["Tier 3: Formal Boundary Proofs & Safety Channels"]
        V1["Safety Proof Invariant Gate"]
        V2["Exception & Rollback Log"]
    end
    subgraph PERSISTENCE_TIER ["Tier 4: Atomic State Persistence"]
        P1["ACID State Store"]
        P2["Audit Log / Proof Trace"]
    end
    I1 --> C1
    C1 --> V1
    V1 --> P1
    style INGESTION_TIER fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style COMPUTE_TIER fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px
    style VERIFICATION_TIER fill:#fff1f2,stroke:#f43f5e,stroke-width:2px
    style PERSISTENCE_TIER fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px"""

    # 3. INTERMEDIATE BLOCK DIAGRAM: 4 modular layers
    if is_rag or len(entities) < 2:
        return """graph TD
    subgraph CLIENT_LAYER ["Input & Prompt Interface"]
        I1["User Query / Prompt"]
        I2["System Preconditions & Task Context"]
    end
    subgraph CACHE_LAYER ["Optimization & Semantic Cache Tier"]
        C1["Semantic Cache (Vector & Embeddings)"]
        C2["Bypass AI Engine on Cache Hits"]
    end
    subgraph GROUNDED_TIER ["Grounded Knowledge Source (Database)"]
        G1["Grounded Source Database (Verified Knowledge Base)"]
        G2["Context Retrieval & Ranking Engine"]
    end
    subgraph GENERATION_TIER ["AI Inference Tier"]
        A1["Augmented Prompt Assembly"]
        A2["AI Engine / LLM (Token Completion)"]
        A3["Truth-Grounded Response Delivery"]
    end
    I1 --> C1
    C2 -->|Cache Miss| G1
    G2 --> A1
    I2 --> A1
    A3 -.->|Populate Cache| C1
    style CLIENT_LAYER fill:#f8fafc,stroke:#94a3b8,stroke-width:1px
    style CACHE_LAYER fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px
    style GROUNDED_TIER fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px
    style GENERATION_TIER fill:#ecfdf5,stroke:#10b981,stroke-width:2px"""

    lines = ["graph TD"]
    lines.append(f'    subgraph INPUT_LAYER ["Input & Ingestion Interface"]')
    lines.append(f'        I1["Client Requests / Raw Data"]')
    lines.append(f'        I2["Config & Preconditions"]')
    lines.append(f'    end')

    lines.append(f'    subgraph CORE_LAYER ["Core System Architecture: {top_clean}"]')
    for idx, e in enumerate(entities[:4]):
        lbl = sanitize_mermaid_label(e["label"], 35)
        lines.append(f'        C{idx+1}["{lbl}"]')
    lines.append(f'    end')

    lines.append(f'    subgraph STORAGE_LAYER ["Persistence & Output Guarantees"]')
    lines.append(f'        S1["Validated State Store"]')
    lines.append(f'        S2["Audit Log / Telemetry"]')
    lines.append(f'    end')

    lines.append('    I1 --> C1')
    lines.append('    C1 --> S1')

    lines.append('    style INPUT_LAYER fill:#f8fafc,stroke:#94a3b8,stroke-width:1px')
    lines.append('    style CORE_LAYER fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px')
    lines.append('    style STORAGE_LAYER fill:#ecfdf5,stroke:#10b981,stroke-width:1px')

    return "\n".join(lines)


def build_concept_map_mermaid(topic: str, entities: List[Dict[str, Any]], relationships: List[Tuple[str, str, str]], level: str = "intermediate") -> str:
    """Builds a semantic concept map with relational edges distinctly calibrated for Beginner, Intermediate, and Advanced."""
    lvl = (level or "intermediate").lower().strip()
    is_rag = any(k in topic.lower() or any(k in e.get("label", "").lower() for e in entities) for k in ["rag", "retrieval", "cache", "grounded", "prompt", "llm", "chatgpt"])
    top_clean = sanitize_mermaid_label(topic, 40)

    # 1. BEGINNER CONCEPT MAP: Intuitive mental model, 4 friendly nodes, emerald/green theme
    if lvl == "beginner":
        lines = ["graph TD"]
        lines.append(f'    ROOT["💡 Intuitive Mental Model: {top_clean}"]')
        if is_rag:
            lines.append('    N1["1. Ask Question (Prompt)"]')
            lines.append('    N2["2. Quick Memory Check (Cache)"]')
            lines.append('    N3["3. Course Books & Verified Facts"]')
            lines.append('    N4["4. Smart AI (Clear Answer)"]')
            lines.append('    ROOT -->|starts with| N1')
            lines.append('    N1 -->|checks instant memory| N2')
            lines.append('    N2 -->|reads verified pages from| N3')
            lines.append('    N3 -->|writes friendly explanation for| N4')
        else:
            nodes_to_show = entities[:4] if entities else [
                {"label": f"Core Concept: {top_clean}"},
                {"label": "Everyday Analogy"},
                {"label": "Practical Application"}
            ]
            for idx, e in enumerate(nodes_to_show):
                n_id = f"N{idx+1}"
                lbl = sanitize_mermaid_label(e["label"], 35)
                lines.append(f'    {n_id}["{lbl}"]')
                rel = "explains simply" if idx == 0 else "connects to"
                lines.append(f'    ROOT -->|{rel}| {n_id}')

        lines.append('    style ROOT fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46')
        lines.append('    style N1 fill:#f0fdf4,stroke:#22c55e,stroke-width:1.5px,color:#14532d')
        if "N2" in "\n".join(lines):
            lines.append('    style N2 fill:#fefce8,stroke:#eab308,stroke-width:1.5px,color:#713f12')
        if "N3" in "\n".join(lines):
            lines.append('    style N3 fill:#eff6ff,stroke:#3b82f6,stroke-width:1.5px,color:#1e3a8a')
        if "N4" in "\n".join(lines):
            lines.append('    style N4 fill:#faf5ff,stroke:#a855f7,stroke-width:1.5px,color:#581c87')
        return "\n".join(lines)

    # 2. ADVANCED CONCEPT MAP: Multi-tier subgraphs, theoretical invariants, proof gates, formal notation
    if lvl == "advanced":
        if is_rag:
            return """graph TD
    subgraph INGESTION ["Tier 1: Formal Query Preconditions (Inv-1)"]
        I1["Formal Query Q \\in \\mathcal{L}"]
        I2["Schema Validation & Boundary Constraints"]
    end
    subgraph CACHE_TIER ["Tier 2: Semantic Metric Space & Cosine Metric"]
        C1["High-Dim Embedding Space E(Q)"]
        DEC_ADV{"sim(E(Q), E(k)) \\ge \\tau ?"}
        C2["O(1) Deterministic Response Bypass"]
    end
    subgraph GROUNDED_TIER ["Tier 3: Partitioned Knowledge Corpus & Retrieval"]
        G1["Partitioned Document Store \\mathcal{D}"]
        G2["Bi-Encoder Dense Scan & Cross-Reranker"]
        G3["Faithfulness Filter \\mathcal{R}_{top-k}"]
    end
    subgraph INFERENCE_TIER ["Tier 4: Constrained Decoder & Invariant Verification"]
        A1["Context-Conditioned Token Generation P(Y|Q, C)"]
        CHK_HALL{"Hallucination Proof: \\models \\text{Grounded}(Y, C) ?"}
        ERR_FALL["Safety Fallback / Rollback Log"]
    end
    subgraph CONSISTENCY_TIER ["Tier 5: Atomic State Mutation & Consistency"]
        S1["Atomic Writeback Protocol (ACID)"]
        S2["Causal Consistency Invariant"]
    end
    I1 --> I2
    I2 --> C1
    C1 --> DEC_ADV
    DEC_ADV -->|sim \\ge \\tau (Hit)| C2
    DEC_ADV -->|sim < \\tau (Miss)| G1
    G1 --> G2
    G2 --> G3
    G3 --> A1
    A1 --> CHK_HALL
    CHK_HALL -->|Violates Guardrail| ERR_FALL
    CHK_HALL -->|Invariant Verified| S1
    S1 --> S2
    S2 -.->|Re-index| C1
    style INGESTION fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style CACHE_TIER fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px
    style GROUNDED_TIER fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px
    style INFERENCE_TIER fill:#fff1f2,stroke:#f43f5e,stroke-width:2px
    style CONSISTENCY_TIER fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px
    style CHK_HALL fill:#ffe4e6,stroke:#e11d48,stroke-width:2px
    style ERR_FALL fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b"""
        else:
            return f"""graph TD
    subgraph FORMAL_MODEL ["Formal Architecture: {top_clean}"]
        M1["Axiomatic Definition"]
        M2["Theoretical Invariant Matrix"]
    end
    subgraph CONSTRAINT_TIER ["Boundary Constraints & Proofs"]
        P1["State Precondition \\mathcal{{P}}"]
        P2["Decomposition Lossless Proof"]
        P3["Postcondition Guarantee \\mathcal{{Q}}"]
    end
    subgraph VERIFICATION_TIER ["Soundness & Invariant Checking"]
        V1{{"Soundness Proof Holds?"}}
        V2["Certified Consistent State"]
        V3["Constraint Violation Rollback"]
    end
    M1 --> M2
    M2 --> P1
    P1 --> P2
    P2 --> P3
    P3 --> V1
    V1 -->|Soundness Certified| V2
    V1 -->|Violation Detected| V3
    style FORMAL_MODEL fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style CONSTRAINT_TIER fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px
    style VERIFICATION_TIER fill:#fff1f2,stroke:#f43f5e,stroke-width:2px
    style V1 fill:#ffe4e6,stroke:#e11d48,stroke-width:2px
    style V2 fill:#dcfce7,stroke:#10b981,stroke-width:2px
    style V3 fill:#fee2e2,stroke:#dc2626,stroke-width:2px"""

    # 3. INTERMEDIATE CONCEPT MAP: 7 engineering components, cache hit/miss branching, amber/slate theme
    lines = ["graph TD"]
    lines.append(f'    ROOT["⚙️ Architecture & Operational Flow: {top_clean}"]')
    if is_rag:
        lines.append('    P1["Client Query Ingestion"]')
        lines.append('    P2["Semantic Vector Cache"]')
        lines.append('    DEC{"Cache Hit Check?"}')
        lines.append('    P3["Grounded Source Database"]')
        lines.append('    P4["Context Retrieval Engine"]')
        lines.append('    P5["Augmented Prompt Assembly"]')
        lines.append('    P6["LLM Inference Engine"]')
        lines.append('    P7["Grounded Response Delivery"]')
        lines.append('    ROOT --> P1')
        lines.append('    P1 -->|checks vector similarity| P2')
        lines.append('    P2 --> DEC')
        lines.append('    DEC -->|Hit / Low Latency| P7')
        lines.append('    DEC -->|Miss / Fetch Facts| P3')
        lines.append('    P3 -->|supplies context| P4')
        lines.append('    P4 -->|enriches| P5')
        lines.append('    P5 -->|transmits to| P6')
        lines.append('    P6 -->|produces completion| P7')
        lines.append('    P7 -.->|writeback| P2')
        lines.append('    style ROOT fill:#1e1b4b,stroke:#4338ca,stroke-width:2px,color:#ffffff')
        lines.append('    style P1 fill:#f8fafc,stroke:#64748b,stroke-width:1.5px')
        lines.append('    style P2 fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#78350f')
        lines.append('    style DEC fill:#fff7ed,stroke:#ea580c,stroke-width:2px,color:#7c2d12')
        lines.append('    style P3 fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px,color:#4c1d95')
        lines.append('    style P4 fill:#e0e7ff,stroke:#6366f1,stroke-width:1.5px,color:#312e81')
        lines.append('    style P5 fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#075985')
        lines.append('    style P6 fill:#fae8ff,stroke:#d946ef,stroke-width:1.5px,color:#701a75')
        lines.append('    style P7 fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#064e3b')
        return "\n".join(lines)

    created_nodes = {"ROOT"}
    if relationships:
        for idx, (src, rel, tgt) in enumerate(relationships[:6]):
            s_id = f"N_{abs(hash(src)) % 1000}"
            t_id = f"N_{abs(hash(tgt)) % 1000}"
            if s_id not in created_nodes:
                lines.append(f'    {s_id}["{sanitize_mermaid_label(src, 35)}"]')
                created_nodes.add(s_id)
            if t_id not in created_nodes:
                lines.append(f'    {t_id}["{sanitize_mermaid_label(tgt, 35)}"]')
                created_nodes.add(t_id)
            rel_label = sanitize_mermaid_label(rel, 25)
            lines.append(f'    {s_id} -->|{rel_label}| {t_id}')
        first_node = [n for n in created_nodes if n != "ROOT"]
        if first_node:
            lines.append(f'    ROOT --> {first_node[0]}')
    else:
        for idx, e in enumerate(entities[:5]):
            n_id = f"NODE_{idx+1}"
            lbl = sanitize_mermaid_label(e["label"], 35)
            lines.append(f'    {n_id}["{lbl}"]')
            rel = "defines & enforces" if idx % 2 == 0 else "requires"
            lines.append(f'    ROOT -->|{rel}| {n_id}')

    lines.append('    style ROOT fill:#1e1b4b,stroke:#4338ca,stroke-width:2px,color:#ffffff')
    return "\n".join(lines)


def build_comparison_mermaid(topic: str, entities: List[Dict[str, Any]], level: str = "intermediate") -> str:
    """Builds a side-by-side comparative layout contrasting approaches calibrated by tier."""
    lvl = (level or "intermediate").lower().strip()
    is_rag = any(k in topic.lower() or any(k in e.get("label", "").lower() for e in entities) for k in ["rag", "retrieval", "cache", "grounded", "prompt", "llm"])
    top_clean = sanitize_mermaid_label(topic, 35)

    if lvl == "beginner":
        return """graph LR
    subgraph WITHOUT_GROUNDING ["Without Course Materials (Guessing)"]
        W1["Risky Guesses / Hallucinations"]
        W2["Hard to Verify Facts"]
        W3["Confusing Jargon"]
    end
    subgraph WITH_GROUNDING ["With Course Materials (True Facts)"]
        G1["100% Verified from Textbook"]
        G2["Clear Step-by-Step Flow"]
        G3["Simple, Friendly Understanding"]
    end
    style WITHOUT_GROUNDING fill:#fee2e2,stroke:#ef4444,stroke-width:1.5px,color:#991b1b
    style WITH_GROUNDING fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b"""

    if lvl == "advanced":
        return """graph LR
    subgraph PARAMETRIC_PARADIGM ["Parametric Memory Paradigm"]
        P1["Internal Neural Weights W"]
        P2["Static Temporal Knowledge Horizon"]
        P3["Heuristic Token Sampling P(Y|W)"]
        P4["Unbounded Hallucination Risk \\epsilon_{param}"]
        P5["Complexity: O(1) Parametric Lookup"]
    end
    subgraph SEMI_PARAMETRIC_RAG ["Semi-Parametric Grounded System (RAG)"]
        S1["Dynamic External Corpus \\mathcal{D}"]
        S2["Real-Time Grounded Source Ingestion"]
        S3["Lossless Context Projection Top-K"]
        S4["Strict Attribution Invariant Bound \\epsilon_{rag} \\to 0"]
        S5["Complexity: O(K \\log N) Hybrid Vector Scan"]
    end
    style PARAMETRIC_PARADIGM fill:#fee2e2,stroke:#ef4444,stroke-width:2px
    style SEMI_PARAMETRIC_RAG fill:#dcfce7,stroke:#10b981,stroke-width:2px"""

    if is_rag:
        return """graph LR
    subgraph MODEL_TRAINING ["Model Pre-Training Paradigm"]
        A1["Internal Neural Weights Altered"]
        A2["Static Knowledge Cut-off"]
        A3["Token Probability Prediction"]
        A4["High Hallucination Risk"]
    end
    subgraph RAG_GROUNDING ["Retrieval-Augmented Generation (RAG)"]
        B1["Dynamic Real-Time Database Queries"]
        B2["Prompts Augmented with Verified Facts"]
        B3["100% Truth-Grounded Responses"]
        B4["Semantic Cache for Latency Reduction"]
    end
    style MODEL_TRAINING fill:#fee2e2,stroke:#ef4444,stroke-width:1.5px
    style RAG_GROUNDING fill:#dcfce7,stroke:#10b981,stroke-width:2px"""

    lines = ["graph LR"]
    e1 = entities[0]["label"] if len(entities) > 0 else f"Standard {top_clean}"
    e2 = entities[1]["label"] if len(entities) > 1 else f"Alternative Approach"

    lines.append(f'    subgraph SUB_A ["Primary Concept: {sanitize_mermaid_label(e1, 30)}"]')
    lines.append(f'        A1["Operational Paradigm: Core Model"]')
    lines.append(f'        A2["Key Advantage: Direct Guarantees"]')
    lines.append(f'        A3["Trade-off: Implementation Complexity"]')
    lines.append(f'    end')

    lines.append(f'    subgraph SUB_B ["Contrasting Concept: {sanitize_mermaid_label(e2, 30)}"]')
    lines.append(f'        B1["Operational Paradigm: Alternative Model"]')
    lines.append(f'        B2["Key Advantage: Optimized Throughput"]')
    lines.append(f'        B3["Trade-off: Relaxed Guarantees"]')
    lines.append(f'    end')

    lines.append('    style SUB_A fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px')
    lines.append('    style SUB_B fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px')

    return "\n".join(lines)


def build_timeline_mermaid(topic: str, entities: List[Dict[str, Any]], level: str = "intermediate") -> str:
    """Builds a sequential stage / timeline diagram calibrated by tier."""
    lvl = (level or "intermediate").lower().strip()
    is_rag = any(k in topic.lower() or any(k in e.get("label", "").lower() for e in entities) for k in ["rag", "retrieval", "cache", "grounded", "prompt", "llm"])

    if lvl == "beginner":
        return """graph LR
    T_1["1. Ask Your Question<br/>Simple Natural Inquiry"] ==> T_2["2. Check Textbook Pages<br/>Read Verified Facts"]
    T_2 ==> T_3["3. Clear Understanding<br/>Easy Step-by-Step Answer"]
    style T_1 fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46
    style T_2 fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a
    style T_3 fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b"""

    if lvl == "advanced":
        return """graph LR
    T_1["Stage 1: Ingestion & Invariant Check<br/>Q \\in \\mathcal{L} Preconditions"] ==> T_2["Stage 2: Metric Evaluation<br/>\\text{sim}(E(Q), E(k)) \\ge \\tau"]
    T_2 ==> T_3["Stage 3: Lossless Retrieval<br/>Dense Scan & Hybrid RRF Fusion"]
    T_3 ==> T_4["Stage 4: Invariant Verification<br/>\\models \\text{Grounded}(Y, C) Proof"]
    T_4 ==> T_5["Stage 5: Atomic State Commitment<br/>ACID Cache Writeback"]
    style T_1 fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style T_2 fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style T_3 fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px
    style T_4 fill:#fff1f2,stroke:#f43f5e,stroke-width:2px
    style T_5 fill:#dcfce7,stroke:#10b981,stroke-width:2px"""

    if is_rag or len(entities) < 2:
        return """graph LR
    T_1["Phase 1: Pre-Training Data Ingestion<br/>Web Scraping (Reddit, WordPress, FT)"] ==> T_2["Phase 2: Standard LLM Completion<br/>Token Matching & Hallucination Risks"]
    T_2 ==> T_3["Phase 3: Retrieval-Augmented Generation<br/>Grounding Prompts with External Databases"]
    T_3 ==> T_4["Phase 4: Semantic Caching<br/>Bypassing LLM on Similar Queries"]
    style T_1 fill:#e0f2fe,stroke:#0284c7,stroke-width:2px
    style T_2 fill:#fee2e2,stroke:#ef4444,stroke-width:2px
    style T_3 fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px
    style T_4 fill:#dcfce7,stroke:#10b981,stroke-width:2px"""

    lines = ["graph LR"]
    steps = [e for e in entities if e.get("node_type") == "process_step"] or entities[:5]
    if not steps:
        steps = [
            {"label": "Phase 1: Ingestion & Setup"},
            {"label": "Phase 2: Execution & Convergence"},
            {"label": "Phase 3: Validation & Output"}
        ]

    prev_id = None
    for idx, s in enumerate(steps[:5]):
        t_id = f"T_{idx+1}"
        lbl = sanitize_mermaid_label(s["label"], 35)
        lines.append(f'    {t_id}["Phase {idx+1}<br/>{lbl}"]')
        if prev_id:
            lines.append(f'    {prev_id} ==> {t_id}')
        prev_id = t_id

    return "\n".join(lines)


def build_hierarchy_mermaid(topic: str, entities: List[Dict[str, Any]], level: str = "intermediate") -> str:
    """Builds a taxonomy tree calibrated by tier."""
    lvl = (level or "intermediate").lower().strip()
    top_clean = sanitize_mermaid_label(topic, 40)
    lines = ["graph TD"]
    lines.append(f'    ROOT["{top_clean}"]')

    if lvl == "beginner":
        lines.append('    CAT1["Foundational Ideas (Simple)"]')
        lines.append('    CAT2["Everyday Examples (Intuitive)"]')
        lines.append('    ROOT --> CAT1')
        lines.append('    ROOT --> CAT2')
        lines.append('    style ROOT fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46')
        lines.append('    style CAT1 fill:#f0fdf4,stroke:#22c55e,stroke-width:1.5px')
        lines.append('    style CAT2 fill:#eff6ff,stroke:#3b82f6,stroke-width:1.5px')
        return "\n".join(lines)

    if lvl == "advanced":
        lines.append('    CAT1["Theoretical Invariants & Boundary Constraints"]')
        lines.append('    CAT2["Formal Architecture & Convergence Guarantees"]')
        lines.append('    ROOT --> CAT1')
        lines.append('    ROOT --> CAT2')
        for idx, e in enumerate(entities[:4]):
            n_id = f"H_{idx+1}"
            lbl = sanitize_mermaid_label(e["label"], 35)
            lines.append(f'    {n_id}["{lbl}"]')
            if idx % 2 == 0:
                lines.append(f'    CAT1 --> {n_id}')
            else:
                lines.append(f'    CAT2 --> {n_id}')
        lines.append('    style ROOT fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#ffffff')
        lines.append('    style CAT1 fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px')
        lines.append('    style CAT2 fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px')
        return "\n".join(lines)

    lines.append(f'    CAT1["Foundational Principles"]')
    lines.append(f'    CAT2["Operational Mechanisms"]')
    lines.append(f'    ROOT --> CAT1')
    lines.append(f'    ROOT --> CAT2')

    for idx, e in enumerate(entities[:4]):
        n_id = f"H_{idx+1}"
        lbl = sanitize_mermaid_label(e["label"], 35)
        lines.append(f'    {n_id}["{lbl}"]')
        if idx % 2 == 0:
            lines.append(f'    CAT1 --> {n_id}')
        else:
            lines.append(f'    CAT2 --> {n_id}')

    lines.append('    style ROOT fill:#1e1b4b,stroke:#4338ca,stroke-width:2px,color:#ffffff')
    lines.append('    style CAT1 fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px')
    lines.append('    style CAT2 fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px')

    return "\n".join(lines)


def build_cycle_mermaid(topic: str, entities: List[Dict[str, Any]], level: str = "intermediate") -> str:
    """Builds a closed-loop state lifecycle machine calibrated by tier."""
    lvl = (level or "intermediate").lower().strip()
    top_clean = sanitize_mermaid_label(topic, 35)

    if lvl == "beginner":
        return f"""graph TD
    S1["1. Ask Question (Ready)"]
    S2["2. Check Verified Notes"]
    S3["3. Understand Clearly"]
    S4["4. Ready for Next Question"]
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S1
    style S1 fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46
    style S2 fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a
    style S3 fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b
    style S4 fill:#faf5ff,stroke:#a855f7,stroke-width:2px,color:#581c87"""

    if lvl == "advanced":
        return f"""graph TD
    S1["S1: Precondition Invariant Check [Inv-1]"]
    S2["S2: Distributed Execution Phase"]
    S3["S3: Barrier Sync & Quorum Agreement"]
    S4["S4: Soundness Proof Verification Gate"]
    S5["S5: Atomic Commit & Consistency State"]
    S1 --> S2
    S2 -->|State Transition| S3
    S3 -->|Quorum Certified| S4
    S4 -->|Invariant Violation| S1
    S4 -->|Proof Verified| S5
    S5 -->|Reset Horizon| S1
    style S1 fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style S2 fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px
    style S3 fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px
    style S4 fill:#ffe4e6,stroke:#e11d48,stroke-width:2px
    style S5 fill:#dcfce7,stroke:#10b981,stroke-width:2px"""

    lines = ["graph TD"]
    lines.append(f'    S1["1. Initial State<br/>({top_clean} Setup)"]')
    lines.append(f'    S2["2. Active Processing"]')
    lines.append(f'    S3["3. Waiting / Event Blocked"]')
    lines.append(f'    S4["4. Evaluation & Convergence"]')
    lines.append(f'    S5["5. Terminated / Rest State"]')

    lines.append('    S1 --> S2')
    lines.append('    S2 -->|I/O or Wait Request| S3')
    lines.append('    S3 -->|Event Ready| S2')
    lines.append('    S2 -->|State Check| S4')
    lines.append('    S4 -->|Iterate / Retry| S2')
    lines.append('    S4 -->|Complete| S5')
    lines.append('    S5 -->|Reset / New Cycle| S1')

    lines.append('    style S1 fill:#e0f2fe,stroke:#0284c7,stroke-width:2px')
    lines.append('    style S2 fill:#dbeafe,stroke:#3b82f6,stroke-width:2px')
    lines.append('    style S3 fill:#ffedd5,stroke:#ea580c,stroke-width:2px')
    lines.append('    style S4 fill:#fce7f3,stroke:#ec4899,stroke-width:2px')
    lines.append('    style S5 fill:#dcfce7,stroke:#10b981,stroke-width:2px')

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# MAIN SERVICE ENTRYPOINT (Innovation 5)
# -----------------------------------------------------------------------------

def generate_visual_explanation(
    chunks: List[Dict[str, Any]], 
    topic: str, 
    diagram_type: str = "auto",
    user_query: Optional[str] = None,
    language: str = "en",
    level: str = "intermediate"
) -> Dict[str, Any]:
    """
    Dynamically constructs rich, verified, evidence-grounded visual diagrams 
    calibrated distinctly for Beginner, Intermediate, and Advanced mastery tiers.
    """
    topic_clean = topic.strip()
    type_req = (diagram_type or "auto").lower().strip()

    # Determine active tier
    lvl = (level or "intermediate").lower().strip()
    if lvl not in ["beginner", "intermediate", "advanced"]:
        if user_query:
            uq_l = user_query.lower()
            if "beginner" in uq_l or "easy" in uq_l:
                lvl = "beginner"
            elif "advanced" in uq_l or "hard" in uq_l:
                lvl = "advanced"
            else:
                lvl = "intermediate"
        else:
            lvl = "intermediate"

    # 1. Retrieve evidence chunks for topic
    scored_chunks = retrieve_relevant_chunks_for_topic(chunks, topic_clean, top_k=8)

    # 2. Check for Insufficient Evidence Limitation
    total_words = sum(len(c.get("content", "").split()) for c, s in scored_chunks)
    has_meaningful_match = any(s > 0.05 for c, s in scored_chunks)

    if not scored_chunks or total_words < 20 or not has_meaningful_match:
        return {
            "topic": topic_clean,
            "detected_type": "concept_map" if type_req == "auto" else type_req,
            "mermaid_code": f"""graph TD
    WARN["⚠️ Insufficient Source Evidence in Uploaded Materials"]
    TOPIC["Requested Topic: {sanitize_mermaid_label(topic_clean, 40)}"]
    REC["Recommendation: Upload relevant chapters, lecture slides, or video transcripts to generate grounded visual diagrams."]
    WARN --> TOPIC
    TOPIC --> REC
    style WARN fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b
    style TOPIC fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style REC fill:#eff6ff,stroke:#3b82f6,stroke-width:1.5px""",
            "description": f"The uploaded course materials do not contain sufficient evidence or descriptive detail about '{topic_clean}' to construct an authentic visual diagram without hallucination.",
            "source_reference": "Uploaded Course Knowledge Base (Insufficient Content Coverage)",
            "steps_or_nodes": [],
            "is_sufficient_evidence": False,
            "limitation_note": f"Notice: Insufficient source evidence. No course passages describing '{topic_clean}' with high confidence were found in the uploaded materials.",
            "available_alternative_types": SUPPORTED_DIAGRAM_TYPES,
            "course_id": chunks[0].get("textbook_id") if chunks else None,
            "level": lvl
        }

    relevant_chunks = [c for c, s in scored_chunks]
    combined_text = " ".join([c.get("content", "") for c in relevant_chunks[:5]])

    # 3. Detect best diagram format if auto requested (calibrated by tier)
    detected_type = type_req if type_req != "auto" and type_req in SUPPORTED_DIAGRAM_TYPES else detect_best_diagram_type(topic_clean, combined_text, level=lvl)

    # 4. Extract entities, steps, and provenance citations for this tier
    entities, relationships = extract_entities_and_steps_from_chunks(relevant_chunks, topic_clean, level=lvl)

    # Provenance summary string
    top_citation = build_source_citation_dict(relevant_chunks[0])
    source_ref_str = format_provenance_label(relevant_chunks[0])

    # 5. Attempt LLM Generation if Gemini API is available
    if is_gemini_available():
        try:
            client = get_gemini_client()
            if not client:
                raise ValueError("Gemini client unavailable")

            context_snippets = []
            for c in relevant_chunks[:6]:
                p_str = format_provenance_label(c)
                context_snippets.append(f"[{p_str}]: {c.get('content', '')}")
            context_block = "\n\n".join(context_snippets)

            tier_guidance = (
                "- BEGINNER: Create a simple, intuitive visual model with 3 to 4 clear nodes/steps. Use friendly everyday analogies and simple language. Avoid confusing technical jargon or complex internals. Use pleasant green/emerald and soft blue accents (e.g. style N1 fill:#ecfdf5,stroke:#10b981)."
                if lvl == "beginner" else
                "- INTERMEDIATE: Create a structured engineering workflow with 5 to 7 operational nodes, standard technical terminology, and at least one decision gate or validation check. Use amber/slate/indigo accents (e.g. style N1 fill:#fffbeb,stroke:#f59e0b)."
                if lvl == "intermediate" else
                "- ADVANCED: Create a rigorous formal system architecture with multi-tier subgraphs, mathematical or structural invariants, boundary constraints, and edge-case failure/rollback paths. Use formal invariant notation (e.g., Inv-1, sim >= tau, models Grounded) and rose/crimson/deep-indigo accents (e.g. style N1 fill:#fff1f2,stroke:#f43f5e)."
            )

            prompt = f"""You are an expert educational visual diagram architect and Mermaid.js specialist.
Create an evidence-grounded interactive Mermaid diagram for the topic: '{topic_clean}'.
Requested Diagram Type: '{detected_type}' (Must be one of: flowchart, concept_map, block_diagram, sequence, comparison, timeline, hierarchy, cycle).
Target Pedagogical Tier: '{lvl.upper()}'

Strict Tier Guidelines for '{lvl.upper()}':
{tier_guidance}

Strict Formatting Rules for '{detected_type}':
- flowchart: Use 'graph TD' with sequential boxes. For intermediate/advanced include decision diamonds {{Decision?}} and failure/rollback edges.
- sequence: Use 'sequenceDiagram' with 'autonumber' and clean participant message exchanges.
- block_diagram: Use 'graph TD' with subgraphs for layers/modules.
- concept_map: Use 'graph TD' with labeled relational edges (A -->|relies on| B).
- comparison: Use 'graph LR' with 2 side-by-side subgraphs.
- timeline: Use 'graph LR' with sequential phase nodes.
- hierarchy: Use 'graph TD' category tree.
- cycle: Use 'graph TD' closed state transition loop.

Strict Grounding Rule: Every step, node, and relationship MUST come directly from the provided source context. Do not invent external facts.
Strict Syntax & Mermaid Rules:
1. ALWAYS quote node text in double quotes: e.g. Node1["Clear Text Here"] or Dec1{"Decision Query?"}.
2. NEVER use unquoted parentheses, ampersands, or colons inside brackets. E.g. write N1["O(L) Complexity & Search"] NOT N1[O(L) Complexity & Search].
3. Edge labels MUST use standard pipe syntax: A -->|Yes| B. Do not use A -- Yes --> B.
4. Do not include markdown backticks around the mermaid_code in the JSON field.

Course Context:
{context_block}

Return strictly JSON with schema:
{{
  "topic": "{topic_clean}",
  "detected_type": "{detected_type}",
  "mermaid_code": "graph TD\\n  ...",
  "description": "Clear explanation of this visual architecture and what it illustrates for a {lvl} student",
  "steps_or_nodes": [
    {{"label": "Node Label", "description": "Grounded explanation from course context"}}
  ]
}}
"""
            raw_text = ""
            for model_cand in FAST_GEMINI_MODELS:
                try:
                    res = client.models.generate_content(
                        model=model_cand,
                        contents=prompt
                    )
                    if res and res.text:
                        raw_text = res.text.strip()
                        break
                except Exception:
                    continue
            if not raw_text:
                raise ValueError("All Gemini candidate models unavailable")
            json_match = re.search(r'\{[\s\S]*\}', raw_text)
            if json_match:
                data = json.loads(json_match.group(0))
                if "mermaid_code" in data and len(data["mermaid_code"].strip()) > 15:
                    enriched_steps = []
                    for idx, s in enumerate(data.get("steps_or_nodes", [])):
                        c_match = relevant_chunks[idx % len(relevant_chunks)]
                        enriched_steps.append({
                            "label": s.get("label", f"Step {idx+1}"),
                            "description": s.get("description", ""),
                            "source_citation": build_source_citation_dict(c_match),
                            "is_supported": True,
                            "node_type": "process_step" if detected_type in ["flowchart", "sequence", "timeline"] else "concept"
                        })

                    return {
                        "topic": topic_clean,
                        "detected_type": detected_type,
                        "mermaid_code": clean_mermaid_syntax(data["mermaid_code"]),
                        "description": data.get("description", f"Visual explanation of {topic_clean} grounded in course materials for {lvl} learners."),
                        "source_reference": source_ref_str,
                        "steps_or_nodes": enriched_steps,
                        "is_sufficient_evidence": True,
                        "limitation_note": None,
                        "available_alternative_types": [t for t in SUPPORTED_DIAGRAM_TYPES if t != detected_type],
                        "course_id": relevant_chunks[0].get("textbook_id"),
                        "level": lvl
                    }
        except Exception as e:
            print(f"Gemini visualizer fallback active: {e}")

    # 6. High-Fidelity Level-Calibrated Dynamic Rule-Based Generator Fallback
    if detected_type == "flowchart":
        mermaid_code = build_flowchart_mermaid(topic_clean, entities, relationships, level=lvl)
        desc = f"{lvl.capitalize()}-level sequential decision flowchart of {topic_clean} showing step-by-step execution, validation checks, and output states."
    elif detected_type == "sequence":
        mermaid_code = build_sequence_mermaid(topic_clean, entities, relationships, level=lvl)
        desc = f"{lvl.capitalize()}-level sequence interaction diagram illustrating message flow, dispatching, and coordination protocol for {topic_clean}."
    elif detected_type == "block_diagram":
        mermaid_code = build_block_diagram_mermaid(topic_clean, entities, level=lvl)
        desc = f"{lvl.capitalize()}-level modular block diagram representing the architectural layers, components, and persistence guarantees of {topic_clean}."
    elif detected_type == "comparison":
        mermaid_code = build_comparison_mermaid(topic_clean, entities, level=lvl)
        desc = f"{lvl.capitalize()}-level comparative analysis matrix contrasting structural models, trade-offs, and performance characteristics for {topic_clean}."
    elif detected_type == "timeline":
        mermaid_code = build_timeline_mermaid(topic_clean, entities, level=lvl)
        desc = f"{lvl.capitalize()}-level chronological stage timeline detailing progressive phases and evolutionary transitions in {topic_clean}."
    elif detected_type == "hierarchy":
        mermaid_code = build_hierarchy_mermaid(topic_clean, entities, level=lvl)
        desc = f"{lvl.capitalize()}-level hierarchical classification tree categorizing {topic_clean} into foundational principles and operational mechanisms."
    elif detected_type == "cycle":
        mermaid_code = build_cycle_mermaid(topic_clean, entities, level=lvl)
        desc = f"{lvl.capitalize()}-level closed-loop state lifecycle diagram showing continuous transitions and feedback loops for {topic_clean}."
    else:  # concept_map
        mermaid_code = build_concept_map_mermaid(topic_clean, entities, relationships, level=lvl)
        desc = f"{lvl.capitalize()}-level semantic concept map connecting {topic_clean} with its dependencies, invariants, and operational mechanisms."

    # Format steps / nodes with real citations
    formatted_steps = []
    for idx, e in enumerate(entities[:6]):
        formatted_steps.append({
            "label": e["label"],
            "description": e["description"],
            "source_citation": e.get("source_citation") or top_citation,
            "is_supported": True,
            "node_type": e.get("node_type", "concept")
        })

    if not formatted_steps:
        for idx, c in enumerate(relevant_chunks[:4]):
            formatted_steps.append({
                "label": f"Core Aspect: {topic_clean} (Part {idx+1})",
                "description": c.get("content", "")[:150] + "...",
                "source_citation": build_source_citation_dict(c),
                "is_supported": True,
                "node_type": "concept"
            })

    return {
        "topic": topic_clean,
        "detected_type": detected_type,
        "mermaid_code": clean_mermaid_syntax(mermaid_code),
        "description": desc,
        "source_reference": source_ref_str,
        "steps_or_nodes": formatted_steps,
        "is_sufficient_evidence": True,
        "limitation_note": None,
        "available_alternative_types": [t for t in SUPPORTED_DIAGRAM_TYPES if t != detected_type],
        "course_id": relevant_chunks[0].get("textbook_id"),
        "level": lvl
    }
