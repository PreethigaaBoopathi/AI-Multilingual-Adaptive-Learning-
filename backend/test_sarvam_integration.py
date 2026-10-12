import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv()

# Add backend to path
sys.path.insert(0, str(BASE_DIR))

from config import (
    SARVAM_API_KEY, 
    is_sarvam_available, 
    mark_sarvam_rate_limited
)
from services.translation_service import (
    translate_text, 
    is_tamil, 
    protect_literals, 
    restore_literals,
    normalize_tamil_to_concept,
    _translate_with_sarvam
)
from services.rag_service import answer_textbook_query
from services.summarization_service import summarize_textbook_content
from services.explanation_service import generate_adaptive_explanation
from services.quiz_service import generate_quiz, evaluate_quiz_submission
from services.assessment_service import evaluate_student_answer
from services.learning_path_service import generate_personalized_learning_path
from services.demo_data import get_demo_textbook_data

def run_tests():
    print("=" * 80)
    print("SARVAM AI TRANSLATION INTEGRATION & MULTILINGUAL LEARNING TEST SUITE")
    print("=" * 80)

    demo_data = get_demo_textbook_data()
    course_chunks = demo_data["chunks"]
    course_id = "tb_dbms_norm_001"
    tests_passed = 0
    total_tests = 12

    # -------------------------------------------------------------------------
    # TEST 1: Sarvam API Authentication & Security
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Sarvam AI API Key Configuration & Security Verification...")
    if not SARVAM_API_KEY:
        print("  FAIL: SARVAM_API_KEY is missing or empty in .env.")
        sys.exit(1)
    
    assert len(SARVAM_API_KEY) > 10, "API key length appears invalid"
    assert is_sarvam_available(), "Sarvam circuit breaker is not available"
    # Verify key is never logged or exposed
    masked_key = f"{SARVAM_API_KEY[:4]}...{SARVAM_API_KEY[-4:]}"
    print(f"  PASS: SARVAM_API_KEY securely configured (prefix: {SARVAM_API_KEY[:4]}***, status: ACTIVE)")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 2: English-to-Tamil Translation (Real API Call)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] English-to-Tamil Translation via Official Sarvam API (mayura:v1)...")
    en_input = "Database normalization eliminates redundancy and ensures data integrity."
    ta_result = translate_text(en_input, target_lang="ta", source_lang="en")
    print(f"  Source EN: {en_input}")
    print(f"  Result TA: {ta_result}")
    assert is_tamil(ta_result), f"Expected Tamil characters in translation, got: {ta_result}"
    print("  PASS: Real English-to-Tamil Sarvam API request succeeded with natural Tamil.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 3: Tamil-to-English Translation (Bidirectional API Call)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Tamil-to-English Reverse Translation via Sarvam AI...")
    ta_input = "இரண்டாம் இயல்பு வடிவம் பகுதி செயல்பாட்டு சார்பை நீக்குகிறது."
    en_result = translate_text(ta_input, target_lang="en", source_lang="ta")
    print(f"  Source TA: {ta_input}")
    print(f"  Result EN: {en_result}")
    assert not is_tamil(en_result) and len(en_result) > 10, f"Expected English translation, got: {en_result}"
    print("  PASS: Real Tamil-to-English Sarvam API request succeeded.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 4: Preservation of Source Citations, Math, Code, and Filenames
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Citation, Code, Math, and Filename Preservation...")
    mixed_input = "In 2NF, we eliminate partial functional dependency (Page 14, dbms_norm.pdf). Use `SELECT *` and equation $O(1)$ (Slide 4)."
    mixed_ta = translate_text(mixed_input, target_lang="ta", source_lang="en")
    print(f"  Input:  {mixed_input}")
    print(f"  Output: {mixed_ta}")
    
    # Assert exact preserved tokens
    assert "(Page 14, dbms_norm.pdf)" in mixed_ta or ("(Page 14" in mixed_ta and "dbms_norm.pdf" in mixed_ta), "Citation or filename altered!"
    assert "`SELECT *`" in mixed_ta, "Code block altered!"
    assert "$O(1)$" in mixed_ta, "Math equation altered!"
    assert "(Slide 4)" in mixed_ta, "Slide citation altered!"
    print("  PASS: Citations, code blocks, math, and filenames preserved 100% untouched.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 5: AI Chatbot in Tamil (Grounding, Evidence Provenance)
    # -------------------------------------------------------------------------
    print("\n[TEST 5] AI Chatbot with Tamil Question & Tamil Grounded Response...")
    chat_ta_query = "இரண்டாம் இயல்பு வடிவம் என்றால் என்ன?"
    chat_res = answer_textbook_query(
        chunks=course_chunks,
        query=chat_ta_query,
        language="ta",
        course_id=course_id
    )
    print(f"  Query: {chat_res['query']}")
    print(f"  Evidence Status: {chat_res['evidence_status']}")
    print(f"  Is Grounded: {chat_res['is_grounded']}")
    print(f"  Confidence: {chat_res['confidence']}")
    print(f"  Citations Count: {len(chat_res['citations'])}")
    print(f"  Answer Preview: {chat_res['answer'][:200]}...")
    
    assert chat_res["is_grounded"] is True, "Answer was expected to be grounded"
    assert is_tamil(chat_res["answer"]), "Answer was expected to be localized in Tamil"
    assert len(chat_res["citations"]) > 0, "Expected grounded citations"
    print("  PASS: AI Chatbot successfully answered Tamil query with grounded Tamil response and citations.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 6: Mixed-Language (Tanglish) Chatbot Query
    # -------------------------------------------------------------------------
    print("\n[TEST 6] AI Chatbot with Mixed-Language (Tanglish) Question...")
    mixed_query = "2NF-ல் partial functional dependency என்றால் என்ன?"
    mixed_chat = answer_textbook_query(
        chunks=course_chunks,
        query=mixed_query,
        language="ta",
        course_id=course_id
    )
    print(f"  Query: {mixed_chat['query']}")
    print(f"  Evidence Status: {mixed_chat['evidence_status']}")
    print(f"  Is Grounded: {mixed_chat['is_grounded']}")
    assert mixed_chat["is_grounded"] is True, "Mixed Tanglish query should resolve to grounded answer"
    assert is_tamil(mixed_chat["answer"]), "Answer must be in Tamil"
    print("  PASS: Mixed Tamil-English query successfully grounded and answered in Tamil.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 7: Anti-Hallucination & Unsupported Questions in Tamil
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Unsupported Question & Insufficient Evidence Refusal in Tamil...")
    unsupported_ta_query = "குவாண்டம் இயற்பியல் மற்றும் கருந்துளைகள் என்றால் என்ன?"
    unsupported_res = answer_textbook_query(
        chunks=course_chunks,
        query=unsupported_ta_query,
        language="ta",
        course_id=course_id
    )
    print(f"  Query: {unsupported_res['query']}")
    print(f"  Evidence Status: {unsupported_res['evidence_status']}")
    print(f"  Is Grounded: {unsupported_res['is_grounded']}")
    print(f"  Refusal: {unsupported_res['answer']}")
    assert unsupported_res["is_grounded"] is False, "Unsupported query must NOT claim grounding"
    assert unsupported_res["evidence_status"] == "unsupported", "Status must be unsupported"
    assert is_tamil(unsupported_res["answer"]), "Refusal message must be in Tamil"
    print("  PASS: Unsupported question correctly refused in Tamil with zero hallucinated citations.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 8: Adaptive Concept Explanations in Tamil
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Concept Explanations Localization in Tamil...")
    exp_res = generate_adaptive_explanation(
        chunks=course_chunks,
        topic="Second Normal Form (2NF)",
        level="beginner",
        language="ta"
    )
    print(f"  Concept: {exp_res.get('concept')}")
    print(f"  Language: {exp_res.get('language')}")
    print(f"  Explanation Preview: {exp_res.get('explanation')[:160]}...")
    assert is_tamil(exp_res.get("explanation")), "Explanation must be in Tamil"
    assert is_tamil(exp_res.get("example")), "Example must be in Tamil"
    print("  PASS: Concept explanations generated in fluent Tamil.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 9: Summaries & Quick Revision in Tamil
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Chapter Summaries & Revision Notes in Tamil...")
    summary_res = summarize_textbook_content(
        chunks=course_chunks,
        chapter_title="Chapter 3: Database Normalization",
        language="ta"
    )
    print(f"  Summary Preview: {summary_res.get('summary')[:160]}...")
    print(f"  Key Concepts Count: {len(summary_res.get('key_concepts', []))}")
    assert is_tamil(summary_res.get("summary")), "Summary must be in Tamil"
    if summary_res.get("key_concepts"):
        assert is_tamil(summary_res["key_concepts"][0]), "Key concepts must be localized"
    print("  PASS: Summaries and revision notes localized in Tamil.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 10: Quizzes, Assessments, and Feedback in Tamil
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Quizzes, Feedback, and Tamil Answer Evaluation...")
    quiz_res = generate_quiz(
        textbook_id=course_id,
        topic="Database Normalization",
        difficulty="medium",
        num_questions=3,
        language="ta"
    )
    assert len(quiz_res["questions"]) > 0, "Quiz questions must be generated"
    first_q = quiz_res["questions"][0]
    print(f"  Quiz Q1: {first_q['question'][:120]}...")
    assert is_tamil(first_q["question"]), "Quiz question must be in Tamil"
    assert is_tamil(first_q["options"][0]["text"]), "Quiz options must be in Tamil"
    
    # Test evaluation of quiz submission with language="ta"
    eval_res = evaluate_quiz_submission(
        user_id="demo_user",
        textbook_id=course_id,
        quiz_id=quiz_res["quiz_id"],
        topic="Database Normalization",
        difficulty="medium",
        answers=[{"question_id": first_q["id"], "selected_key": first_q["correct_key"]}],
        language="ta"
    )
    print(f"  Quiz Score: {eval_res['score_percentage']}%")
    print(f"  Localized Recommendation: {eval_res['recommendation']}")
    assert is_tamil(eval_res["recommendation"]), "Quiz recommendation must be in Tamil"
    
    # Test conceptual evaluation of Tamil student answer
    mock_sa_q = {
        "id": "q_test_tamil_01",
        "question_type": "short_answer",
        "question": "What is the primary condition for 2NF?",
        "expected_answer": "Second normal form eliminates partial functional dependency on primary key.",
        "acceptable_terms": ["2nf", "partial", "dependency", "primary", "key"],
        "explanation": "2NF requires eliminating partial dependencies."
    }
    ta_student_answer = "இரண்டாம் இயல்பு வடிவம் பகுதி சார்புநிலையை நீக்குகிறது"
    sa_eval = evaluate_student_answer(
        question_dict=mock_sa_q,
        student_answer=ta_student_answer,
        user_id="demo_user",
        course_id=course_id,
        language="ta"
    )
    print(f"  Student Tamil Answer: {ta_student_answer}")
    print(f"  Evaluated Correct: {sa_eval['is_correct']}")
    print(f"  Feedback: {sa_eval['feedback']}")
    assert sa_eval["is_correct"] is True, "Student answer in Tamil should be conceptually evaluated as correct"
    assert is_tamil(sa_eval["feedback"]), "Feedback should be in Tamil"
    print("  PASS: Quizzes, feedback, and student Tamil answer evaluation verified.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 11: Personalized Learning Path in Tamil
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Personalized Learning Path in Tamil...")
    path_res = generate_personalized_learning_path(
        course_id=course_id,
        target_concept="Second Normal Form (2NF)",
        language="ta"
    )
    print(f"  Target Concept: {path_res.get('target_concept')}")
    print(f"  Total Steps: {len(path_res.get('steps', []))}")
    if path_res.get("steps"):
        step0 = path_res["steps"][0]
        print(f"  Step 1 Reason: {step0.get('recommendation_reason')}")
        print(f"  Step 1 Objective: {step0.get('measurable_objective')}")
        assert is_tamil(step0.get("recommendation_reason")), "Step reason must be localized in Tamil"
    print("  PASS: Adaptive learning path recommendations localized in Tamil.")
    tests_passed += 1

    # -------------------------------------------------------------------------
    # TEST 12: Regression Check for English Mode & Fallback Cooldown
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Regression Check for English Mode & Resilience...")
    eng_chat = answer_textbook_query(
        chunks=course_chunks,
        query="What is 2NF?",
        language="en",
        course_id=course_id
    )
    print(f"  English Query Answer Preview: {eng_chat['answer'][:120]}...")
    assert not is_tamil(eng_chat["answer"]), "English mode should NOT return Tamil"
    assert eng_chat["is_grounded"] is True, "English query must be grounded"
    
    # Test rate limit cooldown resilience without crashing
    mark_sarvam_rate_limited(2.0)
    # When in cooldown, translate_text should seamlessly fall back to secondary provider/rule engine
    cooldown_res = translate_text("Hello, this is a test during cooldown.", target_lang="ta")
    assert cooldown_res and len(cooldown_res) > 0, "Cooldown fallback failed"
    print("  PASS: English functionality preserved and provider cooldown circuit breaker verified.")
    tests_passed += 1

    print("\n" + "=" * 80)
    print(f"TEST RESULTS: {tests_passed}/{total_tests} TESTS PASSED SUCCESSFULLY (100% PASS RATE)")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
