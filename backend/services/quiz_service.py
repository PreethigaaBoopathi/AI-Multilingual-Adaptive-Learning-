import json
import random
from typing import Dict, Any, List, Optional
from config import GEMINI_API_KEY
from database import record_quiz_result

SAMPLE_DBMS_QUIZ_POOL = [
    # 2NF Questions (Target Weakness Demo)
    {
        "id": 1,
        "topic": "Second Normal Form (2NF)",
        "question": "A table is in Second Normal Form (2NF) if it is in 1NF and does not contain which type of functional dependency?",
        "options": [
            {"key": "A", "text": "Transitive Dependency"},
            {"key": "B", "text": "Partial Functional Dependency"},
            {"key": "C", "text": "Trivial Dependency"},
            {"key": "D", "text": "Multivalued Dependency"}
        ],
        "correct_key": "B",
        "explanation": "2NF requires that no non-prime attribute is partially dependent on any candidate key. Any partial dependency on a composite key must be removed.",
        "source_page": 31,
        "difficulty": "medium"
    },
    {
        "id": 2,
        "topic": "Second Normal Form (2NF)",
        "question": "When can a table in 1NF AUTOMATICALLY satisfy 2NF without further decomposition?",
        "options": [
            {"key": "A", "text": "When the primary key consists of a single (non-composite) attribute"},
            {"key": "B", "text": "When the table has more than 10 columns"},
            {"key": "C", "text": "When there are no foreign keys defined"},
            {"key": "D", "text": "When all column names are alphabetically sorted"}
        ],
        "correct_key": "A",
        "explanation": "Partial dependency requires a composite key (proper subset). If the primary key is single-attribute, partial dependency is mathematically impossible.",
        "source_page": 35,
        "difficulty": "hard"
    },
    {
        "id": 3,
        "topic": "Second Normal Form (2NF)",
        "question": "In relation Enrolment(StudentID, CourseID, Grade, CourseFee), why is CourseFee violating 2NF if CourseID -> CourseFee?",
        "options": [
            {"key": "A", "text": "Because CourseFee is a number and not text"},
            {"key": "B", "text": "Because CourseFee depends on only part of the primary key (CourseID) instead of the full key (StudentID, CourseID)"},
            {"key": "C", "text": "Because StudentID cannot be duplicated"},
            {"key": "D", "text": "Because Grade determines CourseFee"}
        ],
        "correct_key": "B",
        "explanation": "Since CourseFee depends solely on CourseID (a subset of composite key {StudentID, CourseID}), it represents a partial dependency.",
        "source_page": 42,
        "difficulty": "easy"
    },
    # 1NF Questions
    {
        "id": 4,
        "topic": "First Normal Form (1NF)",
        "question": "What is the primary constraint enforced by First Normal Form (1NF)?",
        "options": [
            {"key": "A", "text": "Every determinant must be a candidate key"},
            {"key": "B", "text": "Every attribute domain must contain only atomic (indivisible) values"},
            {"key": "C", "text": "No foreign key can reference a primary key"},
            {"key": "D", "text": "Tables must have at least three columns"}
        ],
        "correct_key": "B",
        "explanation": "1NF mandates domain atomicity and the elimination of multi-valued attributes and repeating groups.",
        "source_page": 16,
        "difficulty": "easy"
    },
    {
        "id": 5,
        "topic": "First Normal Form (1NF)",
        "question": "If an employee table stores multiple contact numbers as '9876543210, 9123456780' in a single cell, which normal form is violated?",
        "options": [
            {"key": "A", "text": "1NF"},
            {"key": "B", "text": "2NF"},
            {"key": "C", "text": "3NF"},
            {"key": "D", "text": "BCNF"}
        ],
        "correct_key": "A",
        "explanation": "Storing non-atomic comma-separated values in a single attribute violates First Normal Form.",
        "source_page": 18,
        "difficulty": "easy"
    },
    # 3NF Questions
    {
        "id": 6,
        "topic": "Third Normal Form (3NF)",
        "question": "Which dependency is explicitly eliminated when converting from 2NF to 3NF?",
        "options": [
            {"key": "A", "text": "Partial Functional Dependency"},
            {"key": "B", "text": "Transitive Dependency (Non-prime attribute -> Non-prime attribute)"},
            {"key": "C", "text": "Join Dependency"},
            {"key": "D", "text": "Atomic Dependency"}
        ],
        "correct_key": "B",
        "explanation": "3NF eliminates transitive dependencies where a non-key attribute determines another non-key attribute.",
        "source_page": 51,
        "difficulty": "medium"
    },
    {
        "id": 7,
        "topic": "Third Normal Form (3NF)",
        "question": "For a non-trivial FD X -> Y in 3NF, what condition must hold for each dependency?",
        "options": [
            {"key": "A", "text": "X must be a Superkey OR Y must be a Prime Attribute"},
            {"key": "B", "text": "X and Y must both be foreign keys"},
            {"key": "C", "text": "Y must always be a numeric field"},
            {"key": "D", "text": "X must be equal to Y"}
        ],
        "correct_key": "A",
        "explanation": "3NF allows X -> Y if X is a superkey OR Y is part of a candidate key (prime attribute).",
        "source_page": 56,
        "difficulty": "hard"
    },
    # Transactions & ACID
    {
        "id": 8,
        "topic": "Transactions & ACID Properties",
        "question": "Which ACID property guarantees that all operations of a transaction succeed together or the database is rolled back?",
        "options": [
            {"key": "A", "text": "Atomicity"},
            {"key": "B", "text": "Consistency"},
            {"key": "C", "text": "Isolation"},
            {"key": "D", "text": "Durability"}
        ],
        "correct_key": "A",
        "explanation": "Atomicity ensures the 'all-or-nothing' execution property of database transactions.",
        "source_page": 76,
        "difficulty": "easy"
    },
    {
        "id": 9,
        "topic": "Transactions & ACID Properties",
        "question": "Durability in ACID guarantees which of the following?",
        "options": [
            {"key": "A", "text": "Transactions run in zero milliseconds"},
            {"key": "B", "text": "Committed updates persist permanently even if system power fails"},
            {"key": "C", "text": "No two users can access the database simultaneously"},
            {"key": "D", "text": "Database tables have no duplicate rows"}
        ],
        "correct_key": "B",
        "explanation": "Durability ensures that once a transaction commits, its modifications survive crashes via write-ahead logging.",
        "source_page": 80,
        "difficulty": "medium"
    },
    {
        "id": 10,
        "topic": "Database Keys & Constraints",
        "question": "What is the defining difference between a Superkey and a Candidate Key?",
        "options": [
            {"key": "A", "text": "A Candidate Key is a minimal Superkey with no unnecessary attributes"},
            {"key": "B", "text": "A Superkey cannot contain NULL values whereas Candidate Keys can"},
            {"key": "C", "text": "Candidate keys can only have 1 column"},
            {"key": "D", "text": "There is no difference"}
        ],
        "correct_key": "A",
        "explanation": "A Candidate Key is an irreducible (minimal) Superkey.",
        "source_page": 8,
        "difficulty": "easy"
    }
]

def generate_quiz(textbook_id: str, topic: str, difficulty: str = "medium", num_questions: int = 5, language: str = "en") -> Dict[str, Any]:
    """
    Generates dynamic evidence-grounded MCQ/assessment questions for the selected course, topic and difficulty.
    Supports English and Tamil seamlessly with technical terminology preservation.
    """
    from services.translation_service import translate_text
    try:
        from services.assessment_service import generate_dynamic_assessment_questions
        dynamic_res = generate_dynamic_assessment_questions(
            course_id=textbook_id,
            topic=topic,
            difficulty=difficulty,
            question_types=["mcq"],
            num_questions=num_questions,
            language=language
        )
        if dynamic_res.get("questions") and len(dynamic_res["questions"]) > 0:
            formatted_qs = []
            for idx, q in enumerate(dynamic_res["questions"]):
                # Ensure integer id and source_page format for backwards compatibility with legacy quiz models
                citation = q.get("source_citation", {}) or {}
                source_pg = citation.get("page") or citation.get("slide") or 1
                
                formatted_qs.append({
                    "id": idx + 1,
                    "db_id": q.get("id"),
                    "topic": q.get("topic") or topic,
                    "question": q.get("question"),
                    "options": [{"key": opt["key"], "text": opt["text"]} for opt in q.get("options", [])],
                    "correct_key": q.get("correct_key", "A"),
                    "explanation": q.get("explanation", ""),
                    "source_page": source_pg,
                    "difficulty": q.get("difficulty", difficulty)
                })
            
            quiz_id = f"quiz_{int(random.random() * 100000)}"
            return {
                "quiz_id": quiz_id,
                "topic": topic,
                "difficulty": difficulty,
                "questions": formatted_qs,
                "language": language
            }
    except Exception as e:
        print(f"Dynamic assessment quiz fallback: {e}")

    # Fallback to demo pool if dynamic generation encountered uninitialized course
    t_clean = topic.strip().lower()
    matching = []
    
    if "all" in t_clean or "normalization" in t_clean or "database" in t_clean or "general" in t_clean:
        matching = list(SAMPLE_DBMS_QUIZ_POOL)
    else:
        for q in SAMPLE_DBMS_QUIZ_POOL:
            if t_clean in q["topic"].lower() or any(term in q["question"].lower() for term in t_clean.split()):
                matching.append(q)
                
    if not matching or len(matching) < num_questions:
        matching = list(SAMPLE_DBMS_QUIZ_POOL)
        
    random.seed(42)  # Stable for demo consistency
    selected = matching[:num_questions] if len(matching) >= num_questions else matching
    
    if language in ["ta", "tamil"]:
        localized = []
        for q in selected:
            qc = dict(q)
            qc["question"] = translate_text(q.get("question", ""), "ta")
            qc["options"] = [{"key": o["key"], "text": translate_text(o["text"], "ta")} for o in q.get("options", [])]
            qc["explanation"] = translate_text(q.get("explanation", ""), "ta")
            localized.append(qc)
        selected = localized

    quiz_id = f"quiz_{int(random.random() * 100000)}"
    return {
        "quiz_id": quiz_id,
        "topic": topic,
        "difficulty": difficulty,
        "questions": selected,
        "language": language
    }

def evaluate_quiz_submission(
    user_id: str, 
    textbook_id: str, 
    quiz_id: str, 
    topic: str, 
    difficulty: str, 
    answers: List[Dict[str, Any]],
    language: str = "en"
) -> Dict[str, Any]:
    """
    Evaluates quiz submission, computes score, topic-wise breakdown, and flags weak topics.
    Also diagnoses possible misconceptions and records detailed attempt history in SQLite.
    """
    from database import get_assessment_questions
    
    # Build question lookup map from both pool and recent DB generated questions
    question_map: Dict[Any, Dict[str, Any]] = {q["id"]: q for q in SAMPLE_DBMS_QUIZ_POOL}
    try:
        db_qs = get_assessment_questions(textbook_id, limit=50)
        for dq in db_qs:
            question_map[dq["id"]] = dq
    except Exception:
        pass
    
    results = []
    correct_count = 0
    topic_stats = {}
    
    for idx, ans in enumerate(answers):
        q_id = ans.get("question_id")
        selected_key = ans.get("selected_key", "").upper()
        
        q_data = question_map.get(q_id)
        if not q_data:
            # Fallback by index if question_id is 1-based index
            if isinstance(q_id, int) and 1 <= q_id <= len(SAMPLE_DBMS_QUIZ_POOL):
                q_data = SAMPLE_DBMS_QUIZ_POOL[q_id - 1]
            else:
                continue
            
        correct_key = q_data.get("correct_key", "A").upper()
        is_correct = (selected_key == correct_key)
        if is_correct:
            correct_count += 1
            
        q_topic = q_data.get("topic", topic)
        if q_topic not in topic_stats:
            topic_stats[q_topic] = {"total": 0, "correct": 0}
        topic_stats[q_topic]["total"] += 1
        if is_correct:
            topic_stats[q_topic]["correct"] += 1
            
        source_pg = q_data.get("source_page") or (q_data.get("source_citation", {}).get("page") if isinstance(q_data.get("source_citation"), dict) else 1) or 1

        results.append({
            "question_id": q_id,
            "question": q_data.get("question", ""),
            "topic": q_topic,
            "selected_key": selected_key,
            "correct_key": correct_key,
            "is_correct": is_correct,
            "explanation": q_data.get("explanation", ""),
            "source_page": source_pg
        })
        
    total_q = len(results)
    score_pct = round((correct_count / total_q) * 100, 1) if total_q > 0 else 0.0
    
    topic_breakdown = []
    weak_topics = []
    
    for t_name, stats in topic_stats.items():
        pct = round((stats["correct"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0.0
        status = "Strong" if pct >= 75 else ("Moderate" if pct >= 60 else "Weak")
        if status == "Weak":
            weak_topics.append(t_name)
        topic_breakdown.append({
            "topic": t_name,
            "total_questions": stats["total"],
            "correct_questions": stats["correct"],
            "percentage": pct,
            "status": status
        })
        
    # Generate recommendation based on weakest topic
    if weak_topics:
        primary_weak = weak_topics[0]
        recommendation = f"Revise {primary_weak}: We detected low accuracy ({topic_stats[primary_weak]['correct']}/{topic_stats[primary_weak]['total']} correct). Review the adaptive explanation and visual flowchart in the Adaptive Revision tab."
    elif score_pct < 60:
        recommendation = f"Revise {topic}: Your score was {score_pct}%. We recommend reviewing Beginner-level explanations and retaking the practice test."
    else:
        recommendation = f"Great work! You scored {score_pct}%. Ready to advance to Higher Normal Forms (3NF / BCNF)."

    # Localize feedback & explanations if Tamil is selected
    if language in ["ta", "tamil"]:
        from services.translation_service import translate_text
        recommendation = translate_text(recommendation, "ta")
        for res_item in results:
            if res_item.get("explanation"):
                res_item["explanation"] = translate_text(res_item["explanation"], "ta")

    # Record in database
    record_quiz_result(
        user_id=user_id,
        textbook_id=textbook_id,
        topic=topic,
        difficulty=difficulty,
        total_q=total_q,
        correct_q=correct_count,
        score_pct=score_pct,
        results=results,
        topic_breakdown=topic_breakdown
    )

    return {
        "quiz_id": quiz_id,
        "total_questions": total_q,
        "correct_count": correct_count,
        "score_percentage": score_pct,
        "results": results,
        "topic_breakdown": topic_breakdown,
        "weak_topics": weak_topics,
        "recommendation": recommendation
    }

