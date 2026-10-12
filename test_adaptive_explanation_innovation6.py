"""
================================================================================
TEST SUITE FOR INNOVATION 6: ADAPTIVE EXPLANATION & VISUAL LEARNING
================================================================================
Comprehensive verification for Innovation 6:
1. Dynamic 3-Tier Explanations: Beginner, Intermediate, Advanced from uploaded content
2. Structure-Driven Visual Format Selection (Flowchart, Sequence, Block, Timeline, etc.)
3. Dynamic Student Mastery Detection per Concept (Different levels for different concepts)
4. Cold-Start / Diagnostic Calibration Check for Unassessed Concepts
5. Grounded Provenance & Citation Integrity Across Levels
6. Honest Insufficient Evidence Handling with Explicit Limitation Notices
7. Level-Tailored Practice Question Generation & Submission Evaluation with Level Progression
8. Full HTTP API Endpoint Verification via FastAPI TestClient
9. Full Regression Verification of Innovations 1, 2, 3, 4, and 5
================================================================================
"""

import sys
import os
import io
import json
import sqlite3
from fastapi.testclient import TestClient

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.main import app
from backend.database import (
    init_db, save_textbook, get_db_connection,
    record_assessment_attempt, upsert_misconception_profile,
    get_adaptive_concept_performance, get_user_misconceptions,
    record_user_concept_progress, get_chunks_for_textbook
)
from backend.services.multimodal_service import process_multimodal_file
from backend.services.concept_graph_service import generate_course_concept_graph
from backend.services.explanation_service import (
    determine_concept_mastery_level,
    select_visual_format_for_content,
    generate_level_tailored_explanation,
    generate_level_practice_question,
    generate_adaptive_explanation_pipeline,
    generate_diagnostic_question_pipeline,
    evaluate_adaptive_practice_pipeline,
    evaluate_diagnostic_session_pipeline
)
from backend.services.visualization_service import generate_visual_explanation
from backend.services.assessment_service import (
    evaluate_student_answer,
    generate_dynamic_assessment_questions
)
from backend.services.rag_service import answer_textbook_query
from backend.services.learning_path_service import generate_personalized_learning_path
from backend.config import DATA_DIR

def setup_multimodal_test_course():
    """Sets up rich test course materials for testing Innovation 6."""
    init_db()
    import fitz
    
    test_dir = DATA_DIR / "test_innovation6"
    test_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = test_dir / "Distributed_Systems_Course.pdf"
    
    # 1. Course Material PDF
    doc = fitz.open()
    
    # Page 1: Concurrency Control & Two-Phase Locking
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Distributed Systems: Concurrency Control and Locking\n\n", fontsize=14)
    p1.insert_text((50, 80), 
        "1. Concurrency Control and Serializability\n"
        "In multi-user database systems, concurrency control protocols guarantee that concurrent transaction executions "
        "are conflict serializable. Conflict serializability ensures the execution schedule is equivalent to some serial schedule.\n\n"
        "2. Two-Phase Locking Protocol (2PL)\n"
        "The Two-Phase Locking (2PL) protocol enforces serializability through two distinct execution phases:\n"
        "- Growing Phase: The transaction may acquire shared (read) or exclusive (write) locks on database items, but cannot release any lock.\n"
        "- Shrinking Phase: The transaction may release acquired locks, but is strictly prohibited from acquiring any new locks.\n"
        "Theorem: If every transaction in a schedule follows 2PL, the resulting schedule is guaranteed to be conflict-serializable.",
        fontsize=10
    )
    
    # Page 2: Raft Consensus & Client-Server Message Flow
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Consensus Protocols and Leader Election\n\n", fontsize=14)
    p2.insert_text((50, 80), 
        "1. Raft Consensus Protocol Communication\n"
        "Raft achieves distributed consensus by electing a distinguished leader node. The protocol follows a sequence of messages:\n"
        "Step 1: The client sends a state machine command to the Leader node via RPC.\n"
        "Step 2: The Leader node appends the entry to its local write-ahead log.\n"
        "Step 3: The Leader sends AppendEntries RPC requests to all Follower nodes in the cluster.\n"
        "Step 4: Followers process the log entry and respond with an acknowledgment RPC back to the Leader.\n"
        "Step 5: Once a majority quorum responds, the Leader commits the entry and replies to the client.\n\n"
        "2. Evolution of Consensus Protocols\n"
        "Historical evolution and timeline of distributed fault tolerance:\n"
        "In 1989, Paxos was formulated by Leslie Lamport. In 2014, Ongaro and Ousterhout developed Raft for understandability.",
        fontsize=10
    )
    
    doc.save(str(pdf_path))
    doc.close()
    
    metadata, chunks, media = process_multimodal_file(pdf_path, "Distributed_Systems_Course.pdf")
    course_id = metadata["id"]
    save_textbook(metadata, chunks, media)
    
    generate_course_concept_graph(course_id, force_regenerate=True)
    return course_id

def main():
    print("=" * 80)
    print("TESTING INNOVATION 6: ADAPTIVE EXPLANATION & VISUAL LEARNING")
    print("=" * 80)
    
    student_user_id = "test_student_innov6"
    course_id = setup_multimodal_test_course()
    print(f"[Setup] Course {course_id} indexed with multimodal chunks and concept graph.\n")

    # -------------------------------------------------------------------------
    # TEST 1: Beginner-Level Explanation
    # -------------------------------------------------------------------------
    print("[Test 1] Testing Beginner-Level Explanation (Simple Language & Analogy)...")
    beg_res = generate_adaptive_explanation_pipeline(
        course_id=course_id,
        topic_or_concept="Two-Phase Locking Protocol",
        user_id=student_user_id,
        requested_level="beginner"
    )
    assert beg_res["level"] == "beginner"
    assert len(beg_res["explanation"]) > 50
    assert beg_res["analogy"] is not None
    assert len(beg_res["key_terms"]) >= 1
    assert beg_res["is_sufficient_evidence"] is True
    print(f"[PASS] Beginner explanation generated:")
    print(f"  Level: {beg_res['level']}")
    print(f"  Analogy: {beg_res['analogy'][:100]}...")
    print(f"  Key Terms Count: {len(beg_res['key_terms'])}")

    # -------------------------------------------------------------------------
    # TEST 2: Intermediate-Level Explanation
    # -------------------------------------------------------------------------
    print("\n[Test 2] Testing Intermediate-Level Explanation (Technical Mechanics & Worked Example)...")
    med_res = generate_adaptive_explanation_pipeline(
        course_id=course_id,
        topic_or_concept="Two-Phase Locking Protocol",
        user_id=student_user_id,
        requested_level="intermediate"
    )
    assert med_res["level"] == "intermediate"
    assert len(med_res["explanation"]) > 50
    assert len(med_res["example"]) > 20
    print(f"[PASS] Intermediate explanation generated:")
    print(f"  Level: {med_res['level']}")
    print(f"  Worked Example: {med_res['example'][:100]}...")

    # -------------------------------------------------------------------------
    # TEST 3: Advanced-Level Explanation
    # -------------------------------------------------------------------------
    print("\n[Test 3] Testing Advanced-Level Explanation (Formal Invariants & Edge Cases)...")
    adv_res = generate_adaptive_explanation_pipeline(
        course_id=course_id,
        topic_or_concept="Two-Phase Locking Protocol",
        user_id=student_user_id,
        requested_level="advanced"
    )
    assert adv_res["level"] == "advanced"
    assert len(adv_res["explanation"]) > 50
    assert adv_res.get("formal_notes_or_limitations") is not None
    print(f"[PASS] Advanced explanation generated:")
    print(f"  Level: {adv_res['level']}")
    print(f"  Formal Notes: {adv_res['formal_notes_or_limitations'][:100]}...")

    # -------------------------------------------------------------------------
    # TEST 4: Structure-Driven Visual Representation Selection
    # -------------------------------------------------------------------------
    print("\n[Test 4] Testing Content Structure-Driven Visual Format Selection...")
    chunks = get_chunks_for_textbook(course_id)
    
    # Raft protocol contains communication messages -> sequence
    fmt_raft = select_visual_format_for_content(chunks, "Raft Consensus Protocol Communication", "auto")
    assert fmt_raft in ["sequence", "flowchart"]
    print(f"[PASS] Protocol interaction topic detected format: '{fmt_raft}'")

    # Historical evolution -> timeline
    fmt_history = select_visual_format_for_content(chunks, "Evolution of Consensus Protocols and Milestones", "auto")
    assert fmt_history == "timeline"
    print(f"[PASS] Chronological history topic detected format: '{fmt_history}'")

    # 2PL growing/shrinking phases -> flowchart or concept_map
    fmt_2pl = select_visual_format_for_content(chunks, "Two-Phase Locking Protocol Execution Phases", "auto")
    assert fmt_2pl in ["flowchart", "concept_map"]
    print(f"[PASS] Multi-phase execution topic detected format: '{fmt_2pl}'")

    # -------------------------------------------------------------------------
    # TEST 5: Dynamic Student Mastery Detection per Concept
    # -------------------------------------------------------------------------
    print("\n[Test 5] Testing Dynamic Mastery Detection (Different Levels for Different Concepts)...")
    # Simulate Student:
    # 1. High performance on "Conflict Serializability" (2 correct, 100% accuracy) -> Advanced
    # 2. Low performance & Active Misconception on "Two-Phase Locking Protocol" -> Beginner
    record_assessment_attempt({
        "user_id": student_user_id,
        "course_id": course_id,
        "question_id": "q_ser_01",
        "question_text": "What is conflict serializability?",
        "topic": "Conflict Serializability",
        "concept_name": "Conflict Serializability",
        "question_type": "mcq",
        "difficulty": "medium",
        "student_answer": "A",
        "is_correct": 1,
        "score": 1.0,
        "evaluation_status": "correct",
        "feedback": "Correct"
    })
    record_assessment_attempt({
        "user_id": student_user_id,
        "course_id": course_id,
        "question_id": "q_ser_02",
        "question_text": "Serializability schedule test",
        "topic": "Conflict Serializability",
        "concept_name": "Conflict Serializability",
        "question_type": "mcq",
        "difficulty": "hard",
        "student_answer": "A",
        "is_correct": 1,
        "score": 1.0,
        "evaluation_status": "correct",
        "feedback": "Correct"
    })

    record_assessment_attempt({
        "user_id": student_user_id,
        "course_id": course_id,
        "question_id": "q_2pl_01",
        "question_text": "Can a transaction acquire locks during shrinking phase?",
        "topic": "Two-Phase Locking Protocol",
        "concept_name": "Two-Phase Locking Protocol",
        "question_type": "mcq",
        "difficulty": "medium",
        "student_answer": "B",
        "is_correct": 0,
        "score": 0.0,
        "evaluation_status": "incorrect",
        "feedback": "Incorrect"
    })
    upsert_misconception_profile(
        user_id=student_user_id,
        course_id=course_id,
        misconception={
            "concept_name": "Two-Phase Locking Protocol",
            "topic": "Concurrency Control",
            "misconception_title": "Lock Acquisition in Shrinking Phase",
            "hypothesis_text": "Student incorrectly believes locks can be re-acquired after releasing.",
            "expected_understanding": "2PL strictly prohibits acquiring new locks once any lock is released.",
            "confidence": "high"
        }
    )

    # Evaluate Concept 1: Conflict Serializability
    mastery_ser = determine_concept_mastery_level(course_id, "Conflict Serializability", student_user_id, "auto")
    assert mastery_ser["level"] == "advanced"
    assert mastery_ser["mastery_status"] == "Mastered"
    print(f"[PASS] Concept 'Conflict Serializability' calibrated to: {mastery_ser['level'].upper()} (Accuracy={mastery_ser['mastery_score']}%)")

    # Evaluate Concept 2: Two-Phase Locking
    mastery_2pl = determine_concept_mastery_level(course_id, "Two-Phase Locking Protocol", student_user_id, "auto")
    assert mastery_2pl["level"] == "beginner"
    assert mastery_2pl["active_misconception"] is not None
    print(f"[PASS] Concept 'Two-Phase Locking' calibrated to: {mastery_2pl['level'].upper()} (Active Misconception: {mastery_2pl['active_misconception']['misconception_title']})")

    # -------------------------------------------------------------------------
    # TEST 6: Multi-Question Diagnostic Assessment Session (3-5 Questions)
    # -------------------------------------------------------------------------
    print("\n[Test 6] Testing Multi-Question (3-5) Diagnostic Assessment & Calibration Pipeline...")
    diag_res = generate_diagnostic_question_pipeline(course_id, "Raft Consensus Protocol Communication", student_user_id)
    assert diag_res["concept"] == "Raft Consensus Protocol Communication"
    assert 3 <= diag_res["total_questions"] <= 5, f"Expected 3-5 questions, got {diag_res['total_questions']}"
    assert len(diag_res["questions"]) == diag_res["total_questions"]
    assert diag_res["is_sufficient_evidence"] is True
    print(f"[PASS] Dynamic diagnostic assessment generated {diag_res['total_questions']} questions covering multiple aspects:")
    for idx, q in enumerate(diag_res["questions"]):
        print(f"  Q{idx+1} ({q.get('diagnostic_aspect', 'Core')}) [{q.get('difficulty', 'medium')}]: '{q.get('question')}'")

    # Evaluate Diagnostic Submission: 2 Correct, 1 Incorrect
    mock_diag_answers = []
    for idx, q in enumerate(diag_res["questions"]):
        ans = q.get("correct_key", "A") if idx % 2 == 0 else "B"  # partial mastery
        mock_diag_answers.append({
            "question_id": q.get("id"),
            "question_type": q.get("question_type", "mcq"),
            "student_answer": ans,
            "concept_name": q.get("concept_name", "Raft Consensus Protocol Communication"),
            "topic": q.get("topic", "Distributed Systems"),
            "is_prerequisite": q.get("is_prerequisite", False),
            "prerequisite_concept": q.get("prerequisite_concept"),
            "diagnostic_aspect": q.get("diagnostic_aspect"),
            "correct_key": q.get("correct_key", "A"),
            "expected_answer": q.get("expected_answer", ""),
            "options": q.get("options", []),
            "difficulty": q.get("difficulty", "medium")
        })

    diag_eval = evaluate_diagnostic_session_pipeline(
        course_id=course_id,
        concept_name="Raft Consensus Protocol Communication",
        answers=mock_diag_answers,
        user_id=student_user_id
    )

    assert diag_eval["total_questions"] == len(mock_diag_answers)
    assert diag_eval["calibrated_level"] in ["beginner", "intermediate", "advanced"]
    assert len(diag_eval["demonstrated_strengths"]) >= 1
    assert len(diag_eval["knowledge_gaps"]) >= 1
    assert diag_eval["recommended_visual_format"] in ["flowchart", "concept_map", "block_diagram", "sequence", "comparison", "timeline", "hierarchy", "cycle"]
    print(f"[PASS] Diagnostic evaluation completed successfully:")
    print(f"  Score: {diag_eval['score_percentage']}% ({diag_eval['correct_count']}/{diag_eval['total_questions']})")
    print(f"  Calibrated Level: {diag_eval['calibrated_level'].upper()}")
    print(f"  Recommended Visual: {diag_eval['recommended_visual_format'].upper()}")
    print(f"  Strengths: {diag_eval['demonstrated_strengths'][0]}")
    print(f"  Knowledge Gaps: {diag_eval['knowledge_gaps'][0]}")

    # Test Insufficient Evidence on Diagnostic Generation
    insuff_diag = generate_diagnostic_question_pipeline(course_id, "Quantum Entanglement and Quantum Key Distribution", student_user_id)
    assert insuff_diag["is_sufficient_evidence"] is False
    assert insuff_diag["total_questions"] == 0
    assert "Insufficient source evidence" in insuff_diag["limitation_note"]
    print(f"[PASS] Insufficient source evidence honestly handled for ungrounded topic diagnostic check.")

    # -------------------------------------------------------------------------
    # TEST 7: Source Grounding & Citation Integrity Across Levels
    # -------------------------------------------------------------------------
    print("\n[Test 7] Verifying Source Grounding & Genuine Citations Across Explanation Levels...")
    for lvl in ["beginner", "intermediate", "advanced"]:
        exp = generate_adaptive_explanation_pipeline(
            course_id=course_id,
            topic_or_concept="Two-Phase Locking Protocol",
            user_id=student_user_id,
            requested_level=lvl
        )
        assert len(exp["citations"]) >= 1
        assert exp["citations"][0]["filename"] == "Distributed_Systems_Course.pdf"
        assert exp["citations"][0]["page"] in [1, 2]
    print(f"[PASS] Citations verified with authentic filenames and page locations across all 3 tiers.")

    # -------------------------------------------------------------------------
    # TEST 8: Honest Insufficient Evidence Handling
    # -------------------------------------------------------------------------
    print("\n[Test 8] Testing Insufficient Evidence Detection...")
    insuff_res = generate_adaptive_explanation_pipeline(
        course_id=course_id,
        topic_or_concept="Quantum Computing and Shor's Algorithm",
        user_id=student_user_id,
        requested_level="beginner"
    )
    assert insuff_res["is_sufficient_evidence"] is False
    assert insuff_res["limitation_note"] is not None
    assert "Insufficient source evidence" in insuff_res["limitation_note"]
    print(f"[PASS] Insufficient evidence handled honestly without hallucinating false citations:")
    print(f"  Limitation Notice: {insuff_res['limitation_note']}")

    # -------------------------------------------------------------------------
    # TEST 9: Adaptive Practice Submission & Next Level Progression
    # -------------------------------------------------------------------------
    print("\n[Test 9] Testing Practice Submission & Level Adaptation...")
    # Student at Beginner submits correct answer -> Recommends Level Up to Intermediate
    prac_res_correct = evaluate_adaptive_practice_pipeline(
        course_id=course_id,
        concept_name="Two-Phase Locking Protocol",
        question_id="q_prac_2pl_01",
        question_type="mcq",
        student_answer="A",
        current_level="beginner",
        user_id=student_user_id
    )
    assert prac_res_correct["is_correct"] is True
    assert prac_res_correct["next_recommended_level"] == "intermediate"
    assert prac_res_correct["recommended_action"] == "level_up"
    print(f"[PASS] Correct practice response evaluated:")
    print(f"  Score: {prac_res_correct['score'] * 100}%")
    print(f"  Next Recommended Level: {prac_res_correct['next_recommended_level'].upper()}")
    print(f"  Summary: {prac_res_correct['adaptation_summary']}")

    # -------------------------------------------------------------------------
    # TEST 10: FastAPI HTTP Endpoints Test via TestClient
    # -------------------------------------------------------------------------
    print("\n[Test 10] Testing Innovation 6 HTTP Endpoints via FastAPI TestClient...")
    client = TestClient(app)
    
    # 1. POST /api/adaptive-explain
    resp_exp = client.post("/api/adaptive-explain", json={
        "textbook_id": course_id,
        "topic_or_concept": "Two-Phase Locking Protocol",
        "requested_level": "intermediate",
        "preferred_visual_format": "flowchart",
        "user_id": student_user_id
    })
    assert resp_exp.status_code == 200, f"Adaptive explain HTTP failed: {resp_exp.text}"
    exp_json = resp_exp.json()
    assert exp_json["level"] == "intermediate"
    assert exp_json["visual_representation"] is not None
    assert len(exp_json["citations"]) >= 1
    
    # 2. POST /api/adaptive-explain/diagnostic
    resp_diag = client.post("/api/adaptive-explain/diagnostic", json={
        "textbook_id": course_id,
        "concept": "Raft Consensus Protocol",
        "user_id": student_user_id
    })
    assert resp_diag.status_code == 200
    assert resp_diag.json()["concept"] == "Raft Consensus Protocol"
    
    # 3. POST /api/adaptive-explain/diagnostic/submit
    resp_diag_sub = client.post("/api/adaptive-explain/diagnostic/submit", json={
        "course_id": course_id,
        "concept_name": "Raft Consensus Protocol",
        "user_id": student_user_id,
        "answers": [
            {
                "question_id": "diag_http_01",
                "question_type": "mcq",
                "student_answer": "A",
                "concept_name": "Raft Consensus Protocol",
                "topic": "Distributed Consensus",
                "is_prerequisite": False,
                "correct_key": "A"
            }
        ]
    })
    assert resp_diag_sub.status_code == 200, f"Diagnostic submit failed: {resp_diag_sub.text}"
    diag_sub_json = resp_diag_sub.json()
    assert diag_sub_json["score_percentage"] == 100.0
    assert "calibrated_level" in diag_sub_json

    # 4. POST /api/adaptive-explain/submit-practice
    resp_submit = client.post("/api/adaptive-explain/submit-practice", json={
        "course_id": course_id,
        "concept_name": "Raft Consensus Protocol",
        "question_id": "q_test_raft",
        "question_type": "mcq",
        "student_answer": "A",
        "current_level": "beginner",
        "user_id": student_user_id
    })
    assert resp_submit.status_code == 200
    assert "next_recommended_level" in resp_submit.json()

    # 5. GET /api/adaptive-explain/concept-status/{course_id}/{concept_name}
    resp_stat = client.get(f"/api/adaptive-explain/concept-status/{course_id}/Two-Phase%20Locking%20Protocol?user_id={student_user_id}")
    assert resp_stat.status_code == 200
    assert resp_stat.json()["concept_name"] == "Two-Phase Locking Protocol"
    print(f"[PASS] All 5 Innovation 6 HTTP API endpoints verified successfully.")

    # -------------------------------------------------------------------------
    # TEST 11: Regression Testing Innovations 1, 2, 3, 4, and 5
    # -------------------------------------------------------------------------
    print("\n[Test 11] Regression Testing Innovations 1, 2, 3, 4, and 5...")
    # Innovation 1 (Multimodal Ingestion)
    assert len(get_chunks_for_textbook(course_id)) >= 2
    print("[PASS] Innovation 1 (Multimodal Ingestion): OK")

    # Innovation 2 (Concept Graph)
    graph = generate_course_concept_graph(course_id)
    assert len(graph["nodes"]) >= 2
    print("[PASS] Innovation 2 (Concept Graph): OK")

    # Innovation 3 (Grounded Tutor)
    tutor_res = answer_textbook_query(chunks=get_chunks_for_textbook(course_id), query="Explain Two-Phase Locking", course_id=course_id)
    assert tutor_res["is_grounded"] is True
    print("[PASS] Innovation 3 (Anti-Hallucination Grounded Tutor): OK")

    # Innovation 4 (Adaptive Assessment)
    assess_res = generate_dynamic_assessment_questions(
        course_id=course_id,
        topic="All",
        difficulty="medium",
        question_types=["mcq", "short_answer"],
        num_questions=3,
        user_id="fresh_regression_student"
    )
    assert len(assess_res["questions"]) >= 1
    print("[PASS] Innovation 4 (Adaptive Assessment): OK")

    # Innovation 5 (Personalized Learning Paths & Dynamic Visuals)
    path_res = generate_personalized_learning_path(course_id, "Two-Phase Locking Protocol", student_user_id)
    assert len(path_res["steps"]) >= 1
    print("[PASS] Innovation 5 (Personalized Learning Paths): OK")

    print("\n" + "=" * 80)
    print("ALL INNOVATION 6 TESTS PASSED SUCCESSFULLY (11/11 TEST SUITES)")
    print("=" * 80)

if __name__ == "__main__":
    main()
