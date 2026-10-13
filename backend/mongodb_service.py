import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from pymongo import MongoClient, ReplaceOne, UpdateOne
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from config import MONGODB_URL, MONGODB_DB_NAME

_mongo_client: Optional[MongoClient] = None
_mongo_db = None
_mongo_connected: Optional[bool] = None
_indexes_initialized: bool = False

def get_mongo_client() -> Optional[MongoClient]:
    global _mongo_client, _mongo_connected
    if not MONGODB_URL:
        _mongo_connected = False
        return None
        
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=2500,
                maxPoolSize=25,
                minPoolSize=1,
                retryWrites=True
            )
            # Quick ping check
            _mongo_client.admin.command("ping")
            _mongo_connected = True
            init_mongo_indexes()
        except Exception as e:
            print(f"[MongoDB] Notice: Could not connect to MongoDB Atlas ({e}). Operating in resilient mode.")
            _mongo_connected = False
            _mongo_client = None
            return None
            
    return _mongo_client

def get_mongo_db():
    global _mongo_db
    client = get_mongo_client()
    if client is not None:
        if _mongo_db is None:
            _mongo_db = client[MONGODB_DB_NAME]
        return _mongo_db
    return None

def is_mongo_available() -> bool:
    global _mongo_connected
    if _mongo_connected is not None and not _mongo_connected:
        return False
    return get_mongo_db() is not None

def init_mongo_indexes():
    """Initializes primary indexes on MongoDB collections for optimal query speed once."""
    global _indexes_initialized
    if _indexes_initialized or _mongo_client is None:
        return
    _indexes_initialized = True
    try:
        if _mongo_client is None:
            return
        db = _mongo_client[MONGODB_DB_NAME]
        
        # Course & Chunks
        db.textbooks.create_index("id", unique=True)
        db.chunks.create_index([("textbook_id", 1), ("chapter_id", 1), ("section_id", 1)])
        db.media_items.create_index([("file_id", 1), ("source_type", 1)])
        
        # Concepts & Graph
        db.concepts.create_index([("course_id", 1), ("id", 1)])
        db.concepts.create_index([("course_id", 1), ("name", 1)])
        db.concept_sources.create_index([("concept_id", 1), ("course_id", 1)])
        db.concept_relationships.create_index([("course_id", 1), ("source_concept_id", 1), ("target_concept_id", 1)])
        
        # Assessment & Progress
        db.assessment_questions.create_index([("course_id", 1), ("topic", 1)])
        db.assessment_questions.create_index("question_hash", unique=True, sparse=True)
        db.assessment_attempts.create_index([("user_id", 1), ("course_id", 1), ("taken_at", -1)])
        db.misconception_profiles.create_index([("user_id", 1), ("course_id", 1), ("concept_name", 1), ("misconception_title", 1)], unique=True)
        db.user_concept_progress.create_index([("user_id", 1), ("course_id", 1), ("concept_id", 1)], unique=True)
        db.quiz_history.create_index([("user_id", 1), ("textbook_id", 1), ("taken_at", -1)])
        db.topic_mastery.create_index([("user_id", 1), ("topic", 1)], unique=True)
    except Exception as e:
        print(f"[MongoDB] Index setup note: {e}")

# --------------------------------------------------------------------------
# Collection-level implementations matching database.py
# --------------------------------------------------------------------------

def save_textbook_mongo(metadata_dict: Dict[str, Any], chunks: List[Dict[str, Any]], media_items: Optional[List[Dict[str, Any]]] = None) -> bool:
    db = get_mongo_db()
    if db is None:
        return False
    try:
        tb_doc = {
            "id": metadata_dict["id"],
            "title": metadata_dict["title"],
            "filename": metadata_dict["filename"],
            "source_type": metadata_dict.get("source_type", "pdf"),
            "total_pages": metadata_dict.get("total_pages", len(chunks)),
            "total_slides": metadata_dict.get("total_slides"),
            "duration_seconds": metadata_dict.get("duration_seconds"),
            "duration_str": metadata_dict.get("duration_str"),
            "file_size_bytes": metadata_dict.get("file_size_bytes", 0),
            "extracted_images_count": metadata_dict.get("extracted_images_count", 0),
            "extracted_transcripts_count": metadata_dict.get("extracted_transcripts_count", 0),
            "extracted_tables_count": metadata_dict.get("extracted_tables_count", 0),
            "media_items": metadata_dict.get("media_items", media_items or []),
            "chapters": metadata_dict.get("chapters", []),
            "created_at": metadata_dict.get("created_at", datetime.now().isoformat())
        }
        db.textbooks.replace_one({"id": tb_doc["id"]}, tb_doc, upsert=True)
        
        # Replace chunks
        db.chunks.delete_many({"textbook_id": tb_doc["id"]})
        if chunks:
            chunk_docs = []
            for c in chunks:
                extra_meta = c.get("metadata", {})
                chunk_docs.append({
                    "id": c["id"],
                    "textbook_id": c.get("textbook_id", tb_doc["id"]),
                    "material_id": c.get("material_id", tb_doc["id"]),
                    "source_type": c.get("source_type", tb_doc.get("source_type", "pdf")),
                    "filename": c.get("filename", tb_doc["filename"]),
                    "chapter_id": c.get("chapter_id", ""),
                    "chapter_title": c.get("chapter_title", ""),
                    "section_id": c.get("section_id", ""),
                    "section_title": c.get("section_title", ""),
                    "page": c.get("page", 1),
                    "slide_number": c.get("slide_number"),
                    "start_time": c.get("start_time"),
                    "end_time": c.get("end_time"),
                    "timestamp_str": c.get("timestamp_str"),
                    "content_type": c.get("content_type", "text"),
                    "content": c.get("content", ""),
                    "media_path": c.get("media_path"),
                    "extra_metadata": extra_meta
                })
            db.chunks.insert_many(chunk_docs, ordered=False)
            
        # Media items
        if media_items:
            db.media_items.delete_many({"file_id": tb_doc["id"]})
            media_docs = []
            for m in media_items:
                media_docs.append({
                    "id": m.get("id", f"media_{m.get('filename', '')}_{m.get('page', 0)}"),
                    "file_id": tb_doc["id"],
                    "filename": m.get("filename", tb_doc["filename"]),
                    "source_type": m.get("source_type", tb_doc.get("source_type", "pdf")),
                    "content_type": m.get("content_type", "image"),
                    "page": m.get("page"),
                    "slide": m.get("slide"),
                    "timestamp": m.get("timestamp"),
                    "media_path": m.get("media_path", ""),
                    "media_filename": m.get("media_filename", ""),
                    "width": m.get("width"),
                    "height": m.get("height"),
                    "format": m.get("format", "png"),
                    "description": m.get("description", ""),
                    "created_at": datetime.now().isoformat()
                })
            if media_docs:
                db.media_items.insert_many(media_docs, ordered=False)
        return True
    except Exception as e:
        print(f"[MongoDB] Error saving textbook: {e}")
        return False

def get_textbook_mongo(textbook_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        doc = db.textbooks.find_one({"id": textbook_id}, {"_id": 0})
        return doc
    except Exception as e:
        print(f"[MongoDB] Error fetching textbook: {e}")
        return None

def get_all_textbooks_mongo() -> Optional[List[Dict[str, Any]]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        cursor = db.textbooks.find({}, {"_id": 0}).sort("created_at", -1)
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] Error fetching textbooks: {e}")
        return None

def get_chunks_for_textbook_mongo(textbook_id: str, chapter_id: Optional[str] = None, section_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        query: Dict[str, Any] = {"textbook_id": textbook_id}
        if chapter_id:
            query["chapter_id"] = chapter_id
        if section_id:
            query["section_id"] = section_id
        cursor = db.chunks.find(query, {"_id": 0}).sort([("page", 1), ("slide_number", 1), ("start_time", 1)])
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] Error fetching chunks: {e}")
        return None

def get_media_for_textbook_mongo(textbook_id: str) -> Optional[List[Dict[str, Any]]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        cursor = db.media_items.find({"file_id": textbook_id}, {"_id": 0}).sort([("page", 1), ("slide", 1)])
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] Error fetching media: {e}")
        return None

def record_quiz_result_mongo(user_id: str, textbook_id: str, topic: str, difficulty: str, total_q: int, correct_q: int, score_pct: float, results: List[Dict[str, Any]], topic_breakdown: List[Dict[str, Any]]) -> bool:
    db = get_mongo_db()
    if db is None:
        return False
    try:
        import uuid
        quiz_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        db.quiz_history.insert_one({
            "id": quiz_id,
            "user_id": user_id,
            "textbook_id": textbook_id,
            "topic": topic,
            "difficulty": difficulty,
            "total_questions": total_q,
            "correct_count": correct_q,
            "score_percentage": score_pct,
            "results": results,
            "taken_at": now
        })
        
        # Update topic mastery
        for tb in topic_breakdown:
            t_name = tb["topic"]
            t_tot = tb["total"]
            t_cor = tb["correct"]
            curr = db.topic_mastery.find_one({"user_id": user_id, "topic": t_name})
            if curr:
                new_tot = curr.get("total_attempts", 0) + t_tot
                new_cor = curr.get("correct_attempts", 0) + t_cor
                new_pct = round((new_cor / new_tot) * 100, 1) if new_tot > 0 else 0.0
                db.topic_mastery.update_one(
                    {"user_id": user_id, "topic": t_name},
                    {"$set": {"total_attempts": new_tot, "correct_attempts": new_cor, "mastery_percentage": new_pct, "last_updated": now}}
                )
            else:
                pct = round((t_cor / t_tot) * 100, 1) if t_tot > 0 else 0.0
                db.topic_mastery.insert_one({
                    "user_id": user_id,
                    "topic": t_name,
                    "total_attempts": t_tot,
                    "correct_attempts": t_cor,
                    "mastery_percentage": pct,
                    "last_updated": now
                })
        return True
    except Exception as e:
        print(f"[MongoDB] Error recording quiz result: {e}")
        return False

def get_user_performance_mongo(user_id: str = "demo_user") -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        history = list(db.quiz_history.find({"user_id": user_id}, {"_id": 0}).sort("taken_at", -1))
        mastery = list(db.topic_mastery.find({"user_id": user_id}, {"_id": 0}))
        
        topic_masteries = []
        strong_topics = []
        weak_topics = []
        total_answered = 0
        total_correct = 0

        for m in mastery:
            pct = float(m.get("mastery_percentage", 0.0))
            status = "Strong" if pct >= 75.0 else ("Moderate" if pct >= 60.0 else "Weak")
            attempts = int(m.get("total_attempts", 0))
            correct = int(m.get("correct_attempts", 0))
            t_name = str(m.get("topic", "General"))
            
            topic_masteries.append({
                "topic": t_name,
                "mastery_percentage": pct,
                "quizzes_taken": attempts,
                "status": status,
                "last_practiced": str(m.get("last_updated") or m.get("last_practiced") or datetime.now().isoformat())
            })
            if pct >= 75.0:
                strong_topics.append(t_name)
            elif pct < 60.0:
                weak_topics.append(t_name)
            total_answered += attempts
            total_correct += correct

        # If user has quiz history but total_answered was not counted from mastery
        if total_answered == 0 and history:
            total_answered = sum(int(q.get("total_questions", 0)) for q in history)
            total_correct = sum(int(q.get("correct_count", 0)) for q in history)

        # Default starter demo state if user has completely zero records
        if not topic_masteries and not history:
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

        acc_pct = round((total_correct / total_answered) * 100, 1) if total_answered > 0 else (
            round(sum(float(q.get("score_percentage", 0.0)) for q in history) / len(history), 1) if history else 72.0
        )
        overall_progress = round(sum(t["mastery_percentage"] for t in topic_masteries) / len(topic_masteries), 1) if topic_masteries else 72.0

        recent_activity = []
        for r in history[:10]:
            recent_activity.append({
                "quiz_id": str(r.get("id") or r.get("quiz_id") or "quiz"),
                "topic": str(r.get("topic", "General")),
                "difficulty": str(r.get("difficulty", "Medium")),
                "score_percentage": float(r.get("score_percentage", 0.0)),
                "taken_at": str(r.get("taken_at", ""))
            })

        if not recent_activity and not history:
            recent_activity = [
                {"quiz_id": "quiz_demo_1", "topic": "Second Normal Form (2NF)", "difficulty": "Medium", "score_percentage": 40.0, "taken_at": "Today, 3:20 PM"},
                {"quiz_id": "quiz_demo_2", "topic": "Database Keys & Constraints", "difficulty": "Easy", "score_percentage": 100.0, "taken_at": "Today, 11:30 AM"},
                {"quiz_id": "quiz_demo_3", "topic": "First Normal Form (1NF)", "difficulty": "Medium", "score_percentage": 80.0, "taken_at": "Today, 9:15 AM"}
            ]

        quizzes_completed = len(history) if history else (3 if not mastery else 0)

        return {
            "overall_progress": overall_progress,
            "quizzes_completed": quizzes_completed,
            "questions_answered": total_answered,
            "accuracy_percentage": acc_pct,
            "strong_topics": strong_topics,
            "weak_topics": weak_topics,
            "topic_masteries": topic_masteries,
            "recent_activity": recent_activity,
            # Backward-compatible fields
            "total_quizzes": quizzes_completed,
            "average_score": acc_pct,
            "topic_mastery": mastery,
            "quiz_history": history[:10]
        }
    except Exception as e:
        print(f"[MongoDB] Error fetching performance: {e}")
        return None

def save_concept_graph_mongo(course_id: str, concepts: List[Dict[str, Any]], relationships: List[Dict[str, Any]], sources: Optional[List[Dict[str, Any]]] = None) -> bool:
    db = get_mongo_db()
    if db is None:
        return False
    try:
        now = datetime.now().isoformat()
        db.concepts.delete_many({"course_id": course_id})
        db.concept_sources.delete_many({"course_id": course_id})
        db.concept_relationships.delete_many({"course_id": course_id})
        
        concept_docs = []
        source_docs = []
        for c in concepts:
            cid = c["id"]
            concept_docs.append({
                "id": cid,
                "course_id": course_id,
                "name": c["name"],
                "topic": c.get("topic", "General"),
                "subtopic": c.get("subtopic"),
                "description": c.get("description", ""),
                "created_at": now
            })
            for s in c.get("sources", []):
                source_docs.append({
                    "id": s.get("id", f"src_{cid}_{len(source_docs)}"),
                    "concept_id": cid,
                    "course_id": course_id,
                    "content_unit_id": s.get("content_unit_id"),
                    "source_type": s.get("source_type", "pdf"),
                    "filename": s.get("filename"),
                    "page_number": s.get("page_number"),
                    "slide_number": s.get("slide_number"),
                    "start_time": s.get("start_time"),
                    "end_time": s.get("end_time"),
                    "timestamp_str": s.get("timestamp_str"),
                    "excerpt": s.get("excerpt"),
                    "media_path": s.get("media_path"),
                    "created_at": now
                })
        
        if sources:
            for s in sources:
                cid = s.get("concept_id", "")
                source_docs.append({
                    "id": s.get("id", f"src_{cid}_{len(source_docs)}"),
                    "concept_id": cid,
                    "course_id": course_id,
                    "content_unit_id": s.get("content_unit_id"),
                    "source_type": s.get("source_type", "pdf"),
                    "filename": s.get("filename"),
                    "page_number": s.get("page_number"),
                    "slide_number": s.get("slide_number"),
                    "start_time": s.get("start_time"),
                    "end_time": s.get("end_time"),
                    "timestamp_str": s.get("timestamp_str"),
                    "excerpt": s.get("excerpt"),
                    "media_path": s.get("media_path"),
                    "created_at": now
                })
                
        if concept_docs:
            db.concepts.insert_many(concept_docs, ordered=False)
        if source_docs:
            db.concept_sources.insert_many(source_docs, ordered=False)
            
        rel_docs = []
        for r in relationships:
            s_id = r.get("source_concept_id") or r.get("source_id") or ""
            t_id = r.get("target_concept_id") or r.get("target_id") or ""
            r_type = r.get("relationship_type") or r.get("type", "related_to")
            rel_docs.append({
                "id": r.get("id") or f"rel_{s_id}_{t_id}_{r_type}",
                "course_id": course_id,
                "source_concept_id": s_id,
                "target_concept_id": t_id,
                "source_concept_name": r.get("source_concept_name") or r.get("source_name", ""),
                "target_concept_name": r.get("target_concept_name") or r.get("target_name", ""),
                "relationship_type": r_type,
                "confidence": r.get("confidence", 1.0),
                "evidence": r.get("evidence", ""),
                "created_at": now
            })
        if rel_docs:
            db.concept_relationships.insert_many(rel_docs, ordered=False)
            
        return True
    except Exception as e:
        print(f"[MongoDB] Error saving concept graph: {e}")
        return False

def get_concept_graph_mongo(course_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        concepts = list(db.concepts.find({"course_id": course_id}, {"_id": 0}))
        if not concepts:
            return None
            
        c_ids = [c["id"] for c in concepts]
        sources = list(db.concept_sources.find({"course_id": course_id}, {"_id": 0}))
        relationships = list(db.concept_relationships.find({"course_id": course_id}, {"_id": 0}))
        
        sources_by_c = {}
        for s in sources:
            cid = s["concept_id"]
            if cid not in sources_by_c:
                sources_by_c[cid] = []
            sources_by_c[cid].append(s)
            
        enriched_concepts = []
        for c in concepts:
            enriched_concepts.append({
                "id": c["id"],
                "name": c["name"],
                "topic": c["topic"],
                "subtopic": c.get("subtopic"),
                "description": c.get("description", ""),
                "sources": sources_by_c.get(c["id"], [])
            })
            
        enriched_rels = []
        for r in relationships:
            enriched_rels.append({
                "id": r["id"],
                "source_id": r["source_concept_id"],
                "target_id": r["target_concept_id"],
                "source_name": r["source_concept_name"],
                "target_name": r["target_concept_name"],
                "type": r["relationship_type"],
                "confidence": r.get("confidence", 1.0),
                "evidence": r.get("evidence", "")
            })
            
        return {
            "course_id": course_id,
            "concepts": enriched_concepts,
            "relationships": enriched_rels
        }
    except Exception as e:
        print(f"[MongoDB] Error fetching concept graph: {e}")
        return None

def get_concept_details_mongo(course_id: str, concept_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        c = db.concepts.find_one({"course_id": course_id, "$or": [{"id": concept_id}, {"name": concept_id}]}, {"_id": 0})
        if not c:
            return None
        actual_id = c["id"]
        sources = list(db.concept_sources.find({"concept_id": actual_id, "course_id": course_id}, {"_id": 0}))
        prereqs = list(db.concept_relationships.find({"target_concept_id": actual_id, "course_id": course_id, "relationship_type": "prerequisite_of"}, {"_id": 0}))
        leads_to = list(db.concept_relationships.find({"source_concept_id": actual_id, "course_id": course_id, "relationship_type": "prerequisite_of"}, {"_id": 0}))
        
        return {
            "id": c["id"],
            "name": c["name"],
            "topic": c["topic"],
            "subtopic": c.get("subtopic"),
            "description": c.get("description", ""),
            "sources": sources,
            "prerequisites": [p["source_concept_name"] for p in prereqs],
            "leads_to": [l["target_concept_name"] for l in leads_to]
        }
    except Exception as e:
        print(f"[MongoDB] Error fetching concept details: {e}")
        return None

def save_assessment_question_mongo(q_dict: Dict[str, Any]) -> Optional[str]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        import uuid
        qid = q_dict.get("id") or str(uuid.uuid4())
        doc = dict(q_dict)
        doc["id"] = qid
        doc["created_at"] = doc.get("created_at", datetime.now().isoformat())
        q_hash = doc.get("question_hash")
        if q_hash:
            db.assessment_questions.replace_one({"question_hash": q_hash}, doc, upsert=True)
        else:
            db.assessment_questions.replace_one({"id": qid}, doc, upsert=True)
        return qid
    except Exception as e:
        print(f"[MongoDB] Error saving assessment question: {e}")
        return None

def get_assessment_questions_mongo(
    course_id: str, 
    topic: Optional[str] = None, 
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    concept_name: Optional[str] = None, 
    limit: int = 20
) -> Optional[List[Dict[str, Any]]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        query: Dict[str, Any] = {"course_id": course_id}
        if topic and topic.lower() != "all":
            query["$or"] = [
                {"topic": {"$regex": topic, "$options": "i"}},
                {"concept_name": {"$regex": topic, "$options": "i"}}
            ]
        if difficulty and difficulty.lower() != "all":
            query["difficulty"] = {"$regex": f"^{difficulty}$", "$options": "i"}
        if question_type and question_type.lower() != "all":
            query["question_type"] = {"$regex": f"^{question_type}$", "$options": "i"}
        if concept_name:
            query["concept_name"] = concept_name
        cursor = db.assessment_questions.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] Error fetching assessment questions: {e}")
        return None

def record_assessment_attempt_mongo(attempt_dict: Dict[str, Any]) -> Optional[str]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        import uuid
        aid = attempt_dict.get("id") or str(uuid.uuid4())
        doc = dict(attempt_dict)
        doc["id"] = aid
        doc["taken_at"] = doc.get("taken_at", datetime.now().isoformat())
        db.assessment_attempts.insert_one(doc)
        return aid
    except Exception as e:
        print(f"[MongoDB] Error recording assessment attempt: {e}")
        return None

def get_user_assessment_history_mongo(user_id: str, course_id: Optional[str] = None, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        query: Dict[str, Any] = {"user_id": user_id}
        if course_id:
            query["course_id"] = course_id
        cursor = db.assessment_attempts.find(query, {"_id": 0}).sort("taken_at", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] Error fetching assessment history: {e}")
        return None

def upsert_misconception_profile_mongo(user_id: str, course_id: str, misconception: Dict[str, Any]) -> Optional[str]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        import uuid
        now = datetime.now().isoformat()
        c_name = misconception.get("concept_name", "")
        title = misconception.get("misconception_title", "")
        query = {
            "user_id": user_id,
            "course_id": course_id,
            "concept_name": c_name,
            "misconception_title": title
        }
        existing = db.misconception_profiles.find_one(query)
        if existing:
            db.misconception_profiles.update_one(
                query,
                {
                    "$inc": {"occurrence_count": 1},
                    "$set": {
                        "hypothesis_text": misconception.get("hypothesis_text", existing.get("hypothesis_text", "")),
                        "status": "active",
                        "last_detected_at": now
                    }
                }
            )
            return existing.get("id", str(uuid.uuid4()))
        else:
            mid = str(uuid.uuid4())
            new_doc = {
                "id": mid,
                "user_id": user_id,
                "course_id": course_id,
                "concept_name": c_name,
                "topic": misconception.get("topic", "General"),
                "misconception_title": title,
                "hypothesis_text": misconception.get("hypothesis_text", ""),
                "expected_understanding": misconception.get("expected_understanding", ""),
                "confidence": misconception.get("confidence", "high"),
                "occurrence_count": 1,
                "status": "active",
                "clarifying_question": misconception.get("clarifying_question"),
                "evidence_excerpt": misconception.get("evidence_excerpt"),
                "last_detected_at": now
            }
            db.misconception_profiles.insert_one(new_doc)
            return mid
    except Exception as e:
        print(f"[MongoDB] Error upserting misconception profile: {e}")
        return None

def get_user_misconceptions_mongo(user_id: str, course_id: Optional[str] = None, status: Optional[str] = "active") -> Optional[List[Dict[str, Any]]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        query: Dict[str, Any] = {"user_id": user_id}
        if course_id:
            query["course_id"] = course_id
        if status:
            query["status"] = status
        cursor = db.misconception_profiles.find(query, {"_id": 0}).sort("last_detected_at", -1)
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] Error fetching misconceptions: {e}")
        return None

def record_user_concept_progress_mongo(user_id: str, course_id: str, concept_id: str, concept_name: str, status: str = "studied", notes: Optional[str] = None) -> bool:
    db = get_mongo_db()
    if db is None:
        return False
    try:
        import uuid
        now = datetime.now().isoformat()
        query = {"user_id": user_id, "course_id": course_id, "concept_id": concept_id}
        db.user_concept_progress.update_one(
            query,
            {
                "$set": {
                    "concept_name": concept_name,
                    "status": status,
                    "notes": notes,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "course_id": course_id,
                    "concept_id": concept_id
                }
            },
            upsert=True
        )
        return True
    except Exception as e:
        print(f"[MongoDB] Error recording concept progress: {e}")
        return False

def get_user_concept_progress_mongo(user_id: str, course_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    db = get_mongo_db()
    if db is None:
        return None
    try:
        query: Dict[str, Any] = {"user_id": user_id}
        if course_id:
            query["course_id"] = course_id
        cursor = db.user_concept_progress.find(query, {"_id": 0}).sort("updated_at", -1)
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB] Error fetching concept progress: {e}")
        return None

def sync_sqlite_to_mongodb() -> Dict[str, int]:
    """Syncs existing data from SQLite into MongoDB Atlas so that existing courses, chunks, and concept graphs are immediately available in Atlas."""
    db = get_mongo_db()
    if db is None:
        return {"status": 0, "message": "MongoDB not available"}
        
    import sqlite3
    from config import DB_PATH
    if not os.path.exists(DB_PATH):
        return {"status": 0, "message": "SQLite database not found"}
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    synced_counts = {}

    try:
        # 1. Textbooks
        tb_rows = c.execute("SELECT * FROM textbooks").fetchall()
        for r in tb_rows:
            d = dict(r)
            try:
                d["chapters"] = json.loads(d.get("chapters_json") or "[]")
            except Exception:
                d["chapters"] = []
            try:
                d["media_items"] = json.loads(d.get("media_json") or "[]")
            except Exception:
                d["media_items"] = []
            db.textbooks.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["textbooks"] = len(tb_rows)

        # 2. Chunks
        chk_rows = c.execute("SELECT * FROM chunks").fetchall()
        for r in chk_rows:
            d = dict(r)
            try:
                d["extra_metadata"] = json.loads(d.get("extra_metadata_json") or "{}")
            except Exception:
                d["extra_metadata"] = {}
            db.chunks.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["chunks"] = len(chk_rows)

        # 3. Media Items
        media_rows = c.execute("SELECT * FROM media_items").fetchall()
        for r in media_rows:
            d = dict(r)
            db.media_items.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["media_items"] = len(media_rows)

        # 4. Concepts
        c_rows = c.execute("SELECT * FROM concepts").fetchall()
        for r in c_rows:
            d = dict(r)
            db.concepts.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["concepts"] = len(c_rows)

        # 5. Concept Sources
        cs_rows = c.execute("SELECT * FROM concept_sources").fetchall()
        for r in cs_rows:
            d = dict(r)
            db.concept_sources.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["concept_sources"] = len(cs_rows)

        # 6. Concept Relationships
        cr_rows = c.execute("SELECT * FROM concept_relationships").fetchall()
        for r in cr_rows:
            d = dict(r)
            db.concept_relationships.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["concept_relationships"] = len(cr_rows)

        # 7. Assessment Questions
        aq_rows = c.execute("SELECT * FROM assessment_questions").fetchall()
        for r in aq_rows:
            d = dict(r)
            try:
                d["options"] = json.loads(d.get("options_json") or "[]")
            except Exception:
                d["options"] = []
            try:
                d["source_citation"] = json.loads(d.get("source_citation_json") or "{}")
            except Exception:
                d["source_citation"] = {}
            db.assessment_questions.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["assessment_questions"] = len(aq_rows)

        # 8. User Concept Progress
        ucp_rows = c.execute("SELECT * FROM user_concept_progress").fetchall()
        for r in ucp_rows:
            d = dict(r)
            db.user_concept_progress.replace_one({"id": d["id"]}, d, upsert=True)
        synced_counts["user_concept_progress"] = len(ucp_rows)

    except Exception as e:
        print(f"[MongoDB] Sync error: {e}")
    finally:
        conn.close()

    return synced_counts

