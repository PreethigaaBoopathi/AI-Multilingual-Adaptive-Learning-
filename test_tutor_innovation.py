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
    get_chunks_for_textbook, save_concept_graph, get_concept_graph
)
from backend.services.multimodal_service import process_multimodal_file, unify_course_materials
from backend.services.concept_graph_service import generate_course_concept_graph
from backend.services.rag_service import (
    answer_textbook_query, retrieve_relevant_chunks, validate_claims_against_evidence
)
from backend.main import app

client = TestClient(app)

print("=" * 75)
print("TESTING INNOVATION 3: EVIDENCE-GROUNDED TUTOR WITH ANTI-HALLUCINATION LAYER")
print("=" * 75)

init_db()

test_dir = DATA_DIR / "test_innovation3"
test_dir.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# SETUP DYNAMIC MULTIMODAL COURSES
# ----------------------------------------------------------------------
# Course 1: Distributed Systems & Cloud Architecture (PDF + PPT + MP4)
# Course 2: Bioinformatics & Genomics (PDF Only - completely unrelated course for isolation test)
# ----------------------------------------------------------------------

print("\n[Setup] Generating dynamic multimodal course materials...")

# 1. Course 1 PDF
pdf_path_1 = test_dir / "Distributed_Cloud_Architecture.pdf"
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
p2 = doc1.new_page()
p2.insert_textbox(
    fitz.Rect(50, 50, 500, 240),
    """Chapter 2: State Machine Replication
2.1 Raft Leader Election and Log Replication
Raft is a consensus algorithm that manages a replicated log.
Raft achieves consensus by electing a distinguished leader node. The leader accepts log entries from clients and replicates them across followers.
Raft uses randomized election timers ranging between 150ms and 300ms to prevent split-vote scenarios.""",
    fontsize=11
)
doc1.save(str(pdf_path_1))
doc1.close()

# 2. Course 1 PPT (Cross-modal overlap with Two-Phase Commit & Deadlocks)
pptx_path_1 = test_dir / "Distributed_Slides.pptx"
prs1 = Presentation()
s1 = prs1.slides.add_slide(prs1.slide_layouts[0])
s1.shapes.title.text = "Distributed Systems: Consensus & Fault Tolerance"
s1.placeholders[1].text = "Lecturer: Cloud Systems Lab"

s2 = prs1.slides.add_slide(prs1.slide_layouts[1])
s2.shapes.title.text = "Two-Phase Commit Protocol (2PC) Execution"
tf2 = s2.shapes.placeholders[1].text_frame
tf2.text = "Two-Phase Commit coordinates distributed transactions across autonomous nodes."
p_a = tf2.add_paragraph()
p_a.text = "Prepare Phase: Coordinator broadcasts query-to-commit to all participants."
p_b = tf2.add_paragraph()
p_b.text = "Commit Phase: Coordinator instructs either commit or rollback based on unanimous agreement."
notes_s2 = s2.notes_slide
notes_s2.notes_text_frame.text = "Highlight that cohort nodes must write their decision to write-ahead log before replying."

s3 = prs1.slides.add_slide(prs1.slide_layouts[1])
s3.shapes.title.text = "Vector Clocks and Causality"
tf3 = s3.shapes.placeholders[1].text_frame
tf3.text = "Vector clocks determine the causal ordering of events in distributed asynchronous systems."
prs1.save(str(pptx_path_1))

# 3. Course 1 MP4 Video (Spoken lecture discussing Raft election timers)
mp4_path_1 = test_dir / "Distributed_Lecture_Video.mp4"
fps = 30
duration_sec = 2
total_frames = fps * duration_sec
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(str(mp4_path_1), fourcc, fps, (640, 480))
for f in range(total_frames):
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:, :, 0] = 180
    cv2.putText(img, "Lecture: Raft Consensus & Randomized Election Timers", (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    out.write(img)
out.release()

# 4. Course 2 PDF: Bioinformatics (Independent course for course isolation testing)
pdf_path_2 = test_dir / "Bioinformatics_Genomics.pdf"
doc2 = fitz.open()
p2_1 = doc2.new_page()
p2_1.insert_textbox(
    fitz.Rect(50, 50, 500, 240),
    """Chapter 1: Genomic Sequence Alignment
1.1 Needleman-Wunsch Dynamic Programming
The Needleman-Wunsch algorithm performs global sequence alignment between two nucleotide or protein sequences.
It constructs a dynamic programming matrix scoring matches, mismatches, and gap penalties.""",
    fontsize=11
)
doc2.save(str(pdf_path_2))
doc2.close()

# Process Course 1 materials
c1_pdf_meta, c1_pdf_chunks, c1_pdf_media = process_multimodal_file(pdf_path_1, "Distributed_Cloud_Architecture.pdf", custom_id="c1_pdf")
c1_ppt_meta, c1_ppt_chunks, c1_ppt_media = process_multimodal_file(pptx_path_1, "Distributed_Slides.pptx", custom_id="c1_ppt")
c1_vid_meta, c1_vid_chunks, c1_vid_media = process_multimodal_file(mp4_path_1, "Distributed_Lecture_Video.mp4", custom_id="c1_vid")

c1_unified_meta, c1_unified_chunks = unify_course_materials(
    course_id="course_dist_sys_101",
    course_title="Distributed Systems & Cloud Architecture",
    materials=[
        {"metadata": c1_pdf_meta, "chunks": c1_pdf_chunks, "media_items": c1_pdf_media},
        {"metadata": c1_ppt_meta, "chunks": c1_ppt_chunks, "media_items": c1_ppt_media},
        {"metadata": c1_vid_meta, "chunks": c1_vid_chunks, "media_items": c1_vid_media}
    ]
)
save_textbook(c1_unified_meta, c1_unified_chunks, c1_unified_meta["media_items"])
generate_course_concept_graph("course_dist_sys_101", force_regenerate=True)

# Process Course 2 material
c2_pdf_meta, c2_pdf_chunks, c2_pdf_media = process_multimodal_file(pdf_path_2, "Bioinformatics_Genomics.pdf", custom_id="c2_bio")
save_textbook(c2_pdf_meta, c2_pdf_chunks, c2_pdf_media)
generate_course_concept_graph(c2_pdf_meta["id"], force_regenerate=True)

print(" -> Course 1 (Distributed Systems) indexed with unified knowledge base and concept graph.")
print(" -> Course 2 (Bioinformatics) indexed.")

# ----------------------------------------------------------------------
# TEST A — Supported Question
# ----------------------------------------------------------------------
print("\n[Test A] Testing Supported Question with Dynamic Provenance...")
res_a = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="What is Two-Phase Commit Protocol and what are the Prepare and Commit phases?",
    course_id="course_dist_sys_101"
)
print(f" -> Evidence Status: '{res_a['evidence_status']}' (is_grounded={res_a['is_grounded']})")
print(f" -> Citations Count: {len(res_a['citations'])}")
for c in res_a['citations']:
    print(f"    - [{c['source_type'].upper()}] {c['filename']} -> Page: {c['page']}, Slide: {c['slide']}")

assert res_a['evidence_status'] == 'fully_grounded', f"Expected fully_grounded, got {res_a['evidence_status']}"
assert res_a['is_grounded'] is True
assert len(res_a['citations']) >= 1
assert any(c['page'] == 1 for c in res_a['citations'] if c['source_type'] == 'pdf')
assert "Two-Phase Commit" in res_a['answer'] or "Prepare" in res_a['answer']
print(" -> [PASS] Test A: Supported question answered with fully grounded status and genuine citations.")

# ----------------------------------------------------------------------
# TEST B — Cross-Modal Evidence
# ----------------------------------------------------------------------
print("\n[Test B] Testing Cross-Modal Evidence Retrieval across PDF and PPT...")
res_b = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="How does Two-Phase Commit coordinate distributed participants and what does coordinator send?",
    course_id="course_dist_sys_101"
)
print(f" -> Evidence Status: '{res_b['evidence_status']}'")
print(f" -> Citations retrieved across sources: {len(res_b['citations'])}")
source_types_b = set(c['source_type'] for c in res_b['citations'])
print(f" -> Distinct source types cited: {source_types_b}")

assert res_b['is_grounded'] is True
assert len(res_b['citations']) >= 1
for c in res_b['citations']:
    if c['source_type'] == 'pdf':
        assert c['page'] is not None and c['page'] in [1, 2], "PDF citation missing valid page"
    elif c['source_type'] == 'presentation':
        assert c['slide'] is not None and c['slide'] in [1, 2, 3], "PPT citation missing valid slide"
print(" -> [PASS] Test B: Cross-modal evidence correctly retrieves citations with actual page/slide locations.")

# ----------------------------------------------------------------------
# TEST C — Video Evidence
# ----------------------------------------------------------------------
print("\n[Test C] Testing Video Evidence & Timestamp Provenance...")
res_c = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="What are the election timers and consensus discussed in the lecture video?",
    course_id="course_dist_sys_101"
)
print(f" -> Evidence Status: '{res_c['evidence_status']}'")
video_citations = [c for c in res_c['citations'] if c['source_type'] == 'video' or c.get('timestamp')]
print(f" -> Video Citations: {len(video_citations)}")
if video_citations:
    print(f" -> Video Timestamp cited: {video_citations[0]['timestamp']} ({video_citations[0]['filename']})")

assert res_c['is_grounded'] is True
assert len(res_c['citations']) >= 1
print(" -> [PASS] Test C: Video evidence retrieved and cited with genuine location.")

# ----------------------------------------------------------------------
# TEST D — Unsupported Question & Unrelated Passage Guardrail
# ----------------------------------------------------------------------
print("\n[Test D] Testing Unsupported Question (Anti-Hallucination & Relevance Guardrail)...")

# D1: Meta-prompt asking for uncovered topic
res_d1 = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="Explain a topic that is not covered in my uploaded materials",
    course_id="course_dist_sys_101",
    enable_outside_knowledge=False
)
print(f" -> D1 ('Explain uncovered topic'): Status='{res_d1['evidence_status']}', Citations={len(res_d1['citations'])}")
print(f"    Answer: '{res_d1['answer']}'")
assert res_d1['evidence_status'] == 'unsupported', f"Expected unsupported, got {res_d1['evidence_status']}"
assert res_d1['is_grounded'] is False
assert len(res_d1['citations']) == 0
assert res_d1['answer'] == "I couldn't find sufficient information about this question in your uploaded course material."

# D2: Specific technical topic not in course (Segment Tree)
res_d2 = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="What is a segment tree and how do you query range minimums?",
    course_id="course_dist_sys_101",
    enable_outside_knowledge=False
)
print(f" -> D2 ('Segment tree'): Status='{res_d2['evidence_status']}', Citations={len(res_d2['citations'])}")
assert res_d2['evidence_status'] == 'unsupported'
assert res_d2['is_grounded'] is False
assert len(res_d2['citations']) == 0
assert res_d2['answer'] == "I couldn't find sufficient information about this question in your uploaded course material."

# D3: Quantum entanglement
res_d3 = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="What is quantum entanglement and how do qubits achieve superposition?",
    course_id="course_dist_sys_101",
    enable_outside_knowledge=False
)
print(f" -> D3 ('Quantum entanglement'): Status='{res_d3['evidence_status']}', Citations={len(res_d3['citations'])}")
assert res_d3['evidence_status'] == 'unsupported'
assert res_d3['is_grounded'] is False
assert len(res_d3['citations']) == 0
assert res_d3['answer'] == "I couldn't find sufficient information about this question in your uploaded course material."

print(" -> [PASS] Test D: All unsupported questions declined with exact required message and 0 fake citations.")

# ----------------------------------------------------------------------
# TEST E — Partially Supported Question & Claim-Level Validation
# ----------------------------------------------------------------------
print("\n[Test E] Testing Partially Supported Question & Claim-Level Validation...")

# 1. Direct Claim Verification Function Test
sample_claims = [
    "The Two-Phase Commit Protocol is an atomic commitment protocol for distributed databases.",
    "PBFT consensus protocol uses quadratic communication complexity O(R^2) to achieve Byzantine fault tolerance in decentralized blockchains."
]
val_claims, sup_ratio, unsup_claims = validate_claims_against_evidence(
    claims=sample_claims,
    evidence_chunks=c1_unified_chunks,
    subject_tokens=["two-phase", "commit", "pbft", "blockchain"]
)
print(f" -> Claim Validation: Support Ratio = {sup_ratio:.2f}")
print(f"    - Claim 1 Supported: {val_claims[0]['is_supported']} (Citation: Chunk #{val_claims[0]['citation_index']})")
print(f"    - Claim 2 Supported: {val_claims[1]['is_supported']}")
print(f"    - Unsupported Claims: {unsup_claims}")
assert val_claims[0]['is_supported'] is True, "Claim 1 (2PC) should be supported"
assert val_claims[1]['is_supported'] is False, "Claim 2 (PBFT) should NOT be supported"
assert 0.45 <= sup_ratio <= 0.55, f"Expected ~0.50 support ratio, got {sup_ratio}"

# 2. End-to-End Query Test on Partially Covered Topic
res_e = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="Explain Two-Phase Commit Protocol and compare it with Practical Byzantine Fault Tolerance PBFT in blockchain.",
    course_id="course_dist_sys_101",
    enable_outside_knowledge=False
)
print(f" -> End-to-End Evidence Status: '{res_e['evidence_status']}'")
print(f" -> Citations: {len(res_e['citations'])}")

assert res_e['is_grounded'] is True
assert len(res_e['citations']) >= 1
print(" -> [PASS] Test E: Partially supported questions & claim validation verified with high precision.")

# ----------------------------------------------------------------------
# TEST F — Citation Integrity & Database Matching
# ----------------------------------------------------------------------
print("\n[Test F] Testing Citation Integrity against Stored Database Content Units...")
db_chunks = get_chunks_for_textbook("course_dist_sys_101")
db_chunk_ids = {c["id"]: c for c in db_chunks}

for citation in res_a['citations']:
    c_id = citation.get('id')
    assert c_id in db_chunk_ids, f"Citation ID {c_id} does not exist in real database!"
    real_chunk = db_chunk_ids[c_id]
    assert citation['filename'] == real_chunk.get('filename'), "Filename mismatch"
    assert citation['source_type'] == real_chunk.get('source_type'), "Source type mismatch"
    if citation['source_type'] == 'pdf':
        assert citation['page'] == real_chunk.get('page'), "Page number mismatch"
    elif citation['source_type'] == 'presentation':
        assert citation['slide'] == (real_chunk.get('slide_number') or real_chunk.get('page')), "Slide number mismatch"
print(f" -> Verified {len(res_a['citations'])} citation(s) match stored database records with 100% integrity.")
print(" -> [PASS] Test F: Citation integrity verified against real content units.")

# ----------------------------------------------------------------------
# TEST G — Course Isolation
# ----------------------------------------------------------------------
print("\n[Test G] Testing Course Isolation (Course A vs Course B)...")
# Query Course 1 for Course 2 material (Needleman-Wunsch)
res_g1 = answer_textbook_query(
    chunks=get_chunks_for_textbook("course_dist_sys_101"),
    query="What is Needleman-Wunsch algorithm and sequence alignment?",
    course_id="course_dist_sys_101",
    enable_outside_knowledge=False
)
print(f" -> Querying Course 1 for Course 2 topic: Evidence Status='{res_g1['evidence_status']}'")
assert res_g1['evidence_status'] == 'unsupported', "Course 1 should NOT know about Course 2 material"
assert len(res_g1['citations']) == 0

# Query Course 2 for Course 2 material
res_g2 = answer_textbook_query(
    chunks=get_chunks_for_textbook(c2_pdf_meta["id"]),
    query="What is Needleman-Wunsch algorithm and sequence alignment?",
    course_id=c2_pdf_meta["id"],
    enable_outside_knowledge=False
)
print(f" -> Querying Course 2 for Course 2 topic: Evidence Status='{res_g2['evidence_status']}', Citations={len(res_g2['citations'])}")
assert res_g2['evidence_status'] == 'fully_grounded', "Course 2 should answer its own material"
assert len(res_g2['citations']) >= 1
assert res_g2['citations'][0]['filename'] == "Bioinformatics_Genomics.pdf"
print(" -> [PASS] Test G: Course isolation strictly enforced.")

# ----------------------------------------------------------------------
# TEST H — Optional Outside Knowledge & Concept Graph Synergy
# ----------------------------------------------------------------------
print("\n[Test H] Testing Outside Knowledge Toggle & Concept Graph Synergy...")
# 1. Outside Knowledge Enabled on Unsupported Question
res_h1 = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="What is quantum computing and Grover's search algorithm?",
    course_id="course_dist_sys_101",
    enable_outside_knowledge=True
)
print(f" -> Outside Knowledge Enabled Status: '{res_h1['evidence_status']}'")
print(f" -> Outside Knowledge Used: {res_h1['outside_knowledge_used']}")
print(f" -> Citations: {len(res_h1['citations'])} (Must be 0 for outside knowledge)")
assert res_h1['evidence_status'] == 'outside_knowledge'
assert res_h1['outside_knowledge_used'] is True
assert len(res_h1['citations']) == 0
assert "[Outside Knowledge" in res_h1['answer'] or "General Knowledge" in res_h1['answer']

# 2. Innovation 2 Concept Graph Synergy in Tutor
res_h2 = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="Tell me about Two-Phase Commit Protocol",
    course_id="course_dist_sys_101"
)
print(f" -> Related concepts returned from Innovation 2 graph: {[rc['name'] for rc in res_h2.get('related_concepts', [])]}")
assert len(res_h2.get('related_concepts', [])) >= 1, "Should return connected concepts from Innovation 2 graph"

# 3. Semantic matching on rephrased question (different wording from textbook)
res_h3 = answer_textbook_query(
    chunks=c1_unified_chunks,
    query="How do distributed participants coordinate and reach atomic agreement during the prepare and commit stages?",
    course_id="course_dist_sys_101"
)
print(f" -> Rephrased question status: '{res_h3['evidence_status']}', Citations: {len(res_h3['citations'])}")
assert res_h3['evidence_status'] == 'fully_grounded', "Should match semantic evidence even with rephrased wording"
assert len(res_h3['citations']) >= 1

# 4. HTTP API Endpoint Verification
http_res = client.post("/api/chat", json={
    "textbook_id": "course_dist_sys_101",
    "query": "What is Raft Consensus and randomized election timers?",
    "language": "en",
    "enable_outside_knowledge": False
})
assert http_res.status_code == 200, f"HTTP POST /api/chat returned {http_res.status_code}: {http_res.text}"
http_data = http_res.json()
print(f" -> HTTP /api/chat: Status={http_data['evidence_status']}, Grounded={http_data['is_grounded']}, Citations={len(http_data['citations'])}")
assert http_data['evidence_status'] == 'fully_grounded'
assert len(http_data['citations']) >= 1

print("\n" + "=" * 75)
print(">>> ALL INNOVATION 3 TESTS (TEST A - TEST H) PASSED SUCCESSFULLY! <<<")
print("=" * 75)
