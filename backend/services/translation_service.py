import os
import re
import json
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List, Tuple
from config import (
    GEMINI_API_KEY, 
    SARVAM_API_KEY,
    mark_gemini_quota_exhausted,
    is_gemini_available
)

# -----------------------------------------------------------------------------
# CENTRALIZED MULTILINGUAL TAMIL LEARNING SERVICE
# -----------------------------------------------------------------------------

# In-memory translation cache to optimize speed and eliminate duplicate calls
_TRANSLATION_CACHE: Dict[str, str] = {}

# Rate limit / quota circuit breaker state
_GEMINI_QUOTA_COOLDOWN = 0

def _is_quota_cooldown_active() -> bool:
    global _GEMINI_QUOTA_COOLDOWN
    return time.time() < _GEMINI_QUOTA_COOLDOWN

def _set_quota_cooldown(seconds: int = 300):
    global _GEMINI_QUOTA_COOLDOWN
    _GEMINI_QUOTA_COOLDOWN = time.time() + seconds

# -----------------------------------------------------------------------------
# 1. ACADEMIC STEM & COMPUTER SCIENCE TERMINOLOGY GLOSSARY
# -----------------------------------------------------------------------------
# Preserves technical precision while providing accessible Tamil glosses.
ACADEMIC_STEM_TERMS: Dict[str, str] = {
    # Operating Systems & Concurrency
    "round robin scheduling": "Round Robin scheduling (சுழற்சி முறை ஒதுக்கீடு)",
    "round robin": "Round Robin (சுழற்சி முறை ஒதுக்கீடு)",
    "time quantum": "Time Quantum (ஒதுக்கப்படும் நிர்ணய நேரம்)",
    "ready queue": "Ready Queue (தயாராக காத்திருக்கும் வரிசை)",
    "context switch": "Context Switch (ஒரு process-இலிருந்து மற்றொன்றிற்கு CPU மாறுதல்)",
    "context switching": "Context Switching (செயல்முறை மாறுதல்)",
    "process": "Process (செயல்முறை)",
    "processes": "Processes (செயல்முறைகள்)",
    "thread": "Thread (இழை)",
    "threads": "Threads (இழைகள்)",
    "cpu": "CPU (மைய செயலி)",
    "deadlock": "Deadlock (முட்டுக்கட்டை நிலை)",
    "semaphore": "Semaphore (சமிக்ஞை கட்டுப்படுத்தி)",
    "mutex": "Mutex (பரஸ்பர விலக்கு)",
    "paging": "Paging (பக்கமாக்கல்)",
    "virtual memory": "Virtual Memory (மெய்நிகர் நினைவகம்)",
    "preemption": "Preemption (முன்னுரிமை அடிப்படையிலான இடைமறிப்பு)",
    "preemptive": "Preemptive (முன்னுரிமை இடைமறிக்கும்)",
    "non-preemptive": "Non-preemptive (இடைமறிக்காத)",
    "throughput": "Throughput (செயல்திறன் அளவு)",
    "turnaround time": "Turnaround Time (மொத்த நிறைவு நேரம்)",
    "waiting time": "Waiting Time (காத்திருக்கும் நேரம்)",
    "response time": "Response Time (பதில் அளிக்கும் நேரம்)",
    "burst time": "Burst Time (இயங்கும் நேரம்)",
    "first-come first-served": "First-Come First-Served (FCFS - முதலில் வருபவருக்கு முன்னுரிமை)",
    "shortest job first": "Shortest Job First (SJF - குறுகிய பணிக்கு முன்னுரிமை)",

    # Database Systems & Relational Theory
    "database system concepts & relational normalization": "தரவுத்தள அமைப்பு கருத்துக்கள் & தொடர்புடைய சீராக்கம்",
    "database normalization": "தரவுத்தள சீராக்கம் (Database Normalization)",
    "relational database": "தொடர்புடைய தரவுத்தளம் (Relational Database)",
    "relational model & anomalies": "தொடர்புடைய மாதிரி & முரண்பாடுகள்",
    "relational model": "தொடர்புடைய மாதிரி (Relational Model)",
    "candidate keys, primary keys, and superkeys": "வேட்பாளர் சாவி, முதன்மை சாவி மற்றும் சூப்பர்கீ",
    "first normal form (1nf) & atomic values": "முதல் இயல்பு வடிவம் (1NF) & அணு மதிப்புகள்",
    "first normal form": "முதல் இயல்பு வடிவம் (First Normal Form - 1NF)",
    "1nf": "1NF (முதல் இயல்பு வடிவம்)",
    "second normal form (2nf) & partial dependencies": "இரண்டாம் இயல்பு வடிவம் (2NF) & பகுதி சார்புநிலைகள்",
    "second normal form": "இரண்டாம் இயல்பு வடிவம் (Second Normal Form - 2NF)",
    "2nf": "2NF (இரண்டாம் இயல்பு வடிவம்)",
    "third normal form (3nf) & boyce-codd normal form (bcnf)": "மூன்றாம் இயல்பு வடிவம் (3NF) & பாய்ஸ்-கோட் வடிவம் (BCNF)",
    "third normal form": "மூன்றாம் இயல்பு வடிவம் (Third Normal Form - 3NF)",
    "3nf": "3NF (மூன்றாம் இயல்பு வடிவம்)",
    "boyce-codd normal form (bcnf)": "பாய்ஸ்-கோட் இயல்பு வடிவம் (BCNF)",
    "boyce-codd normal form": "பாய்ஸ்-கோட் இயல்பு வடிவம் (BCNF)",
    "bcnf": "BCNF (பாய்ஸ்-கோட் வடிவம்)",
    "transactions and acid properties": "பரிவர்த்தனைகள் மற்றும் ACID பண்புகள்",
    "acid properties (atomicity, consistency, isolation, durability)": "ACID பண்புகள் (முழுமை, நிலைத்தன்மை, தனிமை, நீடித்த தன்மை)",
    "acid properties": "ACID பண்புகள் (Atomicity, Consistency, Isolation, Durability)",
    "definition of 1nf & eliminating repeating groups": "1NF வரையறை & தொடர் குழுக்களை நீக்குதல்",
    "understanding partial functional dependency": "பகுதி செயல்பாட்டு சார்புநிலையைப் புரிந்துகொள்ளுதல்",
    "decomposition into 2nf relations": "2NF அட்டவணைகளாகப் பிரித்தல் (Decomposition)",
    "transitive dependencies & 3nf rules": "கடந்துசெல்லும் சார்புநிலைகள் & 3NF விதிகள்",
    "atomic values": "பிரிக்க முடியாத தனி மதிப்புகள் (Atomic Values)",
    "atomic value": "பிரிக்க முடியாத தனி மதிப்பு (Atomic Value)",
    "functional dependency": "செயல்பாட்டு சார்புநிலை (Functional Dependency)",
    "functional dependencies": "செயல்பாட்டு சார்புநிலைகள் (Functional Dependencies)",
    "partial dependency": "பகுதி சார்புநிலை (Partial Dependency)",
    "partial functional dependency": "பகுதி செயல்பாட்டு சார்புநிலை (Partial Functional Dependency)",
    "transitive dependency": "கடந்துசெல்லும் சார்புநிலை (Transitive Dependency)",
    "multivalued dependency": "பல்மதிப்பு சார்புநிலை (Multivalued Dependency)",
    "candidate key": "வேட்பாளர் சாவி (Candidate Key)",
    "candidate keys": "வேட்பாளர் சாவிகள் (Candidate Keys)",
    "primary key": "முதன்மை சாவி (Primary Key)",
    "superkey": "சூப்பர்கீ (Superkey)",
    "superkeys": "சூப்பர்கீகள் (Superkeys)",
    "foreign key": "வெளிநாட்டு சாவி (Foreign Key)",
    "composite key": "கூட்டு சாவி (Composite Key)",
    "non-prime attribute": "முதன்மை அல்லாத பண்புக்கூறு (Non-prime Attribute)",
    "non-prime attributes": "முதன்மை அல்லாத பண்புக்கூறுகள் (Non-prime Attributes)",
    "prime attribute": "முதன்மை பண்புக்கூறு (Prime Attribute)",
    "prime attributes": "முதன்மை பண்புக்கூறுகள் (Prime Attributes)",
    "transaction": "பரிவர்த்தனை (Transaction)",
    "atomicity": "முழுமைத்தன்மை (Atomicity - எல்லாம் அல்லது எதுவுமில்லை)",
    "consistency": "நிலைத்தன்மை (Consistency)",
    "isolation": "தனிமைப்படுத்தல் (Isolation)",
    "durability": "நீடித்து நிற்கும் தன்மை (Durability)",
    "data redundancy": "தேவையற்ற தரவு நகல் (Data Redundancy)",
    "redundancy": "தேவையற்ற நகலெடுப்பு (Redundancy)",
    "anomalies": "முரண்பாடுகள் (Anomalies)",
    "anomaly": "முரண்பாடு (Anomaly)",
    "insertion anomaly": "செருகல் முரண்பாடு (Insertion Anomaly)",
    "deletion anomaly": "நீக்கல் முரண்பாடு (Deletion Anomaly)",
    "update anomaly": "புதுப்பித்தல் முரண்பாடு (Update Anomaly)",
    "lossless decomposition": "இழப்பற்ற பிரிப்பு (Lossless Decomposition)",
    "dependency preservation": "சார்புநிலை பாதுகாப்பு (Dependency Preservation)",
    "relational schema": "தொடர்புடைய கட்டமைப்பு (Relational Schema)",
    "relational algebra": "தொடர்புடைய இயற்கணிதம் (Relational Algebra)",
    "tuple": "வரிசை/பதிவு (Tuple)",
    "tuples": "வரிசைகள்/பதிவுகள் (Tuples)",
    "attribute": "பண்புக்கூறு (Attribute)",
    "attributes": "பண்புக்கூறுகள் (Attributes)",

    # Data Structures & Algorithms
    "trie data structure": "Trie தரவு அமைப்பு (முன்னொட்டு மரம் - Prefix Tree)",
    "trie": "Trie (முன்னொட்டு தேடல் மரம்)",
    "prefix based search": "முன்னொட்டு அடிப்படையிலான தேடல் (Prefix Based Search)",
    "prefix search": "முன்னொட்டு தேடல் (Prefix Search)",
    "hash table": "ஹேஷ் அட்டவணை (Hash Table)",
    "binary search tree": "இருbinary தேடல் மரம் (Binary Search Tree)",
    "time complexity": "நேரச் சிக்கல்தன்மை (Time Complexity)",
    "space complexity": "இடச் சிக்கல்தன்மை (Space Complexity)",
    "autocomplete": "தானியங்கி நிரப்புதல் (Autocomplete)",
    "spell checker": "எழுத்துப் பிழை திருத்தி (Spell Checker)",
    "longest prefix matching": "நீளமான முன்னொட்டு பொருத்தம் (Longest Prefix Matching)",

    # AI, ML & Retrieval Augmented Generation (RAG)
    "retrieval augmented generation": "Retrieval-Augmented Generation (மீட்டெடுப்புடன் கூடிய உரை உருவாக்கம் - RAG)",
    "rag": "RAG (Retrieval-Augmented Generation)",
    "semantic cache": "Semantic Cache (பொருள்சார் நினைவகம்)",
    "semantic caching": "Semantic Caching (பொருள்சார் நினைவக சேமிப்பு)",
    "vector database": "வெக்டர் தரவுத்தளம் (Vector Database)",
    "embeddings": "எம்பட்டிங்குகள் (Embeddings)",
    "cosine similarity": "கொசைன் ஒற்றுமை (Cosine Similarity)",
    "large language model": "பெரிய மொழி மாதிரி (LLM)",
    "llm": "LLM (பெரிய மொழி மாதிரி)",
    "prompt": "Prompt (உள்ளீட்டு கேள்வி/தூண்டல்)",
    "user prompt": "பயனர் உள்ளீடு (User Prompt)",
    "context retrieval": "சூழல் மீட்டெடுப்பு (Context Retrieval)",
    "hallucination": "தவறான கற்பனை விடை (Hallucination)",
    "grounding": "மூலத் தரவு அடிப்படை (Grounding)",
    "dense retrieval": "செறிவான மீட்டெடுப்பு (Dense Retrieval)",
    "reranker": "மறுவரிசைப்படுத்தி (Reranker)"
}

# English-to-Tamil Core Academic Sentence Patterns
ACADEMIC_SENTENCE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"According to the course materials on ([^,]+), what (.+)\?", re.IGNORECASE),
     r"\1 பற்றிய பாடப் புத்தக உள்ளடக்கத்தின்படி, \2 என்ன?"),
    (re.compile(r"Why is understanding '([^']+)' an essential prerequisite before studying '([^']+)'\?", re.IGNORECASE),
     r"'\2'-ஐப் படிப்பதற்கு முன் '\1'-ஐப் புரிந்துகொள்வது ஏன் அவசியமான முன்நிபந்தனை?"),
    (re.compile(r"'([^']+)' directly builds upon and requires the foundational principles of '([^']+)'\.", re.IGNORECASE),
     r"'\1' என்பது '\2'-ன் அடிப்படைக் கோட்பாடுகளை நேரடியாகச் சார்ந்து அதனடிப்படையில் கட்டமைக்கப்படுகிறது."),
    (re.compile(r"A table is in ([^.]+) if ([^.]+)\.", re.IGNORECASE),
     r"ஒரு அட்டவணை \2 என்றால் அது \1-ல் இருக்கும்."),
    (re.compile(r"The primary goal of ([^ ]+) is to ([^.]+)\.", re.IGNORECASE),
     r"\1-ன் முதன்மை நோக்கம் \2 ஆகும்."),
    (re.compile(r"Notice: Insufficient source evidence\. ([^.]+)\.", re.IGNORECASE),
     r"அறிவிப்பு: போதிய மூலச் சான்றுகள் இல்லை. \1.")
]

# Reverse Concept Dictionary (Tamil terms back to English concepts for answer evaluation)
TAMIL_TO_CONCEPT_MAP: Dict[str, str] = {
    "நேர அளவு": "time quantum",
    "டைம் குவாண்டம்": "time quantum",
    "ஒதுக்கப்படும் நிர்ணய நேரம்": "time quantum",
    "சுழற்சி முறை": "round robin",
    "ரவுண்ட் ராபின்": "round robin",
    "செயல்முறை": "process",
    "செயல்முறைகள்": "processes",
    "மைய செயலி": "cpu",
    "காத்திருக்கும் வரிசை": "ready queue",
    "மாறுதல்": "context switch",
    "முட்டுக்கட்டை": "deadlock",
    "அணு மதிப்புகள்": "atomic values",
    "இரண்டாம் இயல்பு வடிவம்": "second normal form",
    "முதல் இயல்பு வடிவம்": "first normal form",
    "மூன்றாம் இயல்பு வடிவம்": "third normal form",
    "பகுதி சார்புநிலை": "partial dependency",
    "பகுதி சார்புநிலையை": "partial dependency",
    "பகுதி சார்பு": "partial dependency",
    "சார்புநிலை": "dependency",
    "சார்புநிலையை": "dependency",
    "நீக்குகிறது": "eliminates",
    "நீக்குவது": "eliminates",
    "கடந்துசெல்லும் சார்புநிலை": "transitive dependency",
    "கடந்துசெல்லும் சார்பு": "transitive dependency",
    "வேட்பாளர் சாவி": "candidate key",
    "முதன்மை சாவி": "primary key",
    "சூப்பர்கீ": "superkey",
    "வெளிநாட்டு சாவி": "foreign key",
    "முழுமைத்தன்மை": "atomicity",
    "நிலைத்தன்மை": "consistency",
    "தனிமைப்படுத்தல்": "isolation",
    "நீடித்த தன்மை": "durability",
    "தேவையற்ற நகல்": "redundancy",
    "நகலெடுப்பு": "redundancy",
    "முரண்பாடு": "anomaly",
    "செருகல்": "insertion",
    "நீக்கல்": "deletion",
    "புதுப்பித்தல்": "update",
    "முன்னொட்டு": "prefix",
    "மீட்டெடுப்பு": "retrieval",
    "நினைவகம்": "cache"
}

# -----------------------------------------------------------------------------
# 2. LITERAL & CITATION PROTECTION ENGINE
# -----------------------------------------------------------------------------

def protect_literals(text: str) -> Tuple[str, List[str]]:
    """
    Extracts code blocks, math formulas, citations, URLs, and numeric IDs 
    and replaces them with tokens so that citations and code are NEVER altered.
    """
    if not text:
        return text, []

    protected: List[str] = []
    
    def replacer(match):
        token = f"__PROT_TOKEN_{len(protected)}__"
        protected.append(match.group(0))
        return token

    working = text

    # 1. Code blocks (```...```)
    working = re.sub(r'```[\s\S]*?```', replacer, working)
    
    # 2. Inline code (`...`)
    working = re.sub(r'`[^`\n]+`', replacer, working)

    # 3. Source citations: (Pages X-Y), (Page X), (Slide X), (Timestamp XX:XX), and composite (Page 14, file.pdf), [Source ...]
    working = re.sub(r'\[Source\s+\d+[^\]]*\]', replacer, working)
    working = re.sub(r'\((?:Pages?\s+\d+(?:-\d+)?|Slide\s+\d+|Timestamp\s+\d{1,2}:\d{2}|\d{1,2}:\d{2})(?:\s*[,|]\s*[^)]+)?\)', replacer, working)
    working = re.sub(r'\[(?:Pages?\s+\d+(?:-\d+)?|Slide\s+\d+|Timestamp\s+\d{1,2}:\d{2}|\d{1,2}:\d{2})(?:\s*[,|]\s*[^\]]+)?\]', replacer, working)
    
    # 4. LaTeX math equations: $...$ or $$...$$
    working = re.sub(r'\$\$[\s\S]*?\$\$', replacer, working)
    working = re.sub(r'\$[^\$\n]+\$', replacer, working)

    # 5. File extensions / filenames: e.g. document.pdf, lecture.pptx, clip.mp4
    working = re.sub(r'\b[A-Za-z0-9_\-]+\.(?:pdf|pptx?|mp4|docx?|json|csv)\b', replacer, working)

    return working, protected

def restore_literals(text: str, protected: List[str]) -> str:
    """Restores the exact, untouched citations, code, and identifiers."""
    if not text or not protected:
        return text

    res = text
    for idx, original in enumerate(protected):
        token = f"__PROT_TOKEN_{idx}__"
        res = res.replace(token, original)
    return res

# -----------------------------------------------------------------------------
# 3. GOOGLE GEMINI OFFICIAL AI TRANSLATION PROVIDER
# -----------------------------------------------------------------------------

# Supported candidate models with gemini-3.5-flash-lite as primary (fast, low token footprint, high availability)
GEMINI_TRANSLATION_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
]

def is_sarvam_available() -> bool:
    """Sarvam translation is superseded by Google Gemini to prevent HTTP 402 payment errors."""
    return False

def mark_sarvam_rate_limited(duration_seconds: float = 120.0):
    """Backward compatibility no-op."""
    pass

def _translate_with_sarvam(text: str, source_lang: str = "en", target_lang: str = "ta") -> Optional[str]:
    """Deprecated: Sarvam is deactivated. Requests are routed through Google Gemini."""
    return None

def _translate_with_gemini_single_chunk(text: str, source_lang: str = "en", target_lang: str = "ta") -> Optional[str]:
    """
    Translates text between English and Tamil using the official Google Gemini API (google.genai).
    - Preserves academic technical concepts, math formulas, programming code, and citation tokens.
    - Handles rate limits and quota exhaustion with automatic circuit breaker cooldown.
    - Tries candidate models in order.
    """
    if not GEMINI_API_KEY or _is_quota_cooldown_active():
        return None

    clean_text = text.strip()
    if not clean_text:
        return text

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[Gemini Translation] Client init note: {e}")
        return None

    if target_lang == "ta":
        prompt = f"""You are an expert bilingual STEM professor and translator specializing in educational textbooks and course materials.
Translate the following academic explanation into fluent, natural Tamil.

Strict Pedagogical & Technical Rules:
1. Retain English technical terms and programming concepts with natural Tamil glosses where appropriate (e.g. 'Round Robin scheduling (சுழற்சி முறை ஒதுக்கீடு)', 'CPU (மைய செயலி)', 'Time Quantum (ஒதுக்கப்படும் நேரம்)').
2. Preserve programming code, variable names, math equations ($...$, $$...$$), and numbers exactly as given.
3. NEVER alter or fabricate citation references, filenames, page numbers, or timestamps. Crucially: leave all tokens like __PROT_TOKEN_0__, __PROT_TOKEN_1__ completely untouched!
4. Deliver clear, idiomatic, accessible Tamil explanations suited for university students.
5. Output ONLY the translated Tamil text without any preamble, conversational greeting, or closing notes.

English Source:
{clean_text}"""
    else:
        prompt = f"""You are an expert academic translator specializing in Indian language course materials.
Translate the following Tamil educational text into clear, precise academic English for course search and assessment.

Strict Rules:
1. Preserve technical terminology, programming keywords, formulas, and numbers.
2. Crucially: leave all tokens like __PROT_TOKEN_0__, __PROT_TOKEN_1__ completely untouched!
3. Output ONLY the translated English text without preamble or conversational remarks.

Tamil Source:
{clean_text}"""

    for model_name in GEMINI_TRANSLATION_MODELS:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if res and res.text:
                translated = res.text.strip()
                # Clean up any potential markdown code fence if wrapped
                if translated.startswith("```") and translated.endswith("```"):
                    lines = translated.split("\n")
                    if len(lines) >= 3:
                        translated = "\n".join(lines[1:-1]).strip()
                if translated and len(translated) > 1:
                    return translated
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                print(f"[Gemini Translation] Model {model_name} quota exceeded (429): engaging cooldown.")
                _set_quota_cooldown(300)
                mark_gemini_quota_exhausted(300.0)
                break
            elif "503" in err_msg or "UNAVAILABLE" in err_msg:
                print(f"[Gemini Translation] Model {model_name} unavailable (503): trying fallback.")
                continue
            elif "404" in err_msg or "NOT_FOUND" in err_msg:
                continue
            else:
                print(f"[Gemini Translation] Model {model_name} error: {e}")
                continue

    return None

def _translate_with_gemini(text: str, source_lang: str = "en", target_lang: str = "ta") -> Optional[str]:
    """
    High-level Gemini translator handling both short texts and multi-paragraph course documents.
    """
    if not GEMINI_API_KEY or _is_quota_cooldown_active():
        return None

    src = "ta" if source_lang in ["ta", "tamil", "ta-IN"] else "en"
    tgt = "ta" if target_lang in ["ta", "tamil", "ta-IN"] else "en"

    if src == tgt:
        return text

    # Single chunk for reasonable lengths (<= 1500 chars)
    if len(text) <= 1500:
        return _translate_with_gemini_single_chunk(text, source_lang=src, target_lang=tgt)

    # For larger texts (e.g. multi-section summaries, long explanations), translate paragraph by paragraph
    paragraphs = text.split("\n")
    translated_paras: List[str] = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            translated_paras.append(para)
            continue

        para_cache_key = f"{src}_{tgt}_{hash(stripped)}"
        if para_cache_key in _TRANSLATION_CACHE:
            translated_paras.append(_TRANSLATION_CACHE[para_cache_key])
            continue

        res = _translate_with_gemini_single_chunk(stripped, source_lang=src, target_lang=tgt)
        if res is not None:
            m = re.match(r'^([#\-\*\d\.\s]+)', para)
            prefix = m.group(1) if m else ""
            final_p = prefix + res if prefix and not res.startswith(prefix.strip()) else res
            _TRANSLATION_CACHE[para_cache_key] = final_p
            translated_paras.append(final_p)
        else:
            return None

    return "\n".join(translated_paras)


# -----------------------------------------------------------------------------
# 4. HIGH-FIDELITY SYNTACTIC & TERMINOLOGY-AWARE RULE-BASED TRANSLATOR
# -----------------------------------------------------------------------------

# Common academic phrase & connective translations
ACADEMIC_CONNECTIVES: List[Tuple[str, str]] = [
    ("for example,", "எடுத்துக்காட்டாக,"),
    ("for example", "எடுத்துக்காட்டாக"),
    ("in other words,", "வேறு விதமாகக் கூறினால்,"),
    ("in conclusion,", "முடிவாக,"),
    ("therefore,", "எனவே,"),
    ("hence,", "ஆகையால்,"),
    ("in contrast,", "மாறாக,"),
    ("on the other hand,", "மற்றொரு புறம்,"),
    ("according to the course materials,", "பாடப் புத்தகத்தின்படி,"),
    ("according to the course material,", "பாடப் புத்தகத்தின்படி,"),
    ("based on the uploaded materials,", "பதிவேற்றப்பட்ட மூலங்களின்படி,"),
    ("it is defined as", "இது வரையறுக்கப்படுகிறது:"),
    ("is defined as", "என்று வரையறுக்கப்படுகிறது:"),
    ("is known as", "என்று அழைக்கப்படுகிறது:"),
    ("refers to", "குறிக்கிறது:"),
    ("ensures that", "உறுதிசெய்கிறது:"),
    ("requires that", "கட்டாயமாக்குகிறது:"),
    ("consists of", "கொண்டுள்ளது:"),
    ("eliminates", "நீக்குகிறது"),
    ("minimizes", "குறைக்கிறது"),
    ("prevents", "தடுக்கிறது"),
    ("because", "ஏனெனில்"),
    ("due to", "காரணமாக"),
    ("as a result,", "இதன் விளைவாக,"),
    ("step-by-step", "படிப்படியாக"),
    ("key concepts:", "முக்கிய கருத்துக்கள்:"),
    ("important points:", "முக்கிய குறிப்புகள்:"),
    ("quick revision:", "விரைவு திருப்புதல்:"),
    ("summary:", "சுருக்கம்:"),
    ("explanation:", "விளக்கம்:"),
    ("correct!", "சரியான விடை!"),
    ("incorrect.", "தவறான விடை."),
    ("excellent!", "சிறப்பு!"),
    ("partially correct.", "பகுதி சரி."),
    ("you selected option", "நீங்கள் தேர்ந்தெடுத்த தெரிவு:"),
    ("the correct answer is", "சரியான விடை:")
]

def _translate_rule_based_sentence(sentence: str) -> str:
    """Translates a single sentence with syntactic templates and terminology preservation."""
    s = sentence.strip()
    if not s:
        return s

    # 1. Check exact pattern matches
    for pattern, template in ACADEMIC_SENTENCE_PATTERNS:
        match = pattern.match(s)
        if match:
            return pattern.sub(template, s)

    # 2. Terminology replacement with sorted longest-first order
    working = s
    for en_term, ta_term in sorted(ACADEMIC_STEM_TERMS.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = re.compile(rf'\b{re.escape(en_term)}\b', re.IGNORECASE)
        working = pattern.sub(ta_term, working)

    # 3. Academic connectives replacement
    for en_conn, ta_conn in ACADEMIC_CONNECTIVES:
        pattern = re.compile(rf'\b{re.escape(en_conn)}\b', re.IGNORECASE)
        working = pattern.sub(ta_conn, working)

    return working

def _translate_rule_based(text: str) -> str:
    """Translates multi-sentence or bullet-point text using the academic rule engine."""
    paragraphs = text.split("\n")
    translated_paras = []

    for para in paragraphs:
        if not para.strip():
            translated_paras.append("")
            continue

        # Preserve Markdown headings and bullets
        prefix = ""
        content = para
        match_head = re.match(r'^(#{1,6}\s+|[-*]\s+|\d+\.\s+)', para)
        if match_head:
            prefix = match_head.group(1)
            content = para[len(prefix):]

        sentences = re.split(r'([.?!]+(?:\s+|$))', content)
        translated_chunks = []
        for i in range(0, len(sentences), 2):
            sent = sentences[i]
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            if sent.strip():
                translated_sent = _translate_rule_based_sentence(sent)
                translated_chunks.append(translated_sent + punct)
            else:
                translated_chunks.append(sent + punct)

        translated_paras.append(prefix + "".join(translated_chunks))

    return "\n".join(translated_paras)

def _translate_with_google_free(text: str, source_lang: str = "en", target_lang: str = "ta") -> Optional[str]:
    """
    High-reliability free translation fallback supporting multi-sentence & multi-paragraph educational texts.
    Ensures complete, fluent Tamil translation even if Gemini quota or rate limits are engaged.
    """
    if not text or not text.strip():
        return text

    try:
        import urllib.request
        import urllib.parse
        import json

        paragraphs = text.split("\n")
        translated_paras = []

        for p in paragraphs:
            stripped = p.strip()
            if not stripped:
                translated_paras.append("")
                continue

            encoded_query = urllib.parse.quote(stripped)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={encoded_query}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
                translated_chunks = []
                if payload and isinstance(payload, list) and payload[0]:
                    for segment in payload[0]:
                        if segment and segment[0]:
                            translated_chunks.append(segment[0])
                translated_paras.append("".join(translated_chunks) if translated_chunks else stripped)

        result = "\n".join(translated_paras)
        return result if result.strip() else None
    except Exception as e:
        print(f"[Free Translation Fallback] Error: {e}")
        return None


# -----------------------------------------------------------------------------
# 5. PUBLIC CENTRALIZED MULTILINGUAL TRANSLATION API
# -----------------------------------------------------------------------------

def translate_text(text: str, target_lang: str = "ta", source_lang: str = "en") -> str:
    """
    Centralized translation entrypoint supporting bidirectional English <-> Tamil.
    - Preserves source citations, code blocks, formulas, filenames, and technical terminology.
    - Uses Google Gemini (gemini-3.5-flash-lite) as primary official translation provider.
    - Free Cloud Translation Fallback ensures complete translation upon API quota or rate limits.
    - High-fidelity academic rule engine & concept glossaries as secondary fallback.
    - In-memory caching for performance.
    """
    if not text:
        return text

    tgt = "ta" if target_lang in ["ta", "tamil", "ta-IN"] else "en"
    src = "ta" if source_lang in ["ta", "tamil", "ta-IN"] else "en"

    if tgt == src:
        return text

    # Avoid translating text that is already in the requested language
    if tgt == "ta" and is_tamil(text) and not re.search(r'[a-zA-Z]{4,}', text):
        return text
    if tgt == "en" and not is_tamil(text):
        return text

    cache_key = f"{src}_{tgt}_{hash(text)}"
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]

    # 1. Protect code, math equations, citations, and filenames
    protected_text, protected_tokens = protect_literals(text)

    # 2. Priority 1: Official Google Gemini AI Translation
    translated = None
    if GEMINI_API_KEY and not _is_quota_cooldown_active():
        translated = _translate_with_gemini(protected_text, source_lang=src, target_lang=tgt)

    # 3. Priority 2: High-reliability Free Cloud Translation Fallback (Zero Quota Limits)
    if not translated:
        translated = _translate_with_google_free(protected_text, source_lang=src, target_lang=tgt)

    # 4. Priority 3: High-fidelity rule-based & concept normalization fallback
    if not translated:
        if tgt == "ta":
            translated = _translate_rule_based(protected_text)
        elif tgt == "en":
            translated = normalize_tamil_to_concept(protected_text)

    # 5. Restore untouched citations and code
    final_output = restore_literals(translated or text, protected_tokens)

    # 6. Cache result
    _TRANSLATION_CACHE[cache_key] = final_output
    return final_output


def is_tamil(text: str) -> bool:
    """Returns True if the input text contains Tamil Unicode characters."""
    if not text:
        return False
    return bool(re.search(r'[\u0b80-\u0bff]', text))


def normalize_tamil_to_concept(text: str) -> str:
    """
    Maps student answers containing Tamil or Tanglish words back to standard
    English concepts for accurate assessment against course evidence.
    """
    if not text:
        return ""
    result = text
    for ta_term, en_concept in TAMIL_TO_CONCEPT_MAP.items():
        result = result.replace(ta_term, en_concept)
    return result


def format_multilingual_feedback(feedback_en: str, language: str = "en") -> str:
    """Formats assessment feedback in the student's selected language."""
    if not feedback_en or language not in ["ta", "tamil"]:
        return feedback_en
    return translate_text(feedback_en, target_lang="ta")
