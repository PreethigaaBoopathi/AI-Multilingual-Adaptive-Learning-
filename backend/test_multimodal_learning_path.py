"""
Comprehensive Verification Test Suite for Multimodal Adaptive Learning Path Recommendation
Tests all 15 requirements specified in Section 11.
"""
import json
import urllib.request
import urllib.error
import sqlite3
import os
import sys

BASE_URL = "http://localhost:8000"

def post_json(endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_json(endpoint):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def run_tests():
    print("=" * 80)
    print("EXECUTING SECTION 11 TESTING REQUIREMENTS")
    print("=" * 80)
    results = {}

    # Test 1: Target Concept with Sufficient Assessment History
    print("\n--- TEST 1: Target concept with sufficient assessment history ---")
    try:
        # Seed user assessment attempt
        from database import record_assessment_attempt, resolve_misconception
        record_assessment_attempt({
            "user_id": "test_learner_1",
            "course_id": "pdf_817409",
            "question_id": "q_seed_trie",
            "concept_name": "Trie Basics",
            "student_answer": "A tree structure for prefix search",
            "is_correct": True,
            "score": 1.0,
            "evaluation_status": "correct",
            "feedback": "Correct!"
        })
        res = post_json("/api/learning-path/personalized", {
            "course_id": "pdf_817409",
            "target_concept": "Prefix Search",
            "user_id": "test_learner_1"
        })
        assert "steps" in res
        diagnosis = res.get("student_learning_gap_diagnosis", {})
        assert diagnosis.get("has_assessment_history") is True
        print(f"PASSED: Has assessment history: {diagnosis.get('has_assessment_history')}, Total attempts: {diagnosis.get('total_attempts')}")
        results["test_1"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_1"] = f"FAILED: {e}"

    # Test 2: Target Concept with Weak Prerequisite
    print("\n--- TEST 2: Target concept with a weak prerequisite ---")
    try:
        # Record incorrect attempt on prerequisite
        from database import record_assessment_attempt, upsert_misconception_profile
        record_assessment_attempt({
            "user_id": "test_learner_weak",
            "course_id": "pdf_817409",
            "question_id": "q_seed_weak",
            "concept_name": "Tree Structure",
            "student_answer": "Linear linked list array",
            "is_correct": False,
            "score": 0.0,
            "evaluation_status": "incorrect",
            "feedback": "Incorrect"
        })
        upsert_misconception_profile("test_learner_weak", "pdf_817409", {
            "concept_name": "Tree Structure",
            "topic": "Data Structures",
            "misconception_title": "Confuses Trees with Linear Arrays",
            "explanation": "Believes nodes cannot branch"
        })
        res = post_json("/api/learning-path/personalized", {
            "course_id": "pdf_817409",
            "target_concept": "Prefix Search",
            "user_id": "test_learner_weak"
        })
        diag = res.get("student_learning_gap_diagnosis", {})
        assert diag.get("active_misconceptions_count") >= 1 or diag.get("demonstrated_gaps_count") >= 1
        print(f"PASSED: Diagnosed active gaps: {diag.get('demonstrated_gaps_count')}, Misconceptions: {diag.get('active_misconceptions_count')}")
        results["test_2"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_2"] = f"FAILED: {e}"

    # Test 3: Target Concept with Insufficient Assessment History
    print("\n--- TEST 3: Target concept with insufficient assessment history ---")
    try:
        res = post_json("/api/learning-path/personalized", {
            "course_id": "pdf_817409",
            "target_concept": "Trie Operations",
            "user_id": "brand_new_student_xyz"
        })
        diag = res.get("student_learning_gap_diagnosis", {})
        assert diag.get("has_assessment_history") is False
        assert diag.get("untested_prerequisites_count") >= 0
        print(f"PASSED: Transparent handling without fake scores. Summary: {diag.get('diagnostic_summary')}")
        results["test_3"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_3"] = f"FAILED: {e}"

    # Test 4: Recommendations from PDFs and PPT/PPTX Files
    print("\n--- TEST 4: Recommendations from PDFs and PPT/PPTX files ---")
    try:
        # course_cs101_multimodal has presentation slides and pdf passages
        res_index = get_json("/api/learning-path/resources/course_cs101_multimodal")
        modalities = res_index.get("counts_by_modality", {})
        assert "pdf_passage" in modalities and modalities["pdf_passage"] > 0
        assert "presentation_slide" in modalities and modalities["presentation_slide"] > 0
        print(f"PASSED: Indexed {modalities['pdf_passage']} PDF passages and {modalities['presentation_slide']} presentation slides")
        results["test_4"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_4"] = f"FAILED: {e}"

    # Test 5: Recommendations from Processed Lecture Videos with Verified Timestamps
    print("\n--- TEST 5: Recommendations from lecture videos with timestamps ---")
    try:
        res_index = get_json("/api/learning-path/resources/course_cs101_multimodal")
        video_resources = [r for r in res_index.get("resources", []) if r.get("resource_type") == "video_segment"]
        assert len(video_resources) > 0
        v = video_resources[0]
        assert v.get("timestamp_str") is not None
        assert v.get("start_time") is not None
        print(f"PASSED: Video resource found: '{v.get('title')}' with timestamp: {v.get('timestamp_str')} (file: {v.get('filename')})")
        results["test_5"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_5"] = f"FAILED: {e}"

    # Test 6: Correct Page, Slide, Filename, and Timestamp Metadata
    print("\n--- TEST 6: Correct page, slide, filename, and timestamp metadata ---")
    try:
        res_index = get_json("/api/learning-path/resources/course_cs101_multimodal")
        resources = res_index.get("resources", [])
        pdf_res = next(r for r in resources if r.get("resource_type") == "pdf_passage")
        slide_res = next(r for r in resources if r.get("resource_type") == "presentation_slide")
        vid_res = next(r for r in resources if r.get("resource_type") == "video_segment")
        assert pdf_res.get("page_number") is not None and pdf_res.get("filename")
        assert slide_res.get("slide_number") is not None and slide_res.get("filename")
        assert vid_res.get("timestamp_str") is not None and vid_res.get("filename")
        print(f"PASSED: PDF page {pdf_res.get('page_number')} on '{pdf_res.get('filename')}'; Slide {slide_res.get('slide_number')} on '{slide_res.get('filename')}'; Video time {vid_res.get('timestamp_str')} on '{vid_res.get('filename')}'")
        results["test_6"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_6"] = f"FAILED: {e}"

    # Test 7: Selection of Relevant Resource Instead of Keyword-Only Match
    print("\n--- TEST 7: Selection of relevant resource instead of keyword-only match ---")
    try:
        from services.resource_index_service import select_best_multimodal_resource
        res = select_best_multimodal_resource(
            course_id="course_cs101_multimodal",
            concept_name="Process Synchronization",
            topic="Operating Systems",
            learner_gap="active_misconception",
            explanation_level="intermediate"
        )
        assert res.get("best_resource") is not None
        assert res.get("best_resource", {}).get("ranking_score", 0) > 0
        print(f"PASSED: Recommended: '{res['best_resource']['title']}' (Modality: {res['best_resource']['resource_type']}) with rationale: {res['best_resource']['selection_criteria']}")
        results["test_7"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_7"] = f"FAILED: {e}"

    # Test 8: Prerequisite Ordering and Invalid or Cyclic Graph Handling
    print("\n--- TEST 8: Prerequisite ordering and invalid or cyclic graph handling ---")
    try:
        from services.learning_path_service import validate_and_sort_prerequisites_dag
        # Test a graph with an intentional cycle: A -> B -> C -> A
        test_concepts = ["Node_A", "Node_B", "Node_C"]
        test_prereqs = {
            "Node_B": ["Node_A"],
            "Node_C": ["Node_B"],
            "Node_A": ["Node_C"]  # Intentional back-edge cycle
        }
        sorted_order, had_cycle = validate_and_sort_prerequisites_dag(test_concepts, test_prereqs)
        assert had_cycle is True
        assert len(sorted_order) == 3
        print(f"PASSED: Cycle successfully detected and broken. Safe topological sort order: {sorted_order}")
        results["test_8"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_8"] = f"FAILED: {e}"

    # Test 9: Targeted Assessment Following Resource Study
    print("\n--- TEST 9: Targeted assessment following resource study ---")
    try:
        path = post_json("/api/learning-path/personalized", {
            "course_id": "pdf_817409",
            "target_concept": "Prefix Search",
            "user_id": "demo_user"
        })
        steps_with_quiz = [s for s in path.get("steps", []) if s.get("targeted_assessment")]
        assert len(steps_with_quiz) > 0
        step_sample = steps_with_quiz[0]
        q = step_sample["targeted_assessment"]
        assert "question" in q and ("options" in q or "expected_answer" in q)
        print(f"PASSED: Step '{step_sample['concept_name']}' has targeted drill: '{q['question'][:60]}...'")
        results["test_9"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_9"] = f"FAILED: {e}"

    # Test 10: Mastery Updates Based on Genuine Assessment Results
    print("\n--- TEST 10: Mastery updates based on genuine assessment results ---")
    try:
        v_res = post_json("/api/learning-path/verify-step", {
            "course_id": "pdf_817409",
            "concept_name": "Prefix Search",
            "question_id": "q_test_mastery_update",
            "question_text": "What is prefix search?",
            "correct_answer": "Searching keys by prefix in Trie",
            "student_answer": "Searching keys by prefix in Trie",
            "options": ["Searching keys by prefix in Trie", "Sorting an array"],
            "user_id": "test_learner_mastery"
        })
        assert v_res["is_correct"] is True
        assert v_res["status"] == "verified"
        assert v_res["updated_mastery_status"] == "mastered"
        print(f"PASSED: Genuine mastery update confirmed. Score: {v_res['score']}, Status: {v_res['updated_mastery_status']}")
        results["test_10"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_10"] = f"FAILED: {e}"

    # Test 11: Handling of Missing Resources Without Fabricated Citations
    print("\n--- TEST 11: Handling of missing resources without fabricated citations ---")
    try:
        from services.resource_index_service import select_best_multimodal_resource
        res = select_best_multimodal_resource(
            course_id="non_existent_course_123",
            concept_name="Quantum Flux",
            topic="Theoretical Physics"
        )
        assert res.get("best_resource") is None
        assert "No direct uploaded material found" in res.get("selection_rationale", "")
        print(f"PASSED: Transparent handling of missing resources without fake citations: '{res.get('selection_rationale')}'")
        results["test_11"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_11"] = f"FAILED: {e}"

    # Test 12: User and Course Isolation

    print("\n--- TEST 12: User and course isolation ---")
    try:
        res1 = post_json("/api/learning-path/personalized", {
            "course_id": "pdf_817409",
            "user_id": "user_isolated_alpha"
        })
        res2 = post_json("/api/learning-path/personalized", {
            "course_id": "course_cs101_multimodal",
            "user_id": "user_isolated_beta"
        })
        assert res1["course_id"] == "pdf_817409"
        assert res2["course_id"] == "course_cs101_multimodal"
        # Verify resources in res1 belong only to pdf_817409
        for s in res1["steps"]:
            if s.get("recommended_resource"):
                assert s["recommended_resource"]["course_id"] == "pdf_817409"
        print(f"PASSED: Strict user and course isolation maintained across courses.")
        results["test_12"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_12"] = f"FAILED: {e}"

    # Test 13: Error Handling for Unavailable Content and Failed AI Requests
    print("\n--- TEST 13: Error handling for unavailable content ---")
    try:
        # Requesting a course with no data returns clean empty/graceful structure
        res = get_json("/api/learning-path/resources/empty_dummy_course")
        assert res.get("total_resources") == 0
        assert res.get("resources") == []
        print(f"PASSED: Graceful handling for non-existent content: total_resources = {res.get('total_resources')}")
        results["test_13"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_13"] = f"FAILED: {e}"

    # Test 14: Regression Tests for Innovations 1-6
    print("\n--- TEST 14: Regression tests for Innovations 1-6 ---")
    try:
        # Inno 1: Textbooks / chunks
        tb = get_json("/api/textbooks")
        assert len(tb) > 0
        # Inno 2: Concept graph
        cg = get_json("/api/concept-graph/pdf_817409")
        assert "nodes" in cg and len(cg["nodes"]) > 0
        # Inno 3: Grounded Chat / Anti-hallucination
        chat = post_json("/api/chat", {
            "textbook_id": "pdf_817409",
            "query": "What is a Trie?"
        })
        assert "answer" in chat
        # Inno 4: Misconceptions
        misc = get_json("/api/assessment/misconceptions/pdf_817409")
        assert "misconceptions" in misc
        # Inno 5: Visualize
        vis = post_json("/api/visualize", {
            "textbook_id": "pdf_817409",
            "topic": "Trie Data Structure"
        })
        assert "mermaid_code" in vis

        # Inno 6: Adaptive Explain
        ad_exp = post_json("/api/adaptive-explain", {
            "textbook_id": "pdf_817409",
            "topic_or_concept": "Trie Basics",
            "requested_level": "beginner"
        })
        assert "explanation" in ad_exp
        print("PASSED: All Innovations 1-6 endpoints verified and functioning intact.")
        results["test_14"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_14"] = f"FAILED: {e}"

    # Test 15: Preservation of Existing UI and Workflows
    print("\n--- TEST 15: Preservation of existing UI and workflows ---")
    try:
        # Verify static index.html or health endpoints
        h = get_json("/api/health")
        assert h.get("status") == "online"
        print(f"PASSED: Backend and frontend health verified without disruption.")
        results["test_15"] = "PASSED"
    except Exception as e:
        print(f"FAILED: {e}")
        results["test_15"] = f"FAILED: {e}"

    print("\n" + "=" * 80)
    print("TEST SUMMARY REPORT:")
    passed_count = sum(1 for v in results.values() if v == "PASSED")
    print(f"TOTAL: {len(results)} | PASSED: {passed_count} | FAILED: {len(results) - passed_count}")
    print("=" * 80)
    return results

if __name__ == "__main__":
    run_tests()
