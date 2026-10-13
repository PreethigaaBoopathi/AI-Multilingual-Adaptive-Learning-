from typing import Dict, Any, List, Optional
from database import get_user_performance, get_user_misconceptions, get_adaptive_concept_performance, get_concept_graph
from services.quiz_service import SAMPLE_DBMS_QUIZ_POOL

def get_personalized_recommendation(
    user_id: str = "demo_user", 
    target_topic: Optional[str] = None,
    course_id: Optional[str] = "tb_dbms_norm_001",
    language: str = "en"
) -> Dict[str, Any]:
    """
    Generates a personalized remediation pack for the student's weakest topic or active misconception.
    Includes:
    - Diagnostic reason with misconception hypothesis (if present)
    - Short tailored explanation
    - Important bullet points
    - Micro Mermaid diagram
    - Dynamic target practice questions to retake
    """
    from services.translation_service import translate_text
    c_id = course_id or "tb_dbms_norm_001"
    perf = get_user_performance(user_id)
    adaptive_perf = get_adaptive_concept_performance(user_id, c_id)
    active_misconceptions = adaptive_perf.get("active_misconceptions", [])
    
    # Determine topic to remediate
    if target_topic:
        weak_topic = target_topic
    elif active_misconceptions:
        weak_topic = active_misconceptions[0].get("concept_name", "Second Normal Form (2NF)")
    elif adaptive_perf.get("weak_concepts"):
        weak_topic = adaptive_perf["weak_concepts"][0]
    elif perf.get("weak_topics"):
        weak_topic = perf["weak_topics"][0]
    else:
        weak_topic = "Second Normal Form (2NF)"
        
    t_lower = weak_topic.lower()
    
    # Check if there is an active diagnosed misconception for this topic
    matching_misc = next((m for m in active_misconceptions if weak_topic.lower() in m.get("concept_name", "").lower() or weak_topic.lower() in m.get("topic", "").lower()), None)
    
    if matching_misc:
        reason = f"Diagnosed Misconception Hypothesis: {matching_misc.get('hypothesis_text')}"
    elif "2nf" in t_lower or "second normal form" in t_lower:
        reason = "Your recent assessment accuracy on 2NF indicated difficulty recognizing composite key subsets. Mastering partial dependencies is critical before attempting 3NF."
    elif "3nf" in t_lower or "third normal form" in t_lower:
        reason = "Transitive dependency questions showed low accuracy. Focus on recognizing when non-prime attributes determine other non-prime attributes."
    else:
        reason = f"Mastery for {weak_topic} is currently below the recommended proficiency threshold."

    if "2nf" in t_lower or "second normal form" in t_lower:
        short_exp = (
            "Second Normal Form (2NF) specifically resolves Partial Functional Dependencies. "
            "A partial dependency occurs whenever a non-prime attribute depends on only a part of a composite primary key "
            "rather than the full key. To resolve this, remove the partial attribute and place it into a separate table "
            "along with the determinant subset."
        )
        points = [
            "Check if the Primary Key is composite (2+ columns). If it is single-attribute, 2NF is already satisfied!",
            "Identify attributes that depend on only one part of the composite key (e.g., CourseFee -> CourseID).",
            "Decompose into two tables: 1 table for the full composite relationship, and 1 table for the partial determinant."
        ]
        diagram = """graph TD
    subgraph "Before 2NF (Violation)"
        R1["Table: Student_Course<br/>PK: (StudentID, CourseID)"]
        R1 -.->|"Partial Dependency (Violation!)"| F1["CourseFee"]
        R1 --->|"Full Dependency (Valid)"| G1["Grade"]
    end
    subgraph "After 2NF Decomposition (Resolved)"
        T1["Enrolment(StudentID, CourseID, Grade)"]
        T2["Course(CourseID, CourseFee)"]
    end
    
    style F1 fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b
    style G1 fill:#dcfce7,stroke:#10b981,stroke-width:2px,color:#064e3b
    style T1 fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#075985
    style T2 fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px,color:#5b21b6"""
        
    elif "3nf" in t_lower or "third normal form" in t_lower:
        short_exp = (
            "Third Normal Form (3NF) resolves Transitive Dependencies where a non-prime attribute determines another non-prime attribute. "
            "Rule: For every X -> Y, X must be a Superkey OR Y must be a Prime Attribute."
        )
        points = [
            "Table must already be in 2NF.",
            "Eliminate indirect functional dependencies (e.g., EmpID -> DeptID and DeptID -> DeptName).",
            "Split into Employee(EmpID, DeptID) and Department(DeptID, DeptName)."
        ]
        diagram = """graph TD
    E["EmpID (Primary Key)"] -->|"Direct FD"| D["DeptID (Non-Prime)"]
    D -->|"Transitive FD (Violation)"| DN["DeptName (Non-Prime)"]
    
    style D fill:#fef3c7,stroke:#f59e0b,color:#78350f
    style DN fill:#fee2e2,stroke:#ef4444,color:#7f1d1d"""
        
    else:
        short_exp = f"Targeted remediation module for '{weak_topic}' grounded in uploaded course material."
        points = [
            f"Revisit key definitions and formulas of {weak_topic}.",
            "Practice distinguishing core properties from adjacent prerequisite concepts."
        ]
        diagram = f"""graph TD\n    A["{weak_topic}"] --> B["Review Grounded Rules"]\n    B --> C["Take Adaptive Drill"]"""

    # Dynamically generate practice questions if possible
    questions = []
    try:
        from services.assessment_service import generate_dynamic_assessment_questions
        gen_res = generate_dynamic_assessment_questions(
            course_id=c_id,
            target_concept=weak_topic,
            difficulty="easy",
            question_types=["mcq"],
            num_questions=3,
            user_id=user_id,
            language=language
        )
        for idx, q in enumerate(gen_res.get("questions", [])):
            citation = q.get("source_citation", {}) or {}
            source_pg = citation.get("page") or citation.get("slide") or 1
            questions.append({
                "id": idx + 1,
                "topic": q.get("topic", weak_topic),
                "question": q.get("question"),
                "options": [{"key": opt["key"], "text": opt["text"]} for opt in q.get("options", [])],
                "correct_key": q.get("correct_key", "A"),
                "explanation": q.get("explanation", ""),
                "source_page": source_pg,
                "difficulty": q.get("difficulty", "easy")
            })
    except Exception as e:
        print(f"Dynamic recommendation question generation fallback: {e}")

    if not questions:
        # Fallback pool questions
        questions = [q for q in SAMPLE_DBMS_QUIZ_POOL if weak_topic.lower() in q["topic"].lower()][:3]
        if not questions:
            questions = SAMPLE_DBMS_QUIZ_POOL[:3]
        if language in ["ta", "tamil"]:
            localized_q = []
            for q in questions:
                qc = dict(q)
                qc["question"] = translate_text(q.get("question", ""), "ta")
                qc["options"] = [{"key": o["key"], "text": translate_text(o["text"], "ta")} for o in q.get("options", [])]
                qc["explanation"] = translate_text(q.get("explanation", ""), "ta")
                localized_q.append(qc)
            questions = localized_q

    # Localize text if Tamil requested
    if language in ["ta", "tamil"]:
        reason = translate_text(reason, "ta")
        short_exp = translate_text(short_exp, "ta")
        points = [translate_text(p, "ta") for p in points]
        action_btn = f"{weak_topic} பயிற்சி வினாவை மீண்டும் செய் (Retake Drill)"
    else:
        action_btn = f"Retake {weak_topic} Practice Drill"

    return {
        "topic": weak_topic,
        "weakness_reason": reason,
        "short_explanation": short_exp,
        "important_points": points,
        "mermaid_diagram": diagram,
        "practice_questions": questions,
        "action_button_label": action_btn,
        "language": language
    }

