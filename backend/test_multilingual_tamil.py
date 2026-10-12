import sys
import os
from pathlib import Path

# Configure utf-8 encoding for Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Set up paths
sys.path.insert(0, str(Path(__file__).parent))

from services.translation_service import (
    translate_text,
    is_tamil,
    normalize_tamil_to_concept,
    ACADEMIC_STEM_TERMS
)
from services.assessment_service import (
    generate_dynamic_assessment_questions,
    evaluate_student_answer
)
from services.quiz_service import generate_quiz
from services.adaptive_service import get_personalized_recommendation
from services.learning_path_service import generate_personalized_learning_path, verify_learning_path_step
from services.rag_service import answer_textbook_query
from services.summarization_service import summarize_textbook_content

def run_multilingual_tests():
    print("=" * 70)
    print("🚀 RUNNING COMPREHENSIVE TAMIL MULTILINGUAL ADAPTIVE LEARNING TESTS")
    print("=" * 70)
    passed = 0
    total = 0

    # ----------------------------------------------------
    # TEST 1: Translation Service - Technical Term & Citation Preservation
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 1] Technical Term & Citation Protection in Translation...")
    sample_text = (
        "In Round Robin scheduling, the CPU is allocated to each process for a fixed Time Quantum. "
        "Refer to (Page 42) and (Slide 7) or (Timestamp 04:30). "
        "A 2NF table must be in 1NF and have no Partial Functional Dependency."
    )
    tamil_trans = translate_text(sample_text, target_lang="ta")
    print("Original:", sample_text)
    print("Translated (TA):", tamil_trans)
    
    # Check that citations are preserved
    has_page_cite = "(Page 42)" in tamil_trans or "(பக்கம் 42)" in tamil_trans or "Page 42" in tamil_trans
    has_slide_cite = "(Slide 7)" in tamil_trans or "Slide 7" in tamil_trans
    has_time_cite = "04:30" in tamil_trans
    has_tech_terms = ("Round Robin" in tamil_trans or "ரவுண்ட் ராபின்" in tamil_trans) and \
                     ("Time Quantum" in tamil_trans or "டைம் குவாண்டம்" in tamil_trans)
    
    if has_page_cite and has_time_cite and has_tech_terms:
        print("✅ PASS: Citations and key technical terms preserved!")
        passed += 1
    else:
        print(f"❌ FAIL: Check failed. Citations/Terms missing: page={has_page_cite}, time={has_time_cite}, terms={has_tech_terms}")

    # ----------------------------------------------------
    # TEST 2: Tamil Text Detection & Concept Normalization
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 2] Tamil Detection & Normalization...")
    t_text = "டைம் குவாண்டம் மற்றும் அணு மதிப்புகள்"
    is_t = is_tamil(t_text)
    normalized = normalize_tamil_to_concept(t_text)
    print(f"Text: '{t_text}', is_tamil={is_t}, normalized='{normalized}'")
    
    if is_t and "time quantum" in normalized.lower() and "atomic values" in normalized.lower():
        print("✅ PASS: Correctly detected Tamil and mapped technical glosses to canonical concepts!")
        passed += 1
    else:
        print(f"❌ FAIL: is_tamil={is_t}, normalized={normalized}")

    # ----------------------------------------------------
    # TEST 3: Dynamic Assessment Question Generation in Tamil
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 3] Assessment Question Generation in Tamil...")
    ta_assessment = generate_dynamic_assessment_questions(
        course_id="tb_dbms_norm_001",
        target_concept="Second Normal Form (2NF)",
        difficulty="medium",
        num_questions=2,
        language="ta"
    )
    questions = ta_assessment.get("questions", [])
    print(f"Generated {len(questions)} questions in Tamil.")
    assert len(questions) > 0, "No questions generated"
    q0 = questions[0]
    print(f"Q1: {q0.get('question')}")
    print(f"Options: {q0.get('options')}")
    
    # Verify Tamil characters are present in the question or options
    has_tamil_q = is_tamil(q0.get("question", "")) or any(is_tamil(opt) for opt in q0.get("options", []))
    # Verify metadata and expected answers are preserved
    has_meta = "concept_name" in q0 and "correct_key" in q0
    if has_tamil_q and has_meta:
        print("✅ PASS: Tamil assessment generated with intact question metadata and option keys!")
        passed += 1
    else:
        print(f"❌ FAIL: has_tamil_q={has_tamil_q}, has_meta={has_meta}")

    # ----------------------------------------------------
    # TEST 4: Student Answer Evaluation with Tamil / Mixed Input
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 4] Student Answer Evaluation (Tamil Input)...")
    q_sample = {
        "id": "test_q1",
        "question_type": "short_answer",
        "question": "What does Second Normal Form (2NF) eliminate?",
        "correct_answer": "Partial Functional Dependency",
        "concept_name": "Second Normal Form (2NF)",
        "topic": "Normalization",
        "source_citation": {"page": 12, "source_type": "pdf"}
    }
    eval_res = evaluate_student_answer(
        question_dict=q_sample,
        student_answer="பகுதி சார்புநிலை (Partial dependency)",
        user_id="demo_user",
        course_id="tb_dbms_norm_001",
        language="ta"
    )
    print(f"Is Correct: {eval_res.get('is_correct')}, Score: {eval_res.get('score')}")
    print(f"Feedback: {eval_res.get('feedback')}")
    
    if eval_res.get("is_correct") and eval_res.get("score") > 0.7:
        print("✅ PASS: Student's Tamil answer correctly evaluated and awarded full credit!")
        passed += 1
    else:
        print(f"❌ FAIL: Student's Tamil answer was not credited properly: {eval_res}")

    # ----------------------------------------------------
    # TEST 5: Quiz Generation in Tamil
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 5] Quiz Generation in Tamil...")
    quiz_res = generate_quiz(
        textbook_id="tb_dbms_norm_001",
        topic="Normalization",
        difficulty="medium",
        num_questions=2,
        language="ta"
    )
    quiz_questions = quiz_res.get("questions", [])
    print(f"Generated {len(quiz_questions)} quiz questions.")
    assert len(quiz_questions) > 0, "No quiz questions generated"
    q_sample = quiz_questions[0]
    print("Quiz Q1:", q_sample.get("question"))
    print("Quiz Options:", q_sample.get("options"))
    
    has_tamil_quiz = is_tamil(q_sample.get("question", "")) or any(is_tamil(opt) for opt in q_sample.get("options", []))
    if has_tamil_quiz:
        print("✅ PASS: Quiz successfully generated in Tamil!")
        passed += 1
    else:
        print(f"❌ FAIL: Quiz questions do not contain Tamil text.")

    # ----------------------------------------------------
    # TEST 6: Adaptive Remediation Recommendation in Tamil
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 6] Personalized Recommendation in Tamil...")
    rec_res = get_personalized_recommendation(
        user_id="demo_user",
        target_topic="Second Normal Form (2NF)",
        course_id="tb_dbms_norm_001",
        language="ta"
    )
    print("Topic:", rec_res.get("topic"))
    print("Reason (TA):", rec_res.get("weakness_reason"))
    print("Short Explanation (TA):", rec_res.get("short_explanation"))
    points = rec_res.get("important_points") or []
    print("Important Points (TA):", points[:2])
    
    has_tamil_rec = is_tamil(rec_res.get("weakness_reason", "")) or is_tamil(rec_res.get("short_explanation", ""))
    if has_tamil_rec:
        print("✅ PASS: Adaptive recommendation pack generated in Tamil!")
        passed += 1
    else:
        print("❌ FAIL: Adaptive recommendation did not output Tamil text.")

    # ----------------------------------------------------
    # TEST 7: Personalized Learning Path in Tamil
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 7] Personalized Multimodal Learning Path in Tamil...")
    path_res = generate_personalized_learning_path(
        course_id="tb_dbms_norm_001",
        target_concept="Third Normal Form (3NF)",
        user_id="demo_user",
        language="ta"
    )
    print("Rationale (TA):", path_res.get("recommendation_rationale"))
    print("Diagnostic Summary (TA):", path_res.get("diagnostic_summary"))
    steps = path_res.get("steps", [])
    print(f"Total Learning Path Steps: {len(steps)}")
    if steps:
        step0 = steps[0]
        print(f"Step 1 Concept: {step0.get('concept_name')}")
        rec_r = step0.get("recommended_resource") or {}
        r_title = rec_r.get("title") or rec_r.get("resource_title") or "Resource"
        citations = step0.get("source_citations", [])
        page_num = rec_r.get("page_number") or rec_r.get("page")
        slide_num = rec_r.get("slide_number") or rec_r.get("slide")
        time_str = rec_r.get("timestamp_str")
        loc_str = f"Page {page_num}" if page_num else (f"Slide {slide_num}" if slide_num else (f"Time {time_str}" if time_str else str(citations)))
        print(f"Step 1 Recommended Resource Title: {r_title}")
        print(f"Step 1 Location / Citations: {loc_str}")
        
        has_intact_cite = bool(citations) or bool(page_num) or bool(slide_num) or bool(time_str) or bool(rec_r.get("provenance_ref"))
        has_tamil_path = is_tamil(path_res.get("recommendation_rationale", "")) or is_tamil(step0.get("description", ""))
        
        if has_tamil_path and has_intact_cite:
            print("✅ PASS: Learning path localized to Tamil while keeping exact source citations intact!")
            passed += 1
        else:
            print(f"❌ FAIL: has_tamil_path={has_tamil_path}, has_intact_cite={has_intact_cite}")
    else:
        print("❌ FAIL: No steps in learning path.")

    # ----------------------------------------------------
    # TEST 8: English Regression Test
    # ----------------------------------------------------
    total += 1
    print("\n[TEST 8] English Mode Regression...")
    en_assessment = generate_dynamic_assessment_questions(
        course_id="tb_dbms_norm_001",
        target_concept="Second Normal Form (2NF)",
        difficulty="medium",
        num_questions=1,
        language="en"
    )
    en_q = en_assessment.get("questions", [])[0].get("question", "")
    print("EN Question:", en_q)
    
    en_rec = get_personalized_recommendation(
        user_id="demo_user",
        target_topic="Second Normal Form (2NF)",
        course_id="tb_dbms_norm_001",
        language="en"
    )
    print("EN Reason:", en_rec.get("weakness_reason"))
    
    if not is_tamil(en_q) and not is_tamil(en_rec.get("weakness_reason", "")):
        print("✅ PASS: English mode preserved without regression!")
        passed += 1
    else:
        print("❌ FAIL: English mode inadvertently returned Tamil text.")

    print("\n" + "=" * 70)
    print(f"📊 SUMMARY: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    run_multilingual_tests()
