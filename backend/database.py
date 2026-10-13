import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from config import DB_PATH
import mongodb_service

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        organisation TEXT DEFAULT '',
        org_type TEXT DEFAULT 'College',
        department TEXT DEFAULT '',
        role_year TEXT DEFAULT '',
        preferred_language TEXT DEFAULT 'en',
        profile_picture TEXT DEFAULT '',
        reset_token TEXT,
        reset_token_expiry TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )
    """)
    
    # Textbooks & Materials table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS textbooks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        source_type TEXT DEFAULT 'pdf',
        total_pages INTEGER NOT NULL,
        total_slides INTEGER,
        duration_seconds REAL,
        duration_str TEXT,
        file_size_bytes INTEGER NOT NULL,
        extracted_images_count INTEGER DEFAULT 0,
        extracted_transcripts_count INTEGER DEFAULT 0,
        extracted_tables_count INTEGER DEFAULT 0,
        media_json TEXT,
        chapters_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    # Chunks table (for unified knowledge base, RAG & grounding)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        textbook_id TEXT NOT NULL,
        material_id TEXT,
        source_type TEXT DEFAULT 'pdf',
        filename TEXT,
        chapter_id TEXT NOT NULL,
        chapter_title TEXT NOT NULL,
        section_id TEXT NOT NULL,
        section_title TEXT NOT NULL,
        page INTEGER NOT NULL,
        slide_number INTEGER,
        start_time REAL,
        end_time REAL,
        timestamp_str TEXT,
        content_type TEXT DEFAULT 'text',
        content TEXT NOT NULL,
        media_path TEXT,
        extra_metadata_json TEXT,
        FOREIGN KEY (textbook_id) REFERENCES textbooks(id)
    )
    """)

    # Media items table (embedded images, diagrams, video keyframes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_items (
        id TEXT PRIMARY KEY,
        file_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        source_type TEXT NOT NULL,
        content_type TEXT NOT NULL,
        page INTEGER,
        slide INTEGER,
        timestamp TEXT,
        media_path TEXT NOT NULL,
        media_filename TEXT,
        width INTEGER,
        height INTEGER,
        format TEXT,
        description TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Quiz History table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_history (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        textbook_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        total_questions INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        score_percentage REAL NOT NULL,
        results_json TEXT NOT NULL,
        taken_at TEXT NOT NULL
    )
    """)
    
    # Topic Mastery table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topic_mastery (
        user_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        total_attempts INTEGER DEFAULT 0,
        correct_attempts INTEGER DEFAULT 0,
        mastery_percentage REAL DEFAULT 0.0,
        last_updated TEXT NOT NULL,
        PRIMARY KEY (user_id, topic)
    )
    """)
    
    # Concepts table (Innovation 2)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS concepts (
        id TEXT PRIMARY KEY,
        course_id TEXT NOT NULL,
        name TEXT NOT NULL,
        topic TEXT NOT NULL,
        subtopic TEXT,
        description TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Concept Sources table (Innovation 2: Multimodal Provenance)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS concept_sources (
        id TEXT PRIMARY KEY,
        concept_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        content_unit_id TEXT,
        source_type TEXT NOT NULL,
        filename TEXT,
        page_number INTEGER,
        slide_number INTEGER,
        start_time REAL,
        end_time REAL,
        timestamp_str TEXT,
        excerpt TEXT,
        media_path TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
    )
    """)

    # Concept Relationships table (Innovation 2: Prerequisites & Semantic Graph)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS concept_relationships (
        id TEXT PRIMARY KEY,
        course_id TEXT NOT NULL,
        source_concept_id TEXT NOT NULL,
        target_concept_id TEXT NOT NULL,
        source_concept_name TEXT NOT NULL,
        target_concept_name TEXT NOT NULL,
        relationship_type TEXT NOT NULL,
        confidence REAL DEFAULT 1.0,
        evidence TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (source_concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
        FOREIGN KEY (target_concept_id) REFERENCES concepts(id) ON DELETE CASCADE
    )
    """)

    # --- Innovation 4: Assessment, Misconceptions & Adaptive Practice Tables ---
    # Assessment Questions table (dynamic evidence-grounded questions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_questions (
        id TEXT PRIMARY KEY,
        course_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        concept_id TEXT,
        concept_name TEXT,
        difficulty TEXT NOT NULL,
        question_type TEXT NOT NULL,
        question TEXT NOT NULL,
        options_json TEXT,
        correct_key TEXT,
        expected_answer TEXT,
        acceptable_terms_json TEXT,
        numerical_value REAL,
        numerical_tolerance REAL,
        explanation TEXT NOT NULL,
        source_citation_json TEXT NOT NULL,
        source_chunk_id TEXT,
        prerequisite_concept TEXT,
        question_hash TEXT UNIQUE,
        created_at TEXT NOT NULL
    )
    """)

    # Student Assessment Attempts table (detailed submission evaluations & scores)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_attempts (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        question_text TEXT NOT NULL,
        topic TEXT NOT NULL,
        concept_name TEXT,
        question_type TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        student_answer TEXT NOT NULL,
        is_correct INTEGER NOT NULL,
        score REAL NOT NULL,
        evaluation_status TEXT NOT NULL,
        feedback TEXT NOT NULL,
        misconception_json TEXT,
        source_citation_json TEXT,
        clarifying_answer TEXT,
        taken_at TEXT NOT NULL
    )
    """)

    # Misconception Profiles table (tracks diagnostic hypotheses & resolution)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS misconception_profiles (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        concept_name TEXT NOT NULL,
        topic TEXT NOT NULL,
        misconception_title TEXT NOT NULL,
        hypothesis_text TEXT NOT NULL,
        expected_understanding TEXT NOT NULL,
        confidence TEXT NOT NULL,
        occurrence_count INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        clarifying_question TEXT,
        evidence_excerpt TEXT,
        last_detected_at TEXT NOT NULL,
        UNIQUE(user_id, course_id, concept_name, misconception_title)
    )
    """)

    # Innovation 5: Student Concept Study Progress table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_concept_progress (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        course_id TEXT NOT NULL,
        concept_id TEXT NOT NULL,
        concept_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'studied',
        notes TEXT,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, course_id, concept_id)
    )
    """)
    
    # Schema migration helper for existing databases
    existing_user_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
    new_user_cols = [
        ("organisation", "TEXT DEFAULT ''"),
        ("org_type", "TEXT DEFAULT 'College'"),
        ("department", "TEXT DEFAULT ''"),
        ("role_year", "TEXT DEFAULT ''"),
        ("preferred_language", "TEXT DEFAULT 'en'"),
        ("profile_picture", "TEXT DEFAULT ''"),
        ("reset_token", "TEXT"),
        ("reset_token_expiry", "TEXT"),
        ("updated_at", "TEXT")
    ]
    for col_name, col_type in new_user_cols:
        if col_name not in existing_user_cols:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    existing_tb_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(textbooks)").fetchall()]
    new_tb_cols = [
        ("source_type", "TEXT DEFAULT 'pdf'"),
        ("total_slides", "INTEGER"),
        ("duration_seconds", "REAL"),
        ("duration_str", "TEXT"),
        ("extracted_images_count", "INTEGER DEFAULT 0"),
        ("extracted_transcripts_count", "INTEGER DEFAULT 0"),
        ("extracted_tables_count", "INTEGER DEFAULT 0"),
        ("media_json", "TEXT"),
        ("user_id", "TEXT DEFAULT 'system'")
    ]
    for col_name, col_type in new_tb_cols:
        if col_name not in existing_tb_cols:
            try:
                cursor.execute(f"ALTER TABLE textbooks ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    existing_chk_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(chunks)").fetchall()]
    new_chk_cols = [
        ("material_id", "TEXT"),
        ("source_type", "TEXT DEFAULT 'pdf'"),
        ("filename", "TEXT"),
        ("slide_number", "INTEGER"),
        ("start_time", "REAL"),
        ("end_time", "REAL"),
        ("timestamp_str", "TEXT"),
        ("content_type", "TEXT DEFAULT 'text'"),
        ("media_path", "TEXT"),
        ("extra_metadata_json", "TEXT")
    ]
    for col_name, col_type in new_chk_cols:
        if col_name not in existing_chk_cols:
            try:
                cursor.execute(f"ALTER TABLE chunks ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    conn.commit()
    conn.close()

# Database helper functions
def save_textbook(metadata_dict: Dict[str, Any], chunks: List[Dict[str, Any]], media_items: Optional[List[Dict[str, Any]]] = None):
    try:
        if mongodb_service.is_mongo_available():
            mongodb_service.save_textbook_mongo(metadata_dict, chunks, media_items)
    except Exception as e:
        print(f"[MongoDB] save_textbook notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT OR REPLACE INTO textbooks (
        id, title, filename, source_type, total_pages, total_slides, duration_seconds, duration_str,
        file_size_bytes, extracted_images_count, extracted_transcripts_count, extracted_tables_count,
        media_json, chapters_json, created_at, user_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        metadata_dict["id"],
        metadata_dict["title"],
        metadata_dict["filename"],
        metadata_dict.get("source_type", "pdf"),
        metadata_dict.get("total_pages", len(chunks)),
        metadata_dict.get("total_slides"),
        metadata_dict.get("duration_seconds"),
        metadata_dict.get("duration_str"),
        metadata_dict["file_size_bytes"],
        metadata_dict.get("extracted_images_count", 0),
        metadata_dict.get("extracted_transcripts_count", 0),
        metadata_dict.get("extracted_tables_count", 0),
        json.dumps(metadata_dict.get("media_items", media_items or [])),
        json.dumps(metadata_dict["chapters"]),
        datetime.now().isoformat() if (not metadata_dict.get("created_at") or str(metadata_dict.get("created_at")).startswith("D:")) else metadata_dict.get("created_at"),
        metadata_dict.get("user_id", "system")
    ))
    
    # Remove old chunks for this textbook if any
    cursor.execute("DELETE FROM chunks WHERE textbook_id = ?", (metadata_dict["id"],))
    
    # Insert chunks with full provenance
    for chunk in chunks:
        extra_meta = chunk.get("metadata", {})
        cursor.execute("""
        INSERT OR REPLACE INTO chunks (
            id, textbook_id, material_id, source_type, filename, chapter_id, chapter_title,
            section_id, section_title, page, slide_number, start_time, end_time, timestamp_str,
            content_type, content, media_path, extra_metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk["id"],
            chunk.get("textbook_id", metadata_dict["id"]),
            chunk.get("material_id", metadata_dict["id"]),
            chunk.get("source_type", metadata_dict.get("source_type", "pdf")),
            chunk.get("filename", metadata_dict["filename"]),
            chunk["chapter_id"],
            chunk["chapter_title"],
            chunk["section_id"],
            chunk["section_title"],
            chunk.get("page", 1),
            chunk.get("slide_number"),
            chunk.get("start_time"),
            chunk.get("end_time"),
            chunk.get("timestamp_str"),
            chunk.get("content_type", "text"),
            chunk["content"],
            chunk.get("media_path"),
            json.dumps(extra_meta) if extra_meta else None
        ))

    # Save media items if provided
    items_to_save = media_items or metadata_dict.get("media_items", [])
    if items_to_save:
        cursor.execute("DELETE FROM media_items WHERE file_id = ?", (metadata_dict["id"],))
        for m in items_to_save:
            cursor.execute("""
            INSERT OR REPLACE INTO media_items (
                id, file_id, filename, source_type, content_type, page, slide, timestamp,
                media_path, media_filename, width, height, format, description, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                m["id"],
                m.get("file_id", metadata_dict["id"]),
                m.get("filename", metadata_dict["filename"]),
                m.get("source_type", "pdf"),
                m.get("content_type", "image"),
                m.get("page"),
                m.get("slide"),
                m.get("timestamp"),
                m["media_path"],
                m.get("media_filename"),
                m.get("width"),
                m.get("height"),
                m.get("format"),
                m.get("description"),
                datetime.now().isoformat()
            ))
    
    conn.commit()
    conn.close()

def get_textbook(textbook_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM textbooks WHERE id = ?", (textbook_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        r_dict = dict(row)
        return {
            "id": r_dict["id"],
            "title": r_dict["title"],
            "filename": r_dict["filename"],
            "source_type": r_dict.get("source_type", "pdf"),
            "total_pages": r_dict["total_pages"],
            "total_slides": r_dict.get("total_slides"),
            "duration_seconds": r_dict.get("duration_seconds"),
            "duration_str": r_dict.get("duration_str"),
            "file_size_bytes": r_dict["file_size_bytes"],
            "extracted_images_count": r_dict.get("extracted_images_count", 0),
            "extracted_transcripts_count": r_dict.get("extracted_transcripts_count", 0),
            "extracted_tables_count": r_dict.get("extracted_tables_count", 0),
            "media_items": json.loads(r_dict["media_json"]) if r_dict.get("media_json") else [],
            "chapters": json.loads(r_dict["chapters_json"]),
            "created_at": r_dict["created_at"],
            "user_id": r_dict.get("user_id", "system")
        }

    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_textbook_mongo(textbook_id)
            if mongo_res:
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_textbook notice: {e}")

    return None

def get_all_textbooks(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM textbooks WHERE user_id = ? OR user_id = 'system' OR user_id IS NULL OR user_id = '' ORDER BY created_at DESC", (user_id,))
    else:
        cursor.execute("SELECT * FROM textbooks ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    if rows:
        textbooks = []
        for row in rows:
            r_dict = dict(row)
            textbooks.append({
                "id": r_dict["id"],
                "title": r_dict["title"],
                "filename": r_dict["filename"],
                "source_type": r_dict.get("source_type", "pdf"),
                "total_pages": r_dict["total_pages"],
                "total_slides": r_dict.get("total_slides"),
                "duration_seconds": r_dict.get("duration_seconds"),
                "duration_str": r_dict.get("duration_str"),
                "file_size_bytes": r_dict["file_size_bytes"],
                "extracted_images_count": r_dict.get("extracted_images_count", 0),
                "extracted_transcripts_count": r_dict.get("extracted_transcripts_count", 0),
                "extracted_tables_count": r_dict.get("extracted_tables_count", 0),
                "media_items": json.loads(r_dict["media_json"]) if r_dict.get("media_json") else [],
                "chapters": json.loads(r_dict["chapters_json"]),
                "created_at": r_dict["created_at"],
                "user_id": r_dict.get("user_id", "system")
            })
        return textbooks

    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_all_textbooks_mongo()
            if mongo_res is not None and len(mongo_res) > 0:
                if user_id:
                    return [tb for tb in mongo_res if tb.get("user_id") in (user_id, "system", None, "")]
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_all_textbooks notice: {e}")

    return []

def delete_textbook(textbook_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a specific textbook and all associated chunks, media items, concepts,
    prerequisites, adaptive paths, and quiz history.
    If user_id is provided, verifies ownership or allowed shared deletion.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM textbooks WHERE id = ?", (textbook_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        tb_owner = row[0] if row else None
        if user_id and tb_owner and tb_owner not in (user_id, "system", ""):
            conn.close()
            return False

        with conn:
            cursor.execute("DELETE FROM chunks WHERE textbook_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM media_items WHERE file_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM quiz_history WHERE textbook_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM concept_sources WHERE course_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM concept_relationships WHERE course_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM concepts WHERE course_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM assessment_questions WHERE course_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM assessment_attempts WHERE course_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM misconception_profiles WHERE course_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM user_concept_progress WHERE course_id = ?", (textbook_id,))
            cursor.execute("DELETE FROM textbooks WHERE id = ?", (textbook_id,))
            
        conn.close()
    except Exception as e:
        print(f"[delete_textbook error]: {e}")
        return False

    try:
        if mongodb_service.is_mongo_available():
            db = mongodb_service.get_mongo_db()
            if db is not None:
                db["textbooks"].delete_one({"id": textbook_id})
                db["chunks"].delete_many({"textbook_id": textbook_id})
    except Exception as e:
        print(f"[MongoDB] delete_textbook notice: {e}")
        
    return True

def clear_all_textbooks(user_id: Optional[str] = None) -> int:
    """
    Clear all textbooks for the given user_id (or all textbooks if user_id is None).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("SELECT id FROM textbooks WHERE user_id = ? OR user_id = 'system' OR user_id IS NULL OR user_id = ''", (user_id,))
        else:
            cursor.execute("SELECT id FROM textbooks")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"[clear_all_textbooks select error]: {e}")
        return 0
    
    count = 0
    for r in rows:
        tb_id = dict(r)["id"]
        if delete_textbook(tb_id, user_id):
            count += 1
            
    return count

def get_chunks_for_textbook(textbook_id: str, chapter_id: Optional[str] = None, section_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM chunks WHERE textbook_id = ?"
    params = [textbook_id]
    
    if chapter_id:
        query += " AND chapter_id = ?"
        params.append(chapter_id)
    if section_id:
        query += " AND section_id = ?"
        params.append(section_id)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        chunks = []
        for row in rows:
            c = dict(row)
            if c.get("extra_metadata_json"):
                try:
                    c["metadata"] = json.loads(c["extra_metadata_json"])
                except Exception:
                    c["metadata"] = {}
            chunks.append(c)
        return chunks

    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_chunks_for_textbook_mongo(textbook_id, chapter_id, section_id)
            if mongo_res is not None and len(mongo_res) > 0:
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_chunks_for_textbook notice: {e}")

    return []

def get_media_for_textbook(textbook_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM media_items WHERE file_id = ? ORDER BY page ASC, slide ASC", (textbook_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return [dict(r) for r in rows]

    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_media_for_textbook_mongo(textbook_id)
            if mongo_res is not None and len(mongo_res) > 0:
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_media_for_textbook notice: {e}")

    return []

def record_quiz_result(user_id: str, textbook_id: str, topic: str, difficulty: str, total_q: int, correct_q: int, score_pct: float, results: List[Dict[str, Any]], topic_breakdown: List[Dict[str, Any]]):
    try:
        if mongodb_service.is_mongo_available():
            tb_norm = [{"topic": tb["topic"], "total": tb.get("total_questions", tb.get("total", 0)), "correct": tb.get("correct_questions", tb.get("correct", 0))} for tb in topic_breakdown]
            mongodb_service.record_quiz_result_mongo(user_id, textbook_id, topic, difficulty, total_q, correct_q, score_pct, results, tb_norm)
    except Exception as e:
        print(f"[MongoDB] record_quiz_result notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    quiz_id = f"quiz_{int(datetime.now().timestamp())}"
    now_iso = datetime.now().isoformat()
    
    cursor.execute("""
    INSERT INTO quiz_history (id, user_id, textbook_id, topic, difficulty, total_questions, correct_count, score_percentage, results_json, taken_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        quiz_id,
        user_id,
        textbook_id,
        topic,
        difficulty,
        total_q,
        correct_q,
        score_pct,
        json.dumps(results),
        now_iso
    ))
    
    # Update topic mastery table
    for tb in topic_breakdown:
        t_name = tb["topic"]
        t_total = tb["total_questions"]
        t_correct = tb["correct_questions"]
        
        cursor.execute("SELECT total_attempts, correct_attempts FROM topic_mastery WHERE user_id = ? AND topic = ?", (user_id, t_name))
        row = cursor.fetchone()
        if row:
            new_total = row["total_attempts"] + t_total
            new_correct = row["correct_attempts"] + t_correct
            new_pct = round((new_correct / new_total) * 100, 1) if new_total > 0 else 0
            cursor.execute("""
            UPDATE topic_mastery SET total_attempts = ?, correct_attempts = ?, mastery_percentage = ?, last_updated = ?
            WHERE user_id = ? AND topic = ?
            """, (new_total, new_correct, new_pct, now_iso, user_id, t_name))
        else:
            pct = round((t_correct / t_total) * 100, 1) if t_total > 0 else 0
            cursor.execute("""
            INSERT INTO topic_mastery (user_id, topic, total_attempts, correct_attempts, mastery_percentage, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, t_name, t_total, t_correct, pct, now_iso))
            
    conn.commit()
    conn.close()

def _normalize_performance_data(perf: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not perf:
        perf = {}
    
    quizzes_completed = int(perf.get("quizzes_completed", perf.get("total_quizzes", 0)))
    questions_answered = int(perf.get("questions_answered", 0))
    acc_pct = float(perf.get("accuracy_percentage", perf.get("average_score", 0.0)))
    
    topic_masteries = []
    raw_masteries = perf.get("topic_masteries") or perf.get("topic_mastery") or []
    for m in raw_masteries:
        if isinstance(m, dict):
            pct = float(m.get("mastery_percentage", 0.0))
            status = m.get("status") or ("Strong" if pct >= 75.0 else ("Moderate" if pct >= 60.0 else "Weak"))
            topic_masteries.append({
                "topic": str(m.get("topic", "General")),
                "mastery_percentage": pct,
                "quizzes_taken": int(m.get("quizzes_taken", m.get("total_attempts", 0))),
                "status": status,
                "last_practiced": str(m.get("last_practiced") or m.get("last_updated") or "")
            })
            
    strong_topics = list(perf.get("strong_topics") or [t["topic"] for t in topic_masteries if t["mastery_percentage"] >= 75.0])
    weak_topics = list(perf.get("weak_topics") or [t["topic"] for t in topic_masteries if t["mastery_percentage"] < 60.0])
    
    overall_progress = float(perf.get("overall_progress", round(sum(t["mastery_percentage"] for t in topic_masteries) / len(topic_masteries), 1) if topic_masteries else 72.0))
    
    recent_activity = []
    raw_activity = perf.get("recent_activity") or perf.get("quiz_history") or []
    for r in raw_activity:
        if isinstance(r, dict):
            recent_activity.append({
                "quiz_id": str(r.get("quiz_id") or r.get("id") or "quiz"),
                "topic": str(r.get("topic", "General")),
                "difficulty": str(r.get("difficulty", "Medium")),
                "score_percentage": float(r.get("score_percentage", 0.0)),
                "taken_at": str(r.get("taken_at", ""))
            })
            
    if not topic_masteries:
        topic_masteries = [
            {"topic": "Introduction & Relational Model", "mastery_percentage": 90.0, "quizzes_taken": 4, "status": "Strong", "last_practiced": "2026-09-14T10:00:00"},
            {"topic": "Database Keys & Constraints", "mastery_percentage": 85.0, "quizzes_taken": 3, "status": "Strong", "last_practiced": "2026-09-14T11:30:00"},
            {"topic": "First Normal Form (1NF)", "mastery_percentage": 80.0, "quizzes_taken": 3, "status": "Strong", "last_practiced": "2026-09-15T09:15:00"},
            {"topic": "Second Normal Form (2NF)", "mastery_percentage": 40.0, "quizzes_taken": 2, "status": "Weak", "last_practiced": "2026-09-15T15:20:00"},
            {"topic": "Third Normal Form (3NF)", "mastery_percentage": 55.0, "quizzes_taken": 2, "status": "Weak", "last_practiced": "2026-09-15T16:00:00"},
            {"topic": "Transactions & ACID Properties", "mastery_percentage": 78.0, "quizzes_taken": 3, "status": "Strong", "last_practiced": "2026-09-15T18:00:00"}
        ]
        strong_topics = ["Introduction & Relational Model", "Database Keys & Constraints", "First Normal Form (1NF)", "Transactions & ACID Properties"]
        weak_topics = ["Second Normal Form (2NF)", "Third Normal Form (3NF)"]
        if questions_answered == 0:
            questions_answered = 25
        if quizzes_completed == 0:
            quizzes_completed = 3
        if acc_pct == 0.0:
            acc_pct = 72.0

    if not recent_activity:
        recent_activity = [
            {"quiz_id": "quiz_demo_1", "topic": "Second Normal Form (2NF)", "difficulty": "Medium", "score_percentage": 40.0, "taken_at": "Today, 3:20 PM"},
            {"quiz_id": "quiz_demo_2", "topic": "Database Keys & Constraints", "difficulty": "Easy", "score_percentage": 100.0, "taken_at": "Today, 11:30 AM"},
            {"quiz_id": "quiz_demo_3", "topic": "First Normal Form (1NF)", "difficulty": "Medium", "score_percentage": 80.0, "taken_at": "Today, 9:15 AM"}
        ]

    return {
        "overall_progress": overall_progress,
        "quizzes_completed": quizzes_completed,
        "questions_answered": questions_answered,
        "accuracy_percentage": acc_pct,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "topic_masteries": topic_masteries,
        "recent_activity": recent_activity,
        "total_quizzes": quizzes_completed,
        "average_score": acc_pct,
        "topic_mastery": topic_masteries,
        "quiz_history": recent_activity
    }

def get_user_performance(user_id: str = "demo_user") -> Dict[str, Any]:
    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_user_performance_mongo(user_id)
            if mongo_res is not None:
                return _normalize_performance_data(mongo_res)
    except Exception as e:
        print(f"[MongoDB] get_user_performance notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch all mastery records
    cursor.execute("SELECT * FROM topic_mastery WHERE user_id = ?", (user_id,))
    mastery_rows = cursor.fetchall()
    
    # Fetch quiz history
    cursor.execute("SELECT * FROM quiz_history WHERE user_id = ? ORDER BY taken_at DESC LIMIT 10", (user_id,))
    history_rows = cursor.fetchall()
    conn.close()
    
    topic_masteries = []
    strong_topics = []
    weak_topics = []
    
    total_answered = 0
    total_correct = 0
    
    for row in mastery_rows:
        pct = row["mastery_percentage"]
        status = "Strong" if pct >= 75 else ("Moderate" if pct >= 60 else "Weak")
        t_obj = {
            "topic": row["topic"],
            "mastery_percentage": pct,
            "quizzes_taken": row["total_attempts"],
            "status": status,
            "last_practiced": row["last_updated"]
        }
        topic_masteries.append(t_obj)
        if pct >= 75:
            strong_topics.append(row["topic"])
        elif pct < 60:
            weak_topics.append(row["topic"])
            
        total_answered += row["total_attempts"]
        total_correct += row["correct_attempts"]
        
    # Default demo state if no history exists yet
    if not topic_masteries:
        topic_masteries = [
            {"topic": "Introduction & Relational Model", "mastery_percentage": 90.0, "quizzes_taken": 4, "status": "Strong", "last_practiced": "2026-09-14T10:00:00"},
            {"topic": "Database Keys & Constraints", "mastery_percentage": 85.0, "quizzes_taken": 3, "status": "Strong", "last_practiced": "2026-09-14T11:30:00"},
            {"topic": "First Normal Form (1NF)", "mastery_percentage": 80.0, "quizzes_taken": 3, "status": "Strong", "last_practiced": "2026-09-15T09:15:00"},
            {"topic": "Second Normal Form (2NF)", "mastery_percentage": 40.0, "quizzes_taken": 2, "status": "Weak", "last_practiced": "2026-09-15T15:20:00"},
            {"topic": "Third Normal Form (3NF)", "mastery_percentage": 55.0, "quizzes_taken": 2, "status": "Weak", "last_practiced": "2026-09-15T16:00:00"},
            {"topic": "Transactions & ACID Properties", "mastery_percentage": 78.0, "quizzes_taken": 3, "status": "Strong", "last_practiced": "2026-09-15T18:00:00"}
        ]
        strong_topics = ["Introduction & Relational Model", "Database Keys & Constraints", "First Normal Form (1NF)", "Transactions & ACID Properties"]
        weak_topics = ["Second Normal Form (2NF)", "Third Normal Form (3NF)"]
        total_answered = 25
        total_correct = 18

    acc_pct = round((total_correct / total_answered) * 100, 1) if total_answered > 0 else 72.0
    overall_progress = round(sum(t["mastery_percentage"] for t in topic_masteries) / len(topic_masteries), 1) if topic_masteries else 72.0

    recent_activity = []
    for r in history_rows:
        recent_activity.append({
            "quiz_id": r["id"],
            "topic": r["topic"],
            "difficulty": r["difficulty"],
            "score_percentage": r["score_percentage"],
            "taken_at": r["taken_at"]
        })
        
    if not recent_activity:
        recent_activity = [
            {"quiz_id": "quiz_demo_1", "topic": "Second Normal Form (2NF)", "difficulty": "Medium", "score_percentage": 40.0, "taken_at": "Today, 3:20 PM"},
            {"quiz_id": "quiz_demo_2", "topic": "Database Keys & Constraints", "difficulty": "Easy", "score_percentage": 100.0, "taken_at": "Today, 11:30 AM"},
            {"quiz_id": "quiz_demo_3", "topic": "First Normal Form (1NF)", "difficulty": "Medium", "score_percentage": 80.0, "taken_at": "Today, 9:15 AM"}
        ]

    return _normalize_performance_data({
        "overall_progress": overall_progress,
        "quizzes_completed": len(history_rows) if history_rows else 3,
        "questions_answered": total_answered,
        "accuracy_percentage": acc_pct,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "topic_masteries": topic_masteries,
        "recent_activity": recent_activity
    })

# --- Innovation 2: Concept and Prerequisite Graph Database Functions ---

def save_concept_graph(
    course_id: str,
    concepts: List[Dict[str, Any]],
    sources: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]]
):
    """
    Persists the dynamically generated concept graph, sources, and relationships
    for a course or textbook into the database.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongodb_service.save_concept_graph_mongo(course_id, concepts, relationships, sources)
    except Exception as e:
        print(f"[MongoDB] save_concept_graph notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()

    # Clear previous graph for this course
    cursor.execute("DELETE FROM concept_relationships WHERE course_id = ?", (course_id,))
    cursor.execute("DELETE FROM concept_sources WHERE course_id = ?", (course_id,))
    cursor.execute("DELETE FROM concepts WHERE course_id = ?", (course_id,))

    # Insert Concepts
    for c in concepts:
        cursor.execute("""
        INSERT OR REPLACE INTO concepts (
            id, course_id, name, topic, subtopic, description, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            c["id"],
            course_id,
            c["name"],
            c.get("topic", "General"),
            c.get("subtopic", ""),
            c.get("description", ""),
            c.get("created_at", now_iso)
        ))

    # Insert Concept Sources (Multimodal Provenance)
    for s in sources:
        cursor.execute("""
        INSERT OR REPLACE INTO concept_sources (
            id, concept_id, course_id, content_unit_id, source_type, filename,
            page_number, slide_number, start_time, end_time, timestamp_str,
            excerpt, media_path, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s["id"],
            s["concept_id"],
            course_id,
            s.get("content_unit_id"),
            s.get("source_type", "pdf"),
            s.get("filename"),
            s.get("page_number"),
            s.get("slide_number"),
            s.get("start_time"),
            s.get("end_time"),
            s.get("timestamp_str"),
            s.get("excerpt", ""),
            s.get("media_path"),
            s.get("created_at", now_iso)
        ))

    # Insert Concept Relationships & Prerequisites
    for r in relationships:
        cursor.execute("""
        INSERT OR REPLACE INTO concept_relationships (
            id, course_id, source_concept_id, target_concept_id,
            source_concept_name, target_concept_name, relationship_type,
            confidence, evidence, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["id"],
            course_id,
            r["source_concept_id"],
            r["target_concept_id"],
            r.get("source_concept_name", ""),
            r.get("target_concept_name", ""),
            r.get("relationship_type", "related_to"),
            r.get("confidence", 1.0),
            r.get("evidence", ""),
            r.get("created_at", now_iso)
        ))

    conn.commit()
    conn.close()

def get_concept_graph(course_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the full concept graph (nodes, edges, sources, topics) for a course.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM concepts WHERE course_id = ? ORDER BY topic ASC, name ASC", (course_id,))
    concept_rows = cursor.fetchall()
    if not concept_rows:
        conn.close()
        return None

    cursor.execute("SELECT * FROM concept_sources WHERE course_id = ? ORDER BY page_number ASC, slide_number ASC, start_time ASC", (course_id,))
    source_rows = cursor.fetchall()

    cursor.execute("SELECT * FROM concept_relationships WHERE course_id = ?", (course_id,))
    rel_rows = cursor.fetchall()

    conn.close()

    # Map sources by concept_id
    sources_by_concept = {}
    for s in source_rows:
        s_dict = dict(s)
        c_id = s_dict["concept_id"]
        if c_id not in sources_by_concept:
            sources_by_concept[c_id] = []
        sources_by_concept[c_id].append(s_dict)

    # Build nodes
    nodes = []
    topics_set = set()
    topic_counts = {}

    for c in concept_rows:
        c_dict = dict(c)
        c_id = c_dict["id"]
        c_topic = c_dict.get("topic", "General")
        topics_set.add(c_topic)
        topic_counts[c_topic] = topic_counts.get(c_topic, 0) + 1

        c_sources = sources_by_concept.get(c_id, [])
        source_types = list(set([s.get("source_type") for s in c_sources if s.get("source_type")]))
        
        nodes.append({
            "id": c_id,
            "name": c_dict["name"],
            "topic": c_topic,
            "subtopic": c_dict.get("subtopic", ""),
            "description": c_dict.get("description", ""),
            "sources": c_sources,
            "source_types": source_types,
            "cross_modal_count": len(source_types),
            "prerequisites": [],
            "dependents": []
        })

    # Build edges and enrich nodes with prereqs / dependents
    node_map = {n["id"]: n for n in nodes}
    edges = []
    prereq_count = 0
    cross_modal_count = sum(1 for n in nodes if len(n["source_types"]) > 1)

    for r in rel_rows:
        r_dict = dict(r)
        src_id = r_dict["source_concept_id"]
        tgt_id = r_dict["target_concept_id"]
        rel_type = r_dict.get("relationship_type", "related_to")

        edges.append({
            "id": r_dict["id"],
            "source": src_id,
            "target": tgt_id,
            "source_concept_id": src_id,
            "target_concept_id": tgt_id,
            "source_concept_name": r_dict["source_concept_name"],
            "target_concept_name": r_dict["target_concept_name"],
            "relationship_type": rel_type,
            "confidence": r_dict["confidence"],
            "evidence": r_dict["evidence"]
        })

        if rel_type == "prerequisite":
            prereq_count += 1
            if src_id in node_map:
                node_map[src_id]["dependents"].append(r_dict["target_concept_name"])
            if tgt_id in node_map:
                node_map[tgt_id]["prerequisites"].append(r_dict["source_concept_name"])

    # Extract distinct topics
    topics_list = [{"name": t, "count": topic_counts[t]} for t in sorted(list(topics_set))]

    return {
        "course_id": course_id,
        "nodes": nodes,
        "edges": edges,
        "topics": topics_list,
        "stats": {
            "total_concepts": len(nodes),
            "total_relationships": len(edges),
            "total_prerequisites": prereq_count,
            "total_sources": len(source_rows),
            "cross_modal_concepts": cross_modal_count,
            "total_topics": len(topics_list)
        }
    }

def get_concept_details(course_id: str, concept_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns granular information for a single concept including all its sources,
    prerequisites, dependent concepts, and related concepts with evidence.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM concepts WHERE course_id = ? AND id = ?", (course_id, concept_id))
    concept_row = cursor.fetchone()
    if not concept_row:
        conn.close()
        return None

    c_dict = dict(concept_row)

    cursor.execute("SELECT * FROM concept_sources WHERE course_id = ? AND concept_id = ? ORDER BY page_number ASC, slide_number ASC, start_time ASC", (course_id, concept_id))
    source_rows = [dict(r) for r in cursor.fetchall()]

    # Prerequisites (where this concept is target and relationship is prerequisite)
    cursor.execute("""
    SELECT * FROM concept_relationships 
    WHERE course_id = ? AND target_concept_id = ? AND relationship_type = 'prerequisite'
    """, (course_id, concept_id))
    prereq_rows = [dict(r) for r in cursor.fetchall()]

    # Dependents (where this concept is source and relationship is prerequisite)
    cursor.execute("""
    SELECT * FROM concept_relationships 
    WHERE course_id = ? AND source_concept_id = ? AND relationship_type = 'prerequisite'
    """, (course_id, concept_id))
    dependent_rows = [dict(r) for r in cursor.fetchall()]

    # Other Related concepts
    cursor.execute("""
    SELECT * FROM concept_relationships 
    WHERE course_id = ? AND (source_concept_id = ? OR target_concept_id = ?) AND relationship_type != 'prerequisite'
    """, (course_id, concept_id, concept_id))
    related_rows = [dict(r) for r in cursor.fetchall()]

    conn.close()

    source_types = list(set([s.get("source_type") for s in source_rows if s.get("source_type")]))

    return {
        "concept": {
            **c_dict,
            "sources": source_rows,
            "source_types": source_types,
            "cross_modal_count": len(source_types)
        },
        "prerequisites": [{
            "concept_id": r["source_concept_id"],
            "name": r["source_concept_name"],
            "evidence": r["evidence"],
            "confidence": r["confidence"]
        } for r in prereq_rows],
        "dependents": [{
            "concept_id": r["target_concept_id"],
            "name": r["target_concept_name"],
            "evidence": r["evidence"],
            "confidence": r["confidence"]
        } for r in dependent_rows],
        "related_concepts": [{
            "concept_id": r["target_concept_id"] if r["source_concept_id"] == concept_id else r["source_concept_id"],
            "name": r["target_concept_name"] if r["source_concept_id"] == concept_id else r["source_concept_name"],
            "relationship_type": r["relationship_type"],
            "evidence": r["evidence"],
            "confidence": r["confidence"]
        } for r in related_rows],
        "sources": source_rows
    }


# =========================================================================
# INNOVATION 4: MISCONCEPTION-AWARE ADAPTIVE ASSESSMENT DATABASE FUNCTIONS
# =========================================================================

def save_assessment_question(question_dict: Dict[str, Any]) -> str:
    """
    Saves a dynamically generated assessment question with full evidence grounding.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongodb_service.save_assessment_question_mongo(question_dict)
    except Exception as e:
        print(f"[MongoDB] save_assessment_question notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    q_id = question_dict.get("id") or f"q_{int(datetime.now().timestamp() * 1000)}"

    cursor.execute("""
    INSERT OR REPLACE INTO assessment_questions (
        id, course_id, topic, concept_id, concept_name, difficulty,
        question_type, question, options_json, correct_key, expected_answer,
        acceptable_terms_json, numerical_value, numerical_tolerance,
        explanation, source_citation_json, source_chunk_id,
        prerequisite_concept, question_hash, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        q_id,
        question_dict["course_id"],
        question_dict.get("topic", "General"),
        question_dict.get("concept_id"),
        question_dict.get("concept_name"),
        question_dict.get("difficulty", "medium"),
        question_dict.get("question_type", "mcq"),
        question_dict["question"],
        json.dumps(question_dict.get("options", [])),
        question_dict.get("correct_key"),
        question_dict.get("expected_answer"),
        json.dumps(question_dict.get("acceptable_terms", [])),
        question_dict.get("numerical_value"),
        question_dict.get("numerical_tolerance"),
        question_dict.get("explanation", ""),
        json.dumps(question_dict.get("source_citation", {})),
        question_dict.get("source_chunk_id"),
        question_dict.get("prerequisite_concept"),
        question_dict.get("question_hash"),
        question_dict.get("created_at", now_iso)
    ))

    conn.commit()
    conn.close()
    return q_id

def get_assessment_questions(
    course_id: str, 
    topic: Optional[str] = None, 
    difficulty: Optional[str] = None, 
    question_type: Optional[str] = None, 
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Retrieves stored assessment questions filtered by course, topic, difficulty, and type.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_assessment_questions_mongo(
                course_id=course_id,
                topic=topic,
                difficulty=difficulty,
                question_type=question_type,
                limit=limit
            )
            if mongo_res and len(mongo_res) > 0:
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_assessment_questions notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM assessment_questions WHERE course_id = ?"
    params: List[Any] = [course_id]

    if topic and topic.lower() != "all":
        query += " AND (LOWER(topic) LIKE ? OR LOWER(concept_name) LIKE ?)"
        params.extend([f"%{topic.lower()}%", f"%{topic.lower()}%"])
    if difficulty and difficulty.lower() != "all":
        query += " AND LOWER(difficulty) = ?"
        params.append(difficulty.lower())
    if question_type and question_type.lower() != "all":
        query += " AND LOWER(question_type) = ?"
        params.append(question_type.lower())

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    questions = []
    for r in rows:
        r_dict = dict(r)
        questions.append({
            "id": r_dict["id"],
            "course_id": r_dict["course_id"],
            "topic": r_dict["topic"],
            "concept_id": r_dict.get("concept_id"),
            "concept_name": r_dict.get("concept_name"),
            "difficulty": r_dict["difficulty"],
            "question_type": r_dict["question_type"],
            "question": r_dict["question"],
            "options": json.loads(r_dict["options_json"]) if r_dict.get("options_json") else [],
            "correct_key": r_dict.get("correct_key"),
            "expected_answer": r_dict.get("expected_answer"),
            "acceptable_terms": json.loads(r_dict["acceptable_terms_json"]) if r_dict.get("acceptable_terms_json") else [],
            "numerical_value": r_dict.get("numerical_value"),
            "numerical_tolerance": r_dict.get("numerical_tolerance"),
            "explanation": r_dict["explanation"],
            "source_citation": json.loads(r_dict["source_citation_json"]) if r_dict.get("source_citation_json") else {},
            "source_chunk_id": r_dict.get("source_chunk_id"),
            "prerequisite_concept": r_dict.get("prerequisite_concept"),
            "question_hash": r_dict.get("question_hash"),
            "created_at": r_dict["created_at"]
        })
    return questions

def get_previously_attempted_question_hashes(user_id: str, course_id: str) -> Set[str]:
    """
    Returns the set of question hashes or question texts already attempted by the user
    to prevent repetitive question generation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DISTINCT q.question_hash, a.question_text
    FROM assessment_attempts a
    LEFT JOIN assessment_questions q ON a.question_id = q.id
    WHERE a.user_id = ? AND a.course_id = ?
    """, (user_id, course_id))
    rows = cursor.fetchall()
    conn.close()

    hashes = set()
    for r in rows:
        if r[0]:
            hashes.add(r[0])
        if r[1]:
            # Also hash the clean question text
            clean_q = re.sub(r'\s+', ' ', r[1].lower().strip())
            hashes.add(clean_q)
    return hashes

def record_assessment_attempt(attempt_dict: Dict[str, Any]) -> str:
    """
    Records a student's answer submission along with evaluation score, feedback,
    and diagnosed misconception hypothesis.
    """
    now_iso = datetime.now().isoformat()
    att_id = attempt_dict.get("id") or f"att_{int(datetime.now().timestamp() * 1000)}"
    attempt_dict["id"] = att_id

    try:
        if mongodb_service.is_mongo_available():
            mongodb_service.record_assessment_attempt_mongo(attempt_dict)
    except Exception as e:
        print(f"[MongoDB] record_assessment_attempt notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO assessment_attempts (
        id, user_id, course_id, question_id, question_text, topic,
        concept_name, question_type, difficulty, student_answer,
        is_correct, score, evaluation_status, feedback,
        misconception_json, source_citation_json, clarifying_answer, taken_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        att_id,
        attempt_dict.get("user_id", "demo_user"),
        attempt_dict["course_id"],
        attempt_dict["question_id"],
        attempt_dict.get("question_text", ""),
        attempt_dict.get("topic", "General"),
        attempt_dict.get("concept_name"),
        attempt_dict.get("question_type", "mcq"),
        attempt_dict.get("difficulty", "medium"),
        attempt_dict.get("student_answer", ""),
        1 if attempt_dict.get("is_correct") else 0,
        attempt_dict.get("score", 0.0),
        attempt_dict.get("evaluation_status", "incorrect"),
        attempt_dict.get("feedback", ""),
        json.dumps(attempt_dict.get("misconception")) if attempt_dict.get("misconception") else None,
        json.dumps(attempt_dict.get("source_citation")) if attempt_dict.get("source_citation") else None,
        attempt_dict.get("clarifying_answer"),
        attempt_dict.get("taken_at", now_iso)
    ))

    # Update topic mastery table
    t_name = attempt_dict.get("topic", "General")
    u_id = attempt_dict.get("user_id", "demo_user")
    is_corr = 1 if attempt_dict.get("is_correct") else 0
    
    cursor.execute("SELECT total_attempts, correct_attempts FROM topic_mastery WHERE user_id = ? AND topic = ?", (u_id, t_name))
    row = cursor.fetchone()
    if row:
        new_total = row["total_attempts"] + 1
        new_correct = row["correct_attempts"] + is_corr
        new_pct = round((new_correct / new_total) * 100, 1) if new_total > 0 else 0.0
        cursor.execute("""
        UPDATE topic_mastery SET total_attempts = ?, correct_attempts = ?, mastery_percentage = ?, last_updated = ?
        WHERE user_id = ? AND topic = ?
        """, (new_total, new_correct, new_pct, now_iso, u_id, t_name))
    else:
        new_pct = 100.0 if is_corr else 0.0
        cursor.execute("""
        INSERT INTO topic_mastery (user_id, topic, total_attempts, correct_attempts, mastery_percentage, last_updated)
        VALUES (?, ?, 1, ?, ?, ?)
        """, (u_id, t_name, is_corr, new_pct, now_iso))

    conn.commit()
    conn.close()
    return att_id

def get_user_assessment_history(user_id: str, course_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieves previous assessment attempts for a user.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_user_assessment_history_mongo(user_id, course_id, limit)
            if mongo_res is not None and len(mongo_res) > 0:
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_user_assessment_history notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM assessment_attempts WHERE user_id = ?"
    params: List[Any] = [user_id]
    if course_id:
        query += " AND course_id = ?"
        params.append(course_id)
    query += " ORDER BY taken_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        r_dict = dict(r)
        history.append({
            "id": r_dict["id"],
            "user_id": r_dict["user_id"],
            "course_id": r_dict["course_id"],
            "question_id": r_dict["question_id"],
            "question_text": r_dict["question_text"],
            "topic": r_dict["topic"],
            "concept_name": r_dict.get("concept_name"),
            "question_type": r_dict["question_type"],
            "difficulty": r_dict["difficulty"],
            "student_answer": r_dict["student_answer"],
            "is_correct": bool(r_dict["is_correct"]),
            "score": r_dict["score"],
            "evaluation_status": r_dict["evaluation_status"],
            "feedback": r_dict["feedback"],
            "misconception": json.loads(r_dict["misconception_json"]) if r_dict.get("misconception_json") else None,
            "source_citation": json.loads(r_dict["source_citation_json"]) if r_dict.get("source_citation_json") else None,
            "clarifying_answer": r_dict.get("clarifying_answer"),
            "taken_at": r_dict["taken_at"]
        })
    return history

def upsert_misconception_profile(user_id: str, course_id: str, misconception: Dict[str, Any]) -> str:
    """
    Tracks diagnosed misconception hypotheses and accumulates occurrence counts.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongodb_service.upsert_misconception_profile_mongo(user_id, course_id, misconception)
    except Exception as e:
        print(f"[MongoDB] upsert_misconception_profile notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    m_id = misconception.get("id") or f"misc_{int(datetime.now().timestamp() * 1000)}"

    c_name = misconception.get("concept_name", "General Concept")
    m_title = misconception.get("misconception_title", "Conceptual Confusion")

    cursor.execute("""
    SELECT id, occurrence_count FROM misconception_profiles
    WHERE user_id = ? AND course_id = ? AND concept_name = ? AND misconception_title = ?
    """, (user_id, course_id, c_name, m_title))
    row = cursor.fetchone()

    if row:
        new_count = row["occurrence_count"] + 1
        m_id = row["id"]
        cursor.execute("""
        UPDATE misconception_profiles
        SET occurrence_count = ?, status = 'active', confidence = ?,
            hypothesis_text = ?, expected_understanding = ?, clarifying_question = ?,
            evidence_excerpt = ?, last_detected_at = ?
        WHERE id = ?
        """, (
            new_count,
            misconception.get("confidence", "medium"),
            misconception.get("hypothesis_text", ""),
            misconception.get("expected_understanding", ""),
            misconception.get("clarifying_question"),
            misconception.get("evidence_excerpt"),
            now_iso,
            m_id
        ))
    else:
        cursor.execute("""
        INSERT INTO misconception_profiles (
            id, user_id, course_id, concept_name, topic, misconception_title,
            hypothesis_text, expected_understanding, confidence, occurrence_count,
            status, clarifying_question, evidence_excerpt, last_detected_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'active', ?, ?, ?)
        """, (
            m_id,
            user_id,
            course_id,
            c_name,
            misconception.get("topic", "General"),
            m_title,
            misconception.get("hypothesis_text", ""),
            misconception.get("expected_understanding", ""),
            misconception.get("confidence", "medium"),
            misconception.get("clarifying_question"),
            misconception.get("evidence_excerpt"),
            now_iso
        ))

    conn.commit()
    conn.close()
    return m_id

def get_user_misconceptions(user_id: str, course_id: Optional[str] = None, status: Optional[str] = "active") -> List[Dict[str, Any]]:
    """
    Retrieves active or all misconception profiles for a user and course.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_user_misconceptions_mongo(user_id, course_id, status)
            if mongo_res is not None and len(mongo_res) > 0:
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_user_misconceptions notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM misconception_profiles WHERE user_id = ?"
    params: List[Any] = [user_id]
    if course_id:
        query += " AND course_id = ?"
        params.append(course_id)
    if status and status.lower() != "all":
        query += " AND status = ?"
        params.append(status.lower())
    query += " ORDER BY occurrence_count DESC, last_detected_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]

def resolve_misconception(user_id: str, course_id: str, concept_name: str):
    """
    Marks a diagnosed misconception as resolved after the student demonstrates correct understanding
    on subsequent assessments.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    UPDATE misconception_profiles
    SET status = 'resolved', last_detected_at = ?
    WHERE user_id = ? AND course_id = ? AND LOWER(concept_name) = ?
    """, (now_iso, user_id, course_id, concept_name.lower()))
    conn.commit()
    conn.close()

def get_adaptive_concept_performance(user_id: str, course_id: str) -> Dict[str, Any]:
    """
    Computes fine-grained concept-level performance, streaks, active misconceptions,
    and prerequisite weaknesses for adaptive practice selection.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Recent attempts for this course
    cursor.execute("""
    SELECT concept_name, topic, is_correct, score, difficulty, question_type, taken_at
    FROM assessment_attempts
    WHERE user_id = ? AND course_id = ?
    ORDER BY taken_at DESC LIMIT 50
    """, (user_id, course_id))
    attempts = [dict(r) for r in cursor.fetchall()]

    # Active misconceptions
    cursor.execute("""
    SELECT * FROM misconception_profiles
    WHERE user_id = ? AND course_id = ? AND status = 'active'
    ORDER BY occurrence_count DESC
    """, (user_id, course_id))
    misconceptions = [dict(r) for r in cursor.fetchall()]

    conn.close()

    concept_stats: Dict[str, Dict[str, Any]] = {}
    current_streak = 0
    total_correct = 0
    total_attempts = len(attempts)

    # Process attempts in chronological order for streak calculation
    for att in reversed(attempts):
        c_name = att.get("concept_name") or att.get("topic") or "General"
        if c_name not in concept_stats:
            concept_stats[c_name] = {
                "concept": c_name,
                "topic": att.get("topic", "General"),
                "total": 0,
                "correct": 0,
                "consecutive_correct": 0,
                "consecutive_incorrect": 0,
                "latest_difficulty": att.get("difficulty", "medium")
            }
        
        stat = concept_stats[c_name]
        stat["total"] += 1
        if att["is_correct"]:
            total_correct += 1
            current_streak += 1
            stat["correct"] += 1
            stat["consecutive_correct"] += 1
            stat["consecutive_incorrect"] = 0
        else:
            current_streak = 0
            stat["consecutive_incorrect"] += 1
            stat["consecutive_correct"] = 0
        stat["latest_difficulty"] = att.get("difficulty", "medium")

    # Compute percentages & mastery status
    weak_concepts = []
    strong_concepts = []
    for c_name, stat in concept_stats.items():
        pct = round((stat["correct"] / stat["total"]) * 100, 1) if stat["total"] > 0 else 0.0
        stat["percentage"] = pct
        if pct < 60.0 or stat["consecutive_incorrect"] >= 2:
            stat["status"] = "Weak"
            weak_concepts.append(c_name)
        elif pct >= 75.0 and stat["consecutive_correct"] >= 2:
            stat["status"] = "Strong"
            strong_concepts.append(c_name)
        else:
            stat["status"] = "Moderate"

    return {
        "user_id": user_id,
        "course_id": course_id,
        "total_attempts": total_attempts,
        "total_correct": total_correct,
        "overall_accuracy": round((total_correct / total_attempts) * 100, 1) if total_attempts > 0 else 0.0,
        "current_streak": current_streak,
        "concept_stats": list(concept_stats.values()),
        "weak_concepts": weak_concepts,
        "strong_concepts": strong_concepts,
        "active_misconceptions": misconceptions
    }


# =========================================================================
# INNOVATION 5: STUDENT CONCEPT STUDY PROGRESS DATABASE FUNCTIONS
# =========================================================================

def record_user_concept_progress(
    user_id: str,
    course_id: str,
    concept_id: str,
    concept_name: str,
    status: str = "studied",
    notes: Optional[str] = None
) -> str:
    """
    Records or updates a student's self-directed progress status on a concept.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongodb_service.record_user_concept_progress_mongo(user_id, course_id, concept_id, concept_name, status, notes)
    except Exception as e:
        print(f"[MongoDB] record_user_concept_progress notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    prog_id = f"prog_{user_id}_{concept_id}"

    cursor.execute("""
    INSERT INTO user_concept_progress (id, user_id, course_id, concept_id, concept_name, status, notes, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, course_id, concept_id) DO UPDATE SET
        status = excluded.status,
        notes = excluded.notes,
        updated_at = excluded.updated_at
    """, (prog_id, user_id, course_id, concept_id, concept_name, status, notes, now_iso))

    conn.commit()
    conn.close()
    return prog_id

def get_user_concept_progress(user_id: str, course_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves concept progress items for a user and optional course.
    """
    try:
        if mongodb_service.is_mongo_available():
            mongo_res = mongodb_service.get_user_concept_progress_mongo(user_id, course_id)
            if mongo_res is not None and len(mongo_res) > 0:
                return mongo_res
    except Exception as e:
        print(f"[MongoDB] get_user_concept_progress notice: {e}")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM user_concept_progress WHERE user_id = ?"
    params: List[Any] = [user_id]
    if course_id:
        query += " AND course_id = ?"
        params.append(course_id)
    query += " ORDER BY updated_at DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]

# --- User Account & Profile Persistence Functions ---
def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists a new user record into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO users (
        id, name, email, password_hash, organisation, org_type, department,
        role_year, preferred_language, profile_picture, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_data["id"],
        user_data["name"].strip(),
        user_data["email"].strip().lower(),
        user_data["password_hash"],
        user_data.get("organisation", "").strip(),
        user_data.get("org_type", "College"),
        user_data.get("department", "").strip(),
        user_data.get("role_year", "").strip(),
        user_data.get("preferred_language", "en"),
        user_data.get("profile_picture", ""),
        user_data.get("created_at", now_iso),
        now_iso
    ))
    conn.commit()
    conn.close()

    # Optional mirror to MongoDB
    try:
        if mongodb_service.is_mongo_available():
            db = mongodb_service.get_mongo_db()
            if db is not None:
                db.users.replace_one({"id": user_data["id"]}, user_data, upsert=True)
    except Exception as e:
        print(f"[MongoDB] user mirror notice: {e}")

    return get_user_by_id(user_data["id"])

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user account by email address (case-insensitive)."""
    if not email:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user account by unique user ID."""
    if not user_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates editable user profile information."""
    allowed_fields = {
        "name", "organisation", "org_type", "department", 
        "role_year", "preferred_language", "profile_picture"
    }
    set_clauses = []
    values = []
    for k, v in updates.items():
        if k in allowed_fields and v is not None:
            set_clauses.append(f"{k} = ?")
            values.append(v)

    if not set_clauses:
        return get_user_by_id(user_id)

    set_clauses.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(user_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()

    updated = get_user_by_id(user_id)
    try:
        if mongodb_service.is_mongo_available():
            db = mongodb_service.get_mongo_db()
            if db is not None and updated:
                db.users.replace_one({"id": user_id}, updated, upsert=True)
    except Exception as e:
        print(f"[MongoDB] update_user mirror notice: {e}")

    return updated

def set_user_reset_token(email: str, reset_token: str, expiry_iso: str) -> bool:
    """Stores a temporary password reset code and expiry for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE LOWER(email) = LOWER(?)",
        (reset_token, expiry_iso, email.strip())
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def reset_user_password(email: str, reset_token: str, new_password_hash: str) -> bool:
    """Verifies reset code and updates password hash."""
    user = get_user_by_email(email)
    if not user:
        return False
    saved_token = user.get("reset_token")
    expiry_str = user.get("reset_token_expiry")
    if not saved_token or saved_token != reset_token:
        return False
    if expiry_str:
        try:
            exp_dt = datetime.fromisoformat(expiry_str)
            if datetime.now() > exp_dt:
                return False
        except Exception:
            pass

    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    cursor.execute(
        "UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL, updated_at = ? WHERE LOWER(email) = LOWER(?)",
        (new_password_hash, now_iso, email.strip())
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0



