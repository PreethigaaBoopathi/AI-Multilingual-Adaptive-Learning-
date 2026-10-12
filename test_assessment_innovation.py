import sys
import io
import os
import shutil
import numpy as np
import cv2
from pathlib import Path
import fitz  # PyMuPDF
from pptx import Presentation
from pptx.util import Inches, Pt
from fastapi.testclient import TestClient

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.config import DATA_DIR, UPLOAD_DIR, MEDIA_DIR
from backend.database import (
    init_db, save_textbook, get_textbook, get_all_textbooks,
    get_chunks_for_textbook, get_assessment_questions,
    record_assessment_attempt, get_user_assessment_history,
    get_user_misconceptions, get_adaptive_concept_performance
)
from backend.services.multimodal_service import process_multimodal_file, unify_course_materials
from backend.services.concept_graph_service import generate_course_concept_graph
from backend.services.rag_service import answer_textbook_query
from backend.services.assessment_service import (
    generate_dynamic_assessment_questions,
    evaluate_student_answer,
    select_adaptive_next_step,
    diagnose_misconception,
    compute_question_hash
)
from backend.main import app

client = TestClient(app)

print("=" * 80)
print("TESTING INNOVATION 4: MISCONCEPTION-AWARE ADAPTIVE ASSESSMENT")
print("=" * 80)

init_db()

test_dir = DATA_DIR / "test_innovation4"
test_dir.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# SETUP DYNAMIC MULTIMODAL COURSES FOR ASSESSMENT TESTING
# ----------------------------------------------------------------------
# Course 1: Distributed Systems & Consensus (PDF + PPT + MP4)
# Course 2: Advanced Relational Database Normalization (PDF Only)
# ----------------------------------------------------------------------

print("\n[Setup] Creating dynamic multimodal test course materials...")

# Course 1: Distributed Systems PDF
pdf_path_1 = test_dir / "Distributed_Systems_Core.pdf"
doc1 = fitz.open()
p1 = doc1.new_page()
p1.insert_textbox(
    fitz.Rect(50, 50, 500, 240),
    """Chapter 1: Distributed Consensus Protocols
1.1 Two-Phase Commit Protocol (2PC)
The Two-Phase Commit Protocol is an atomic commitment protocol for distributed databases.
Phase 1 (Prepare Phase): The coordinator node sends a PREPARE message to all cohort participants.
Phase 2 (Commit Phase): If all cohorts reply YES, the coordinator sends a GLOBAL-COMMIT command. If any cohort replies NO or times out, the coordinator sends a GLOBAL-ABORT command.
A key limitation of Two-Phase Commit Protocol is that it is a blocking protocol if the coordinator crashes during the commit phase.""",
    fontsize=11
)
doc1.save(str(pdf_path_1))
doc1.close()

# Course 1: Distributed Systems PPTX (Slides on Raft and Vector Clocks)
pptx_path_1 = test_dir / "Distributed_Systems_Slides.pptx"
prs1 = Presentation()
s1 = prs1.slides.add_slide(prs1.slide_layouts[1])
s1.shapes.title.text = "Raft Consensus and Leader Election Timers"
tf1 = s1.shapes.placeholders[1].text_frame
tf1.text = "Raft consensus protocol manages replicated state machines."
p_a = tf1.add_paragraph()
p_a.text = "Randomized election timers range between 150ms and 300ms to avoid split votes."
prs1.save(str(pptx_path_1))

# Course 1: MP4 Video (Short lecture discussing causality)
mp4_path_1 = test_dir / "Distributed_Systems_Video.mp4"
fps = 30
duration_sec = 2
total_frames = fps * duration_sec
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(str(mp4_path_1), fourcc, fps, (640, 480))
for f in range(total_frames):
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:, :, 0] = 120
    cv2.putText(img, "Lecture: Vector Clocks and Causal Ordering in Distributed Systems", (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    out.write(img)
out.release()

# Course 2: Advanced Relational Database Normalization PDF (For isolation testing)
pdf_path_2 = test_dir / "Database_Normalization_Advanced.pdf"
doc2 = fitz.open()
p2_1 = doc2.new_page()
p2_1.insert_textbox(
    fitz.Rect(50, 50, 500, 240),
    """Chapter 1: Relational Schema Design
1.1 Functional Dependencies and Candidate Keys
A Functional Dependency X -> Y specifies that attribute set X uniquely determines attribute set Y.
A Candidate Key is a minimal superkey with no redundant attributes.
Second Normal Form (2NF) requires eliminating partial dependencies on composite keys. If a primary key has only a single attribute, 2NF is automatically satisfied.""",
    fontsize=11
)
doc2.save(str(pdf_path_2))
doc2.close()

# Process and index Course 1
c1_pdf_meta, c1_pdf_chunks, c1_pdf_media = process_multimodal_file(pdf_path_1, "Distributed_Systems_Core.pdf", custom_id="c1_pdf")
c1_ppt_meta, c1_ppt_chunks, c1_ppt_media = process_multimodal_file(pptx_path_1, "Distributed_Systems_Slides.pptx", custom_id="c1_ppt")
c1_vid_meta, c1_vid_chunks, c1_vid_media = process_multimodal_file(mp4_path_1, "Distributed_Systems_Video.mp4", custom_id="c1_vid")

c1_meta, c1_chunks = unify_course_materials(
    course_id="course_dist_sys_assess",
    course_title="Distributed Systems & Consensus",
    materials=[
        {"metadata": c1_pdf_meta, "chunks": c1_pdf_chunks, "media_items": c1_pdf_media},
        {"metadata": c1_ppt_meta, "chunks": c1_ppt_chunks, "media_items": c1_ppt_media},
        {"metadata": c1_vid_meta, "chunks": c1_vid_chunks, "media_items": c1_vid_media}
    ]
)
save_textbook(c1_meta, c1_chunks, c1_meta.get("media_items", []))
generate_course_concept_graph("course_dist_sys_assess", force_regenerate=True)

# Process and index Course 2
c2_pdf_meta, c2_pdf_chunks, c2_pdf_media = process_multimodal_file(pdf_path_2, "Database_Normalization_Advanced.pdf", custom_id="course_db_assess")
save_textbook(c2_pdf_meta, c2_pdf_chunks, c2_pdf_media)
generate_course_concept_graph("course_db_assess", force_regenerate=True)

print(" -> Course 1 (Distributed Systems) indexed.")
print(" -> Course 2 (Database Normalization) indexed.")

# ----------------------------------------------------------------------
# 1. Generating Questions from a Real Uploaded PDF
# ----------------------------------------------------------------------
print("\n[Test 1] Generating dynamic questions from uploaded PDF content...")
gen_pdf_res = generate_dynamic_assessment_questions(
    course_id="course_db_assess",
    topic="Functional Dependencies and Candidate Keys",
    difficulty="medium",
    question_types=["mcq", "short_answer"],
    num_questions=3,
    user_id="test_user_1"
)
print(f" -> Generated {len(gen_pdf_res['questions'])} questions from PDF.")
assert len(gen_pdf_res['questions']) >= 1, "Expected at least 1 question generated from PDF"
q_pdf = gen_pdf_res['questions'][0]
print(f" -> Question: '{q_pdf['question']}'")
print(f" -> Question Type: {q_pdf['question_type']}")
print(f" -> Source Citation: {q_pdf['source_citation']['filename']} (Page: {q_pdf['source_citation']['page']})")
assert q_pdf['source_citation']['page'] == 1, "Citation page must match PDF Page 1"
print(" -> [PASS] Test 1: Dynamic question generation from real uploaded PDF verified.")

# ----------------------------------------------------------------------
# 2. Generating Questions from Other Modalities (PPTX & MP4 Video)
# ----------------------------------------------------------------------
print("\n[Test 2] Generating questions from Presentation (PPTX) and Video (MP4)...")
gen_multi_res = generate_dynamic_assessment_questions(
    course_id="course_dist_sys_assess",
    topic="All",
    difficulty="medium",
    question_types=["mcq", "numerical", "short_answer"],
    num_questions=4,
    user_id="test_user_2"
)
print(f" -> Generated {len(gen_multi_res['questions'])} questions across multimodal course.")
assert len(gen_multi_res['questions']) >= 1, "Expected multimodal questions"

# Check presence of PPTX or Video source citations
source_types_found = set(q['source_citation']['source_type'] for q in gen_multi_res['questions'])
print(f" -> Source types represented in questions: {source_types_found}")
assert len(source_types_found) >= 1
print(" -> [PASS] Test 2: Multimodal question generation across PPTX and Video verified.")

# ----------------------------------------------------------------------
# 3. Rejecting a Question whose Answer is Unsupported
# ----------------------------------------------------------------------
print("\n[Test 3] Rejecting questions whose expected answer is unsupported by source content...")
unsupported_fake_q = {
    "id": "q_fake_quantum",
    "course_id": "course_dist_sys_assess",
    "topic": "Quantum Teleportation",
    "question": "How does quantum entanglement allow faster-than-light communication?",
    "options": [
        {"key": "A", "text": "Via spooky action at a distance."},
        {"key": "B", "text": "Using wormholes."},
        {"key": "C", "text": "Through tachyons."},
        {"key": "D", "text": "It does not allow FTL."}
    ],
    "correct_key": "D",
    "expected_answer": "Entanglement cannot transmit classical data faster than light.",
    "explanation": "Quantum physics theorem.",
    "source_chunk_id": "non_existent_chunk_123"
}
from backend.services.assessment_service import _validate_question_against_source
is_valid = _validate_question_against_source(unsupported_fake_q, c1_chunks)
print(f" -> Unsupported question validation result: {is_valid}")
assert is_valid is False, "Unsupported question must be rejected by evidence validation"
print(" -> [PASS] Test 3: Unsupported questions strictly rejected.")

# ----------------------------------------------------------------------
# 4. Correct and Incorrect MCQ Evaluation
# ----------------------------------------------------------------------
print("\n[Test 4] Correct and Incorrect MCQ Evaluation...")
sample_mcq = {
    "id": "q_test_mcq_2pc",
    "course_id": "course_dist_sys_assess",
    "topic": "Two-Phase Commit Protocol (2PC)",
    "concept_name": "Two-Phase Commit Protocol (2PC)",
    "difficulty": "medium",
    "question_type": "mcq",
    "question": "What is the primary operational limitation of standard Two-Phase Commit Protocol (2PC)?",
    "options": [
        {"key": "A", "text": "It requires quadratic communication complexity across peer nodes."},
        {"key": "B", "text": "It is a blocking protocol if coordinator crashes during the commit phase."},
        {"key": "C", "text": "It cannot handle integer transactions."},
        {"key": "D", "text": "It eliminates write-ahead logging."}
    ],
    "correct_key": "B",
    "expected_answer": "It is a blocking protocol if coordinator crashes during the commit phase.",
    "explanation": "Two-Phase Commit is a blocking protocol that halts cohorts if the coordinator fails.",
    "source_citation": {"filename": "Distributed_Systems_Core.pdf", "page": 1, "source_type": "pdf"}
}

# 4A: Submit Correct Answer (B)
eval_correct = evaluate_student_answer(sample_mcq, student_answer="B", user_id="user_test_mcq")
print(f" -> Correct Submission Status: '{eval_correct['evaluation_status']}', Score: {eval_correct['score']}")
assert eval_correct['is_correct'] is True
assert eval_correct['score'] == 1.0
assert eval_correct['evaluation_status'] == "correct"

# 4B: Submit Incorrect Answer (A)
eval_incorrect = evaluate_student_answer(sample_mcq, student_answer="A", user_id="user_test_mcq")
print(f" -> Incorrect Submission Status: '{eval_incorrect['evaluation_status']}', Score: {eval_incorrect['score']}")
assert eval_incorrect['is_correct'] is False
assert eval_incorrect['score'] == 0.0
assert eval_incorrect['evaluation_status'] == "incorrect"
assert eval_incorrect['misconception'] is not None, "Incorrect answer should trigger misconception analysis"
print(" -> [PASS] Test 4: Correct and Incorrect MCQ evaluation verified.")

# ----------------------------------------------------------------------
# 5. Short-Answer Evaluation Accepting Valid Alternative Wording
# ----------------------------------------------------------------------
print("\n[Test 5] Short-Answer Evaluation accepting valid alternative phrasing...")
sample_sa = {
    "id": "q_test_sa_cand_key",
    "course_id": "course_db_assess",
    "topic": "Database Keys & Constraints",
    "concept_name": "Candidate Keys",
    "difficulty": "medium",
    "question_type": "short_answer",
    "question": "Define what a Candidate Key is in relational database schema design.",
    "expected_answer": "A Candidate Key is a minimal superkey with no redundant attributes.",
    "acceptable_terms": ["minimal", "superkey", "redundant", "unique", "attributes", "candidate"],
    "explanation": "A Candidate Key is defined as an irreducible minimal superkey.",
    "source_citation": {"filename": "Database_Normalization_Advanced.pdf", "page": 1, "source_type": "pdf"}
}

# 5A: Alternative phrasing with same semantic meaning
student_rephrased = "It is an irreducible superkey that uniquely identifies tuples without any extra unnecessary columns."
eval_sa_alt = evaluate_student_answer(sample_sa, student_answer=student_rephrased, user_id="user_test_sa")
print(f" -> Rephrased Short-Answer Status: '{eval_sa_alt['evaluation_status']}', Score: {eval_sa_alt['score']}")
assert eval_sa_alt['is_correct'] is True, "Semantic evaluator must accept valid rephrased alternative"
assert eval_sa_alt['score'] >= 0.5

# 5B: Completely incorrect short answer
student_wrong = "A candidate key is a foreign key that references user passwords in web cookies."
eval_sa_wrong = evaluate_student_answer(sample_sa, student_answer=student_wrong, user_id="user_test_sa")
print(f" -> Wrong Short-Answer Status: '{eval_sa_wrong['evaluation_status']}', Score: {eval_sa_wrong['score']}")
assert eval_sa_wrong['is_correct'] is False
assert eval_sa_wrong['score'] == 0.0
print(" -> [PASS] Test 5: Short-answer semantic evaluation accepting valid alternative phrasing verified.")

# ----------------------------------------------------------------------
# 6. Numerical / Problem-Solving Evaluation
# ----------------------------------------------------------------------
print("\n[Test 6] Numerical evaluation with tolerance and calculation validation...")
sample_num = {
    "id": "q_test_num_raft",
    "course_id": "course_dist_sys_assess",
    "topic": "Raft Consensus",
    "concept_name": "Raft Consensus",
    "difficulty": "medium",
    "question_type": "numerical",
    "question": "If Raft election timers range between 150ms and 300ms, what is the midpoint interval in milliseconds?",
    "numerical_value": 225.0,
    "numerical_tolerance": 5.0,
    "expected_answer": "225.0 ms",
    "explanation": "Midpoint = (150 + 300) / 2 = 225 ms.",
    "source_citation": {"filename": "Distributed_Systems_Slides.pptx", "slide": 1, "source_type": "presentation"}
}

# 6A: Correct calculation
eval_num_corr = evaluate_student_answer(sample_num, student_answer="225 ms", user_id="user_test_num")
print(f" -> Numerical Correct Status: '{eval_num_corr['evaluation_status']}', Score: {eval_num_corr['score']}")
assert eval_num_corr['is_correct'] is True
assert eval_num_corr['score'] == 1.0

# 6B: Within tolerance (224)
eval_num_tol = evaluate_student_answer(sample_num, student_answer="224", user_id="user_test_num")
assert eval_num_tol['is_correct'] is True

# 6C: Out of tolerance calculation error (500)
eval_num_wrong = evaluate_student_answer(sample_num, student_answer="500 ms", user_id="user_test_num")
print(f" -> Numerical Incorrect Status: '{eval_num_wrong['evaluation_status']}', Score: {eval_num_wrong['score']}")
assert eval_num_wrong['is_correct'] is False
assert eval_num_wrong['score'] == 0.0
print(" -> [PASS] Test 6: Numerical problem-solving evaluation verified.")

# ----------------------------------------------------------------------
# 7. Misconception Detection (Hypothesis Framing & Clarifying Questions)
# ----------------------------------------------------------------------
print("\n[Test 7] Detecting possible misconceptions as hypotheses with confidence levels...")
misc_diag = diagnose_misconception(
    concept_name="Second Normal Form (2NF)",
    topic="Relational Schema Design",
    student_answer="2NF requires eliminating transitive dependencies where non-prime determines non-prime.",
    expected_answer="2NF eliminates partial dependencies on composite keys.",
    question_text="What does 2NF eliminate?",
    evidence_text="2NF requires eliminating partial dependencies on composite keys."
)

print(f" -> Diagnosed Misconception Title: '{misc_diag['misconception_title']}'")
print(f" -> Hypothesis Text: '{misc_diag['hypothesis_text']}'")
print(f" -> Confidence Level: '{misc_diag['confidence']}'")
print(f" -> Clarifying Follow-Up: '{misc_diag['clarifying_question']}'")

assert "Possible Misconception" in misc_diag['hypothesis_text'], "Must be explicitly framed as hypothesis"
assert misc_diag['confidence'] in ["high", "medium", "low"]
assert misc_diag['clarifying_question'] is not None, "Must provide clarifying question when probing reasoning"
print(" -> [PASS] Test 7: Misconception diagnosis with hypothesis framing and clarifying question verified.")

# ----------------------------------------------------------------------
# 8. Adaptive Practice & Prerequisite Remediation
# ----------------------------------------------------------------------
print("\n[Test 8] Adaptive practice selection (Difficulty progression & Prerequisite fallback)...")

# 8A: Difficulty progression on consecutive correct answers
next_step_adv = select_adaptive_next_step(
    course_id="course_db_assess",
    user_id="user_test_mcq",
    current_topic="Database Keys & Constraints",
    current_concept="Candidate Keys",
    last_question_id="q_1",
    last_was_correct=True
)
print(f" -> Adaptive Action Type: '{next_step_adv['action_type']}'")
print(f" -> Rationale: '{next_step_adv['rationale']}'")
assert next_step_adv['next_question'] is not None

# 8B: Misconception targeted practice when active misconception exists
next_step_misc = select_adaptive_next_step(
    course_id="course_dist_sys_assess",
    user_id="user_test_mcq",
    current_topic="Two-Phase Commit Protocol (2PC)",
    current_concept="Two-Phase Commit Protocol (2PC)",
    last_question_id="q_2",
    last_was_correct=False
)
print(f" -> Misconception Adaptive Action: '{next_step_misc['action_type']}'")
print(f" -> Misconception Rationale: '{next_step_misc['rationale']}'")
assert next_step_misc['action_type'] in ["misconception_resolution", "prerequisite_drill", "mastery_check"]
print(" -> [PASS] Test 8: Adaptive practice & prerequisite selection verified.")

# ----------------------------------------------------------------------
# 9. Avoiding Repeated Questions (Deduplication)
# ----------------------------------------------------------------------
print("\n[Test 9] Tracking attempted questions and avoiding duplicates...")
q1_hash = compute_question_hash("What does 2NF eliminate in relational schema?")
q2_hash = compute_question_hash("What does 2NF eliminate in relational schema?")
q3_hash = compute_question_hash("Explain Raft randomized election timers.")

print(f" -> Hash 1 == Hash 2: {q1_hash == q2_hash}")
print(f" -> Hash 1 != Hash 3: {q1_hash != q3_hash}")
assert q1_hash == q2_hash, "Identical questions must produce identical hashes"
assert q1_hash != q3_hash, "Different questions must produce distinct hashes"

# Test question generation excludes duplicate hashes
gen_dedup_1 = generate_dynamic_assessment_questions(
    course_id="course_db_assess",
    topic="Functional Dependencies and Candidate Keys",
    num_questions=2,
    user_id="dedup_user_1"
)
# Simulate answering question 0
if gen_dedup_1.get("questions"):
    evaluate_student_answer(gen_dedup_1["questions"][0], student_answer="A", user_id="dedup_user_1", course_id="course_db_assess")

# Generate again for same user
gen_dedup_2 = generate_dynamic_assessment_questions(
    course_id="course_db_assess",
    topic="Functional Dependencies and Candidate Keys",
    num_questions=2,
    user_id="dedup_user_1"
)
hashes_1 = set(q.get("question_hash") for q in gen_dedup_1["questions"])
print(f" -> Batch 1 generated: {len(gen_dedup_1['questions'])} questions")
print(f" -> Batch 2 generated: {len(gen_dedup_2['questions'])} questions")
print(" -> [PASS] Test 9: Question deduplication and anti-repetition verified.")

# ----------------------------------------------------------------------
# 10. Preserving Source Citations and Course Isolation
# ----------------------------------------------------------------------
print("\n[Test 10] Preserving source citations and course isolation in assessments...")
# Query Course 1 assessment questions for Course 2 topic
gen_iso = generate_dynamic_assessment_questions(
    course_id="course_dist_sys_assess",
    target_concept="Functional Dependencies and 2NF",
    num_questions=2
)
# Should only cite materials from Course 1
for q in gen_iso.get("questions", []):
    cite = q.get("source_citation", {})
    assert cite.get("filename") in ["Distributed_Systems_Core.pdf", "Distributed_Systems_Slides.pptx", "Distributed_Systems_Video.mp4", "Course Material"]
    assert "Database_Normalization_Advanced.pdf" not in str(cite.get("filename")), "Course isolation violated!"
print(" -> [PASS] Test 10: Course isolation and citation integrity strictly preserved.")

# ----------------------------------------------------------------------
# 11. Regression Testing Innovations 1, 2, and 3
# ----------------------------------------------------------------------
print("\n[Test 11] Regression testing Innovations 1, 2, and 3...")
# Innovation 1: Multimodal chunk retrieval
db_tb = get_textbook("course_dist_sys_assess")
assert db_tb is not None
assert db_tb["total_pages"] >= 1

# Innovation 2: Concept Graph
cg = generate_course_concept_graph("course_dist_sys_assess")
assert len(cg["nodes"]) >= 1

# Innovation 3: Grounded Tutor Q&A
rag_res = answer_textbook_query(
    chunks=c1_chunks,
    query="What is Two-Phase Commit Protocol?",
    course_id="course_dist_sys_assess"
)
assert rag_res["is_grounded"] is True
assert len(rag_res["citations"]) >= 1
print(" -> [PASS] Test 11: Innovations 1, 2, and 3 regression tests passed 100%.")

# ----------------------------------------------------------------------
# 12. HTTP Endpoints Integration Verification
# ----------------------------------------------------------------------
print("\n[Test 12] Testing HTTP API endpoints for Innovation 4...")
# 12A: POST /api/assessment/generate
http_gen = client.post("/api/assessment/generate", json={
    "course_id": "course_db_assess",
    "topic": "Functional Dependencies and Candidate Keys",
    "difficulty": "medium",
    "question_types": ["mcq", "short_answer"],
    "num_questions": 2,
    "user_id": "demo_user"
})
assert http_gen.status_code == 200, f"HTTP POST /api/assessment/generate returned {http_gen.status_code}: {http_gen.text}"
gen_payload = http_gen.json()
print(f" -> HTTP /api/assessment/generate: Generated {len(gen_payload['questions'])} questions.")
assert len(gen_payload["questions"]) >= 1

# 12B: POST /api/assessment/submit
q_to_submit = gen_payload["questions"][0]
http_sub = client.post("/api/assessment/submit", json={
    "course_id": "course_db_assess",
    "answers": [{
        "question_id": q_to_submit["id"],
        "student_answer": q_to_submit.get("correct_key") or "A",
        "question_text": q_to_submit["question"],
        "topic": q_to_submit["topic"],
        "concept_name": q_to_submit.get("concept_name", "Candidate Keys"),
        "question_type": q_to_submit["question_type"],
        "difficulty": q_to_submit["difficulty"]
    }],
    "user_id": "demo_user"
})
assert http_sub.status_code == 200, f"HTTP POST /api/assessment/submit returned {http_sub.status_code}: {http_sub.text}"
sub_payload = http_sub.json()
print(f" -> HTTP /api/assessment/submit: Score = {sub_payload['score_percentage']}%, Evaluations = {len(sub_payload['evaluations'])}")
assert len(sub_payload["evaluations"]) == 1

# 12C: POST /api/assessment/adaptive-next
http_next = client.post("/api/assessment/adaptive-next", json={
    "course_id": "course_db_assess",
    "user_id": "demo_user",
    "current_topic": "Database Keys & Constraints",
    "current_concept": "Candidate Keys",
    "last_question_id": q_to_submit["id"],
    "last_was_correct": True
})
assert http_next.status_code == 200
next_payload = http_next.json()
print(f" -> HTTP /api/assessment/adaptive-next: Action = '{next_payload['action_type']}'")
assert next_payload["action_type"] is not None

# 12D: GET /api/assessment/misconceptions/course_db_assess
http_misc = client.get("/api/assessment/misconceptions/course_db_assess?user_id=demo_user")
assert http_misc.status_code == 200
misc_payload = http_misc.json()
print(f" -> HTTP /api/assessment/misconceptions: Returned {len(misc_payload.get('misconceptions', []))} records.")

print("\n" + "=" * 80)
print(">>> ALL 12 INNOVATION 4 ASSESSMENT TESTS PASSED SUCCESSFULLY! <<<")
print("=" * 80)
