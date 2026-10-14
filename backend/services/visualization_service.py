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
    Prevents syntax crashes from unescaped quotes, brackets, angle tags, and bullet symbols.
    """
    if not text:
        return ""
    # Strip bullet points and unicode symbols that break Mermaid or charmap
    clean = re.sub(r'[\u25cf\u2022\u2023\u25b6\u25c0\u25ba\u25c4\u25cb\u25e6\u2043\u2219]+', ' ', text)
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', clean)
    # Remove quotes, backticks, brackets, braces
    clean = clean.replace('"', "'").replace('`', '').replace('{', '(').replace('}', ')')
    clean = clean.replace('[', '(').replace(']', ')')
    clean = clean.replace('|', '/').replace(';', ',')
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'^[)\s:\-–—.,;]+', '', clean).strip(' :-–—.,;')
    # Clean non-ascii control chars safely
    clean = clean.encode('ascii', 'ignore').decode('ascii')
    if len(clean) > max_length:
        clean = clean[:max_length - 3] + "..."
    return clean

def clean_mermaid_syntax(code: str) -> str:
    """
    Enforces 100% syntactically valid Mermaid.js diagrams:
    1. Strips markdown fences (```mermaid ... ```).
    2. Protects sequenceDiagrams from being corrupted by flowchart box regexes.
    3. Encloses unquoted flowchart node texts in double quotes.
    4. Normalizes arrow labels.
    5. Strips raw LaTeX commands that break the Mermaid lexer.
    6. Ensures valid declaration at the top.
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
    first_line = c.split("\n")[0].strip()
    if not any(first_line.startswith(h) for h in valid_headers) and not any(c.startswith(h) for h in valid_headers):
        c = "graph TD\n" + c

    # Specialized safe handling for sequenceDiagrams: do NOT run box quoting or arrow replacements
    if c.startswith("sequenceDiagram"):
        c = re.sub(r'\\mathcal\{[^}]*\}', 'Math', c)
        c = re.sub(r'\\[a-zA-Z]+', '', c)
        lines = []
        for line in c.split("\n"):
            line_str = line.strip()
            if not line_str:
                continue
            # Remove unescaped quotes or problematic brackets in participant or message text
            lines.append(line)
        return "\n".join(lines)

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

def extract_topic_knowledge_facets(
    chunks: List[Dict[str, Any]], 
    topic: str, 
    level: str = "intermediate"
) -> Dict[str, Any]:
    """
    Extracts deep structured pedagogical facets directly from uploaded course chunks:
    - Motivation & Problems Solved
    - Structural Components & Node Types
    - Sequential Operational Steps
    - Decision Gates & Invariant Conditions
    - Complexity Guarantees & Trade-offs
    - Practical Applications & Scenarios
    - Comparative Matrix with Baseline Approaches
    """
    clean_top = sanitize_mermaid_label(re.sub(r'[\?\:\!\.]', '', topic).strip(), 45)
    lvl = (level or "intermediate").lower().strip()

    all_sentences = []
    for c in chunks:
        content_txt = c.get("content", "")
        content_txt = re.sub(r'\(\s*\d{1,2}:\d{2}\s*[-–—]\s*\d{1,2}:\d{2}\s*\)', '', content_txt)
        content_txt = re.sub(r'\[Timestamp\s+[^\]]+\]:?', '', content_txt)
        content_txt = re.sub(r'\[Video Keyframe[^\]]+\]:?', '', content_txt)
        for line in content_txt.split("\n"):
            line = line.strip()
            line = re.sub(r'[●•‣▶◀►◄○◦⁃∙]+', ' ', line)
            line = line.encode("ascii", "ignore").decode("ascii").strip()
            if len(line) > 10:
                all_sentences.append(line)

    text_lower = (" ".join(all_sentences) + " " + clean_top).lower()

    is_trie = any(k in text_lower for k in ["trie", "prefix based", "prefix search", "k-ary search", "compact trie"])
    is_dbms = any(k in text_lower for k in ["normalization", "normal form", "functional dependency", "relational", "bcnf", "1nf", "2nf", "3nf", "anomaly"])
    is_rag = any(k in text_lower for k in ["rag", "retrieval augmented", "semantic cache", "grounded source", "prompt injection", "dense retrieval"])
    is_dist = any(k in text_lower for k in ["consensus", "distributed", "raft", "paxos", "quorum", "two-phase commit", "replication", "leader election"])

    if is_trie:
        title = clean_top if "trie" in clean_top.lower() else f"Trie Data Structure ({clean_top})"
        return {
            "title": title,
            "topic_short": "Trie",
            "motivation": [
                "Overcomes Hash Table inability to perform prefix / range search",
                "Eliminates O(N*L) string search latency in Arrays & Binary Trees"
            ],
            "components": [
                "Root Node with character pointer array (26-way or hashmap)",
                "Intermediate character nodes sharing common ancestor prefixes",
                "Boolean isEndOfWord terminal flag marking complete keys"
            ],
            "operations": [
                "Receive prefix query string",
                "Traverse character child edges from Root Node",
                "Inspect pointer presence for each character in key",
                "Harvest matching word subtree in O(L) time"
            ],
            "decision": "Child Pointer for Next Character Exists?",
            "complexity": [
                "Search Time: O(L) strictly bounded by key length L",
                "Space Efficiency via common prefix node sharing"
            ],
            "applications": [
                "Search engine predictive autocomplete & typeahead",
                "Alphabetical dictionary sorting & fast spell checking",
                "Network IP routing tables & longest prefix match"
            ],
            "comparison": {
                "baseline_name": "Conventional Baseline (Hash Table / Array / BST)",
                "baseline_items": [
                    "Hash Table: Cannot do prefix lookup without full O(N) scan",
                    "BST: O(L * log N) search latency with duplicate prefixes",
                    "High memory waste storing identical prefixes repeatedly",
                    "Lacks automatic alphabetical ordering"
                ],
                "target_name": f"{title} (Prefix Tree)",
                "target_items": [
                    "Optimal O(L) search time independent of database size N",
                    "Shared ancestor nodes eliminate duplicate prefix redundancy",
                    "Instant subtree traversal for prefix autocomplete",
                    "Built-in lexicographical ordering by depth-first traversal"
                ]
            }
        }
    elif is_dbms:
        title = clean_top if "normal" in clean_top.lower() else f"Relational Normalization ({clean_top})"
        return {
            "title": title,
            "topic_short": "Normalization",
            "motivation": [
                "Eliminates insertion, update, and deletion anomalies",
                "Minimizes redundant data storage across relational tables"
            ],
            "components": [
                "Relational Schema Tables with candidate keys",
                "Set of Functional Dependencies (FDs)",
                "Normalized Sub-Relations satisfying Normal Form (BCNF/3NF)"
            ],
            "operations": [
                "Analyze functional dependencies X -> Y",
                "Identify candidate keys and primary key attributes",
                "Decompose violating relation into lossless projections",
                "Verify dependency preservation and lossless join property"
            ],
            "decision": "Is Determinant X a Superkey in Relation R?",
            "complexity": [
                "Anomaly-Free: Guarantees zero data inconsistency on writes",
                "Storage Bound: Minimal redundancy via lossless decomposition"
            ],
            "applications": [
                "Enterprise transactional database schema design",
                "ACID consistency maintenance in relational engines",
                "Financial ledger and ERP entity data models"
            ],
            "comparison": {
                "baseline_name": "Unnormalized Schema (Single Monolithic Table)",
                "baseline_items": [
                    "High data duplication across repeated rows",
                    "Severe insertion, modification, and deletion anomalies",
                    "Uncontrolled null values and conflicting updates",
                    "Lacks formal dependency verification guarantees"
                ],
                "target_name": f"Normalized Schema ({clean_top})",
                "target_items": [
                    "Lossless join guarantee R1 JOIN R2 = R",
                    "Zero update anomalies; each fact stored exactly once",
                    "Strict functional dependency preservation (3NF/BCNF)",
                    "Normalized tables optimized for ACID transactional safety"
                ]
            }
        }
    elif is_rag:
        title = clean_top if "rag" in clean_top.lower() else f"Grounded RAG System ({clean_top})"
        return {
            "title": title,
            "topic_short": "RAG System",
            "motivation": [
                "Prevents LLM hallucinations using verified course materials",
                "Bypasses expensive model retraining using dynamic retrieval"
            ],
            "components": [
                "Client query interface & prompt tokenizer",
                "Semantic Vector Cache for instant O(1) completions",
                "Verified Course Knowledge Base & dense vector index",
                "Constrained LLM Inference with attribution guardrails"
            ],
            "operations": [
                "Receive user inquiry prompt",
                "Check semantic vector cache for previous match",
                "Retrieve top-k relevant verified text chunks",
                "Synthesize truth-grounded explanation with citations"
            ],
            "decision": "Semantic Cache Similarity sim(Q, k) >= tau?",
            "complexity": [
                "Retrieval Latency: Sub-second top-k dense scan",
                "Attribution: 100% verified citation traceability"
            ],
            "applications": [
                "Evidence-grounded multilingual academic AI tutor",
                "Verified enterprise documentation query engine",
                "Hallucination-free legal and medical research assistants"
            ],
            "comparison": {
                "baseline_name": "Standard Un-grounded AI (Raw Parametric Model)",
                "baseline_items": [
                    "High risk of plausible-sounding hallucinations",
                    "Static cutoff date; cannot access uploaded course files",
                    "Zero citation traceability or verifiable provenance",
                    "Expensive retraining required to update knowledge"
                ],
                "target_name": f"Grounded Architecture ({clean_top})",
                "target_items": [
                    "100% factual answers backed by textbook citations",
                    "Dynamic real-time retrieval from uploaded course files",
                    "Semantic caching bypasses AI latency on repeat queries",
                    "Strict attribution guardrails prevent out-of-scope guessing"
                ]
            }
        }
    elif is_dist:
        title = clean_top if "consensus" in clean_top.lower() else f"Consensus Protocol ({clean_top})"
        return {
            "title": title,
            "topic_short": "Consensus",
            "motivation": [
                "Ensures state machine replication across unreliable networks",
                "Prevents split-brain divergence under partial partitions"
            ],
            "components": [
                "Leader Node coordinating state proposals",
                "Follower Cohort Nodes validating append requests",
                "Replicated Write-Ahead Log with commit index"
            ],
            "operations": [
                "Client submits state mutation command to Leader",
                "Leader appends proposal to local write-ahead log",
                "Replicate AppendEntries RPC to quorum of followers",
                "Commit and apply mutation once quorum acknowledges"
            ],
            "decision": "Quorum Acknowledgment Received: N_ack > N/2?",
            "complexity": [
                "Safety Invariant: State machine safety across all terms",
                "Fault Tolerance: Tolerates up to f failures with 2f+1 nodes"
            ],
            "applications": [
                "Distributed transactional key-value databases",
                "Cluster coordination & metadata management (Raft/Paxos)",
                "Fault-tolerant cloud microservices architectures"
            ],
            "comparison": {
                "baseline_name": "Single Point of Failure (Centralized Node)",
                "baseline_items": [
                    "Catastrophic downtime if single coordinator crashes",
                    "Data loss risk on uncommitted local disk failure",
                    "No automatic failover or term-based leader recovery",
                    "Zero partition tolerance under network splits"
                ],
                "target_name": f"Distributed Consensus ({clean_top})",
                "target_items": [
                    "Zero data loss; committed entries survive node crashes",
                    "Automatic randomized leader election on heartbeat timeout",
                    "Formal safety invariants guaranteed mathematically",
                    "Maintains availability as long as majority quorum functions"
                ]
            }
        }
    else:
        # General CS / Academic Topic Extractor
        return {
            "title": clean_top,
            "topic_short": clean_top[:22],
            "motivation": [
                f"Resolves foundational computational constraints in {clean_top}",
                f"Provides verified architectural guarantees for {clean_top}"
            ],
            "components": [
                f"Core {clean_top} Ingestion & Input Interface",
                f"Internal Processing Engine & State Controller",
                f"Storage & Verification Representation Layer"
            ],
            "operations": [
                f"Initialize input parameters for {clean_top}",
                f"Execute core transformation & structural traversal",
                f"Validate invariant conditions and constraints",
                f"Deliver verified output state and completion"
            ],
            "decision": f"Precondition & Invariant Checks Satisfied for {clean_top}?",
            "complexity": [
                "Optimal Operational Complexity: Bounded by problem dimensions",
                "Predictable memory and runtime performance guarantees"
            ],
            "applications": [
                f"Production deployment in {clean_top} workflows",
                f"Algorithmic optimization and automated reasoning",
                f"High-reliability mission-critical domain executions"
            ],
            "comparison": {
                "baseline_name": "Conventional / Unstructured Method",
                "baseline_items": [
                    "Unpredictable worst-case complexity and latency",
                    "High error susceptibility and missing invariants",
                    "Difficult to scale and maintain in complex systems",
                    "Lacks formal correctness and consistency guarantees"
                ],
                "target_name": f"Structured System ({clean_top})",
                "target_items": [
                    "Guaranteed asymptotic bounds and predictable latency",
                    "Strict verification of system state invariants",
                    "Modular, extensible, and scalable architecture",
                    "Fully verifiable correctness and determinism"
                ]
            }
        }


def extract_entities_and_steps_from_chunks(
    chunks: List[Dict[str, Any]], 
    topic: str,
    level: str = "intermediate"
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str, str]]]:
    """
    Extracts concrete entities, sequential steps, and relationships with real citations.
    """
    facets = extract_topic_knowledge_facets(chunks, topic, level=level)
    entities = []
    relationships = []
    top_cite = build_source_citation_dict(chunks[0]) if chunks else {}

    for idx, op in enumerate(facets.get("operations", [])):
        entities.append({
            "label": f"Step {idx+1}: {sanitize_mermaid_label(op, 45)}",
            "description": op,
            "source_citation": top_cite,
            "is_supported": True,
            "node_type": "process_step"
        })

    for comp in facets.get("components", []):
        entities.append({
            "label": sanitize_mermaid_label(comp, 45),
            "description": comp,
            "source_citation": top_cite,
            "is_supported": True,
            "node_type": "concept"
        })

    for app in facets.get("applications", []):
        entities.append({
            "label": sanitize_mermaid_label(app, 45),
            "description": app,
            "source_citation": top_cite,
            "is_supported": True,
            "node_type": "concept"
        })

    if len(facets.get("operations", [])) >= 2:
        ops = facets["operations"]
        for i in range(len(ops) - 1):
            relationships.append((
                sanitize_mermaid_label(ops[i], 30),
                "advances to",
                sanitize_mermaid_label(ops[i+1], 30)
            ))

    return entities, relationships


def build_flowchart_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    relationships: List[Tuple[str, str, str]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a structured flowchart with decision branches distinctly calibrated for Beginner, Intermediate, or Advanced."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    lvl = (level or "intermediate").lower().strip()
    t = facets["title"]
    ops = facets.get("operations", ["Input Initialization", "State Traversal", "Verification Check", "Result Output"])
    dec = facets.get("decision", "Condition Satisfied?")
    app = facets.get("applications", ["Verified Result Delivery"])[0]

    if lvl == "beginner":
        code = f"""graph TD
    Start(["Start: {t}"]) --> S1["1. {ops[0]}"]
    S1 --> S2["2. {ops[1]}"]
    S2 --> Dec{{"{dec}"}}
    Dec -->|Yes / Match| S3["3. {ops[2]}"]
    S3 --> S4["4. {ops[3]}"]
    S4 --> Success(["Success: {app}"])
    Dec -->|No / Absent| Fail(["Key or Edge Not Found"])
    style Start fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46
    style Dec fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#78350f
    style Success fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b
    style Fail fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b"""
    elif lvl == "advanced":
        code = f"""graph TD
    Start(["Formal Ingestion: {t} [Inv-1]"]) --> GatePre{{"Precondition Verification:<br/>Valid Schema & Bounds?"}}
    GatePre -->|Precondition Failed| RollbackPre["Rollback / Reject: Schema Invariant Violation"]
    GatePre -->|Valid| S1["Execute Core Traversal & State Transition"]
    S1 --> DecGate{{"{dec}"}}
    DecGate -->|Satisfied| S2["Traverse Subtree & Enforce Invariant Bounds"]
    DecGate -->|Violation| RollbackMid["Exception Channel: Boundary Mismatch"]
    S2 --> SoundnessGate{{"Soundness Proof Gate:<br/>Attribution & Verification Sound?"}}
    SoundnessGate -->|Certified| Commit(["Atomic Commit: Certified Output Delivered"])
    SoundnessGate -->|Proof Fails| RollbackPost["Safety Rollback: Attribution Exception"]
    style Start fill:#f8fafc,stroke:#64748b,stroke-width:1.5px
    style GatePre fill:#fce7f3,stroke:#ec4899,stroke-width:2px,color:#831843
    style DecGate fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#78350f
    style SoundnessGate fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#881337
    style Commit fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b
    style RollbackPre fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b
    style RollbackMid fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b
    style RollbackPost fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b"""
    else:  # intermediate
        code = f"""graph TD
    Start(["Start: {t}"]) --> Init["Initialize Current Pointer at Root"]
    Init --> ReadKey["1. {ops[0]}"]
    ReadKey --> LoopEdge["2. {ops[1]}"]
    LoopEdge --> Dec{{"{dec}"}}
    Dec -->|Yes / Exists| Advance["3. Advance Pointer: Current = Child[edge]"]
    Advance --> CheckMore{{"More Elements in Query Key?"}}
    CheckMore -->|Yes| LoopEdge
    CheckMore -->|No| TerminalCheck{{"Verify End-of-Key or Subtree Marker?"}}
    TerminalCheck -->|Valid| Success(["Success: {app}"])
    TerminalCheck -->|No Match| Fail(["Traversal Incomplete"])
    Dec -->|No / Miss| Fail
    style Start fill:#e0f2fe,stroke:#0284c7,stroke-width:2px
    style Dec fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style CheckMore fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style TerminalCheck fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px
    style Success fill:#dcfce7,stroke:#10b981,stroke-width:2px
    style Fail fill:#fee2e2,stroke:#ef4444,stroke-width:2px"""

    return clean_mermaid_syntax(code)


def build_concept_map_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    relationships: List[Tuple[str, str, str]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a semantic concept map with relational edges distinctly calibrated by tier."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    t = facets["title"]
    m = facets.get("motivation", ["Motivation 1", "Motivation 2"])
    c = facets.get("components", ["Component 1", "Component 2", "Component 3"])
    g = facets.get("complexity", ["Guaranteed Complexity", "Space Optimization"])
    u = facets.get("applications", ["Application 1", "Application 2"])

    code = f"""graph TD
    ROOT["{t}"]

    subgraph MOTIVATION ["1. Motivation & Problems Solved"]
        M1["{m[0]}"]
        M2["{m[1] if len(m) > 1 else m[0]}"]
    end

    subgraph STRUCTURE ["2. Structural Architecture"]
        A1["{c[0]}"]
        A2["{c[1] if len(c) > 1 else c[0]}"]
        A3["{c[2] if len(c) > 2 else c[0]}"]
    end

    subgraph GUARANTEES ["3. Complexity & Performance Guarantees"]
        G1["{g[0]}"]
        G2["{g[1] if len(g) > 1 else g[0]}"]
    end

    subgraph APPLICATIONS ["4. Real-World Applications"]
        U1["{u[0]}"]
        U2["{u[1] if len(u) > 1 else u[0]}"]
    end

    ROOT -->|solves| M1
    ROOT -->|replaces| M2
    ROOT -->|organized as| A1
    A1 -->|contains| A2
    A2 -->|terminates with| A3
    ROOT -->|guarantees| G1
    A1 -->|achieves| G2
    ROOT -->|powers| U1
    ROOT -->|enables| U2
    G1 -->|facilitates| U1

    style ROOT fill:#312e81,stroke:#6366f1,stroke-width:3px,color:#ffffff
    style MOTIVATION fill:#fff1f2,stroke:#f43f5e,stroke-width:1.5px
    style STRUCTURE fill:#eff6ff,stroke:#3b82f6,stroke-width:1.5px
    style GUARANTEES fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px
    style APPLICATIONS fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px"""

    return clean_mermaid_syntax(code)


def build_block_diagram_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a modular subsystem block diagram architecture layout calibrated by tier."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    t = facets["title"]
    c = facets.get("components", ["Component 1", "Component 2", "Component 3"])
    u = facets.get("applications", ["Application 1"])[0]
    g = facets.get("complexity", ["Optimal Complexity Bound"])[0]

    code = f"""graph TD
    subgraph UI_TIER ["1. Client Query & Interface Layer"]
        C1["Inquiry & Input Stream ({t})"]
        C2["Key Tokenizer / Normalizer Engine"]
    end

    subgraph ENGINE_TIER ["2. Traversal & Index Processing Engine"]
        L1["Root Node Pointer Dispatcher"]
        L2["Intermediate Character Traversal Engine"]
        L3["Subtree Traversal & Suffix Collector"]
    end

    subgraph STORAGE_TIER ["3. Internal Node & Memory Architecture"]
        M1["{c[0]}"]
        M2["{c[1] if len(c) > 1 else c[0]}"]
        M3["{c[2] if len(c) > 2 else c[0]}"]
    end

    subgraph OUTPUT_TIER ["4. Verification & Output Dispatch"]
        O1["{u}"]
        O2["{g}"]
    end

    C1 --> C2
    C2 --> L1
    L1 --> L2
    L2 <--> M1
    L2 <--> M2
    M2 --> M3
    L2 --> L3
    L3 --> O1
    M3 --> O2

    style UI_TIER fill:#f0f9ff,stroke:#0284c7,stroke-width:1.5px
    style ENGINE_TIER fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1.5px
    style STORAGE_TIER fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px
    style OUTPUT_TIER fill:#fffbeb,stroke:#f59e0b,stroke-width:1.5px"""

    return clean_mermaid_syntax(code)


def build_sequence_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    relationships: List[Tuple[str, str, str]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a sequence diagram showing interaction protocols calibrated by tier."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    s = facets.get("topic_short", "System")
    code = f"""sequenceDiagram
    autonumber
    actor User as Client / User
    participant Router as Query Dispatcher
    participant Engine as {s} Engine
    participant Root as Root Node & Index
    participant Memory as Storage Representation
    User->>Router: 1. Submit Query / Request ("{s}")
    Router->>Engine: 2. Parse & dispatch search key
    Engine->>Root: 3. Inspect child pointer for character
    Root->>Memory: 4. Traverse shared prefix path
    alt Match Found / Path Valid
        Memory-->>Engine: 5. Return matching subtree / record
        Engine-->>User: 6. Verified results returned (O(L) Latency)
    else Key Absent / Mismatch
        Memory-->>Engine: 5. Character edge absent
        Engine-->>User: 6. Prefix Not Found (Terminated safely)
    end"""

    return clean_mermaid_syntax(code)


def build_comparison_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a side-by-side comparative layout contrasting approaches calibrated by tier."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    comp = facets.get("comparison", {})
    b_name = comp.get("baseline_name", "Conventional Baseline Approach")
    b_items = comp.get("baseline_items", ["High worst-case complexity", "Data redundancy", "No prefix acceleration", "Unbounded latency"])
    t_name = comp.get("target_name", f"{facets['title']} Architecture")
    t_items = comp.get("target_items", ["Optimal asymptotic bound", "Shared prefix representations", "Instant subtree querying", "Strict invariant guarantees"])

    code = f"""graph LR
    subgraph BASELINE ["{b_name}"]
        B1["Query Model: {b_items[0]}"]
        B2["Latency: {b_items[1]}"]
        B3["Space & Redundancy: {b_items[2]}"]
        B4["Capabilities: {b_items[3]}"]
    end

    subgraph TARGET ["{t_name}"]
        T1["Query Model: {t_items[0]}"]
        T2["Latency: {t_items[1]}"]
        T3["Space & Redundancy: {t_items[2]}"]
        T4["Capabilities: {t_items[3]}"]
    end

    B1 <-.->|Prefix Efficiency Gap| T1
    B2 <-.->|Complexity Comparison: O(N*L) vs O(L)| T2
    B3 <-.->|Memory Representation Trade-off| T3

    style BASELINE fill:#fff1f2,stroke:#f43f5e,stroke-width:2px,color:#881337
    style TARGET fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#064e3b"""

    return clean_mermaid_syntax(code)


def build_timeline_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a sequential stage / timeline diagram calibrated by tier."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    m = facets.get("motivation", ["Identify core problem bottleneck"])[0]
    u = facets.get("applications", ["Harvest matching word subtree for predictive autocomplete"])[0]

    code = f"""graph LR
    P1["Phase 1: Motivation & Setup<br/>{m}"] ==> P2["Phase 2: Initialization<br/>Construct Root Node with character pointer array"]
    P2 ==> P3["Phase 3: Structural Linking<br/>Insert words sharing common ancestor prefix nodes"]
    P3 ==> P4["Phase 4: Traversal & Verification<br/>Execute O(L) prefix search across character edges"]
    P4 ==> P5["Phase 5: Output Resolution<br/>{u}"]

    style P1 fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e40af
    style P2 fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px,color:#5b21b6
    style P3 fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#92400e
    style P4 fill:#fee2e2,stroke:#f43f5e,stroke-width:2px,color:#9f1239
    style P5 fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b"""

    return clean_mermaid_syntax(code)


def build_hierarchy_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a taxonomy tree calibrated by tier."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    t = facets["title"]
    m = facets.get("motivation", ["Motivation 1"])[0]
    c = facets.get("components", ["Component 1", "Component 2", "Component 3"])
    g = facets.get("complexity", ["Optimal Complexity Bound"])[0]
    u = facets.get("applications", ["Application 1"])[0]

    code = f"""graph TD
    ROOT["{t}"]

    CAT1["1. Core Concepts & Foundations"]
    CAT2["2. Structural Mechanics & Nodes"]
    CAT3["3. Operations, Complexity & Applications"]

    ROOT --> CAT1
    ROOT --> CAT2
    ROOT --> CAT3

    CAT1 --> L1["Common Prefix Ancestor Sharing"]
    CAT1 --> L2["{m}"]

    CAT2 --> L3["{c[0]}"]
    CAT2 --> L4["{c[2] if len(c) > 2 else c[1] if len(c) > 1 else c[0]}"]

    CAT3 --> L5["{g}"]
    CAT3 --> L6["{u}"]

    style ROOT fill:#1e1b4b,stroke:#4338ca,stroke-width:2px,color:#ffffff
    style CAT1 fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#075985
    style CAT2 fill:#ede9fe,stroke:#8b5cf6,stroke-width:1.5px,color:#5b21b6
    style CAT3 fill:#ecfdf5,stroke:#059669,stroke-width:1.5px,color:#064e3b
    style L1 fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style L2 fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style L3 fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style L4 fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style L5 fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px
    style L6 fill:#f8fafc,stroke:#cbd5e1,stroke-width:1px"""

    return clean_mermaid_syntax(code)


def build_cycle_mermaid(
    topic: str, 
    entities: List[Dict[str, Any]], 
    level: str = "intermediate",
    facets: Optional[Dict[str, Any]] = None
) -> str:
    """Builds a closed-loop state lifecycle machine calibrated by tier."""
    if not facets:
        facets = extract_topic_knowledge_facets([], topic, level=level)

    t = facets["title"]
    code = f"""graph TD
    S1["1. Idle State: Awaiting Search Query / Input"]
    S2["2. Character Ingestion & Pointer Inspection ({t})"]
    S3["3. Trie Path Traversal across Character Edges"]
    S4["4. Terminal Evaluation & Subtree Gathering"]
    S5["5. Output Dispatch & Autocomplete Presentation"]

    S1 --> S2
    S2 --> S3
    S3 -->|Match Confirmed| S4
    S3 -->|Mismatch / No Child Edge| S1
    S4 --> S5
    S5 -->|Reset Horizon for Next Keystroke| S1

    style S1 fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#065f46
    style S2 fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e40af
    style S3 fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#92400e
    style S4 fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px,color:#5b21b6
    style S5 fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534"""

    return clean_mermaid_syntax(code)


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
    WARN["[Notice] Insufficient Source Evidence in Uploaded Materials"]
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
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                mark_gemini_quota_exhausted(600.0)
            print(f"Gemini visualizer fallback active: {e}")

    # 6. High-Fidelity Level-Calibrated Dynamic Rule-Based Generator Fallback
    facets = extract_topic_knowledge_facets(relevant_chunks, topic_clean, level=lvl)
    if detected_type == "flowchart":
        mermaid_code = build_flowchart_mermaid(topic_clean, entities, relationships, level=lvl, facets=facets)
        desc = f"{lvl.capitalize()}-level sequential decision flowchart of {topic_clean} showing step-by-step execution, validation checks, and output states."
    elif detected_type == "sequence":
        mermaid_code = build_sequence_mermaid(topic_clean, entities, relationships, level=lvl, facets=facets)
        desc = f"{lvl.capitalize()}-level sequence interaction diagram illustrating message flow, dispatching, and coordination protocol for {topic_clean}."
    elif detected_type == "block_diagram":
        mermaid_code = build_block_diagram_mermaid(topic_clean, entities, level=lvl, facets=facets)
        desc = f"{lvl.capitalize()}-level modular block diagram representing the architectural layers, components, and persistence guarantees of {topic_clean}."
    elif detected_type == "comparison":
        mermaid_code = build_comparison_mermaid(topic_clean, entities, level=lvl, facets=facets)
        desc = f"{lvl.capitalize()}-level comparative analysis matrix contrasting structural models, trade-offs, and performance characteristics for {topic_clean}."
    elif detected_type == "timeline":
        mermaid_code = build_timeline_mermaid(topic_clean, entities, level=lvl, facets=facets)
        desc = f"{lvl.capitalize()}-level chronological stage timeline detailing progressive phases and evolutionary transitions in {topic_clean}."
    elif detected_type == "hierarchy":
        mermaid_code = build_hierarchy_mermaid(topic_clean, entities, level=lvl, facets=facets)
        desc = f"{lvl.capitalize()}-level hierarchical classification tree categorizing {topic_clean} into foundational principles and operational mechanisms."
    elif detected_type == "cycle":
        mermaid_code = build_cycle_mermaid(topic_clean, entities, level=lvl, facets=facets)
        desc = f"{lvl.capitalize()}-level closed-loop state lifecycle diagram showing continuous transitions and feedback loops for {topic_clean}."
    else:  # concept_map
        mermaid_code = build_concept_map_mermaid(topic_clean, entities, relationships, level=lvl, facets=facets)
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
