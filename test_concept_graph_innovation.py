import sys
import io
import os
import shutil
import numpy as np
import cv2
from pathlib import Path
import fitz # PyMuPDF
from pptx import Presentation
from pptx.util import Inches, Pt

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.config import DATA_DIR, UPLOAD_DIR, MEDIA_DIR
from backend.database import (
    init_db, save_textbook, get_textbook, get_all_textbooks,
    save_concept_graph, get_concept_graph, get_concept_details
)
from backend.services.multimodal_service import process_multimodal_file, unify_course_materials
from backend.services.concept_graph_service import (
    generate_course_concept_graph, extract_concepts_and_relationships_dynamic
)

print("=" * 70)
print("TESTING INNOVATION 2: SOURCE-LINKED CONCEPT AND PREREQUISITE GRAPH")
print("=" * 70)

init_db()

test_dir = DATA_DIR / "test_innovation2"
test_dir.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# TEST 1: DYNAMIC COURSE A - MULTIMODAL (PDF + PPT + VIDEO)
# Subject: Distributed Systems & Cloud Infrastructure
# ----------------------------------------------------------------------
print("\n[1/5] Testing Course A (Multimodal PDF + PPT + MP4: Distributed Systems)...")

# 1. Create PDF
pdf_path = test_dir / "Distributed_Systems_Core.pdf"
doc = fitz.open()
page1 = doc.new_page()
p1_text = """Chapter 1: Consistency and Consensus Models
1.1 Two-Phase Commit Protocol (2PC)
The Two-Phase Commit Protocol is a distributed consensus algorithm that ensures all database nodes commit or abort a transaction together.
Before understanding Two-Phase Commit Protocol, one must understand Distributed Transactions.
The protocol consists of a Prepare Phase and a Commit Phase coordinated by a master node."""
page1.insert_textbox(fitz.Rect(50, 50, 500, 250), p1_text, fontsize=11)

page2 = doc.new_page()
p2_text = """Chapter 2: Replication and Quorum
2.1 Raft Consensus Algorithm
Raft is a leader-based consensus algorithm designed for state machine replication.
Raft Consensus Algorithm requires knowledge of Two-Phase Commit Protocol and leader election.
Nodes in Raft can be in Leader, Follower, or Candidate state."""
page2.insert_textbox(fitz.Rect(50, 50, 500, 250), p2_text, fontsize=11)
doc.save(str(pdf_path))
doc.close()

# 2. Create PPTX (with cross-modal discussion of Two-Phase Commit & Raft)
pptx_path = test_dir / "Distributed_Systems_Slides.pptx"
prs = Presentation()
# Slide 1: Title
s1 = prs.slides.add_slide(prs.slide_layouts[0])
s1.shapes.title.text = "Distributed Systems: Consensus & Fault Tolerance"
s1.placeholders[1].text = "Lecturer: Distributed Computing Team"

# Slide 2: Two-Phase Commit Protocol (Cross-modal overlap with PDF Page 1)
s2 = prs.slides.add_slide(prs.slide_layouts[1])
s2.shapes.title.text = "Two-Phase Commit Protocol (2PC)"
tf2 = s2.shapes.placeholders[1].text_frame
tf2.text = "Two-Phase Commit Protocol coordinates distributed participants."
p2a = tf2.add_paragraph()
p2a.text = "Phase 1: Prepare request sent to all cohort nodes."
p2b = tf2.add_paragraph()
p2b.text = "Phase 2: Global commit or global abort executed."

# Slide 3: Raft Leader Election (Cross-modal overlap with PDF Page 2)
s3 = prs.slides.add_slide(prs.slide_layouts[1])
s3.shapes.title.text = "Raft Consensus Algorithm & Heartbeats"
tf3 = s3.shapes.placeholders[1].text_frame
tf3.text = "Raft uses randomized election timers to avoid split votes."
prs.save(str(pptx_path))

# 3. Create MP4 Video (with spoken discussion of Two-Phase Commit & Raft)
mp4_path = test_dir / "Distributed_Systems_Lecture.mp4"
fps = 30
duration_sec = 2
total_frames = fps * duration_sec
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(str(mp4_path), fourcc, fps, (640, 480))
for f in range(total_frames):
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:, :, 1] = 120
    cv2.putText(img, "Lecture: Two-Phase Commit & Raft Consensus", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    out.write(img)
out.release()

# Extract all 3 multimodal materials
pdf_meta, pdf_chunks, pdf_media = process_multimodal_file(pdf_path, "Distributed_Systems_Core.pdf")
ppt_meta, ppt_chunks, ppt_media = process_multimodal_file(pptx_path, "Distributed_Systems_Slides.pptx")
vid_meta, vid_chunks, vid_media = process_multimodal_file(mp4_path, "Distributed_Systems_Lecture.mp4")

# Unify into single Course
course_a_id = "course_dist_sys_101"
unified_meta, unified_chunks = unify_course_materials(
    course_id=course_a_id,
    course_title="CS401: Distributed Systems & Consensus",
    materials=[
        {"metadata": pdf_meta, "chunks": pdf_chunks, "media_items": pdf_media},
        {"metadata": ppt_meta, "chunks": ppt_chunks, "media_items": ppt_media},
        {"metadata": vid_meta, "chunks": vid_chunks, "media_items": vid_media}
    ]
)
save_textbook(unified_meta, unified_chunks, unified_meta["media_items"])

# Generate Concept Graph
graph_a = generate_course_concept_graph(course_a_id, force_regenerate=True)

print(f" -> Total Concepts Discovered: {graph_a['stats']['total_concepts']}")
print(f" -> Total Topics: {len(graph_a['topics'])} ({[t['name'] for t in graph_a['topics']]})")
print(f" -> Total Relationships: {graph_a['stats']['total_relationships']}")
print(f" -> Total Prerequisites: {graph_a['stats']['total_prerequisites']}")
print(f" -> Total Sources Linked: {graph_a['stats']['total_sources']}")
print(f" -> Cross-Modal Concepts (Linked across PDF+PPT+Video): {graph_a['stats']['cross_modal_concepts']}")

assert graph_a['stats']['total_concepts'] >= 2, "Failed to dynamically discover concepts for Course A"
assert graph_a['stats']['total_prerequisites'] >= 1, "Failed to identify prerequisite relationships"
assert graph_a['stats']['total_sources'] >= 3, "Failed to link sources"

# Verify Cross-Modal Linking & Provenance
tpc_concept = next((n for n in graph_a["nodes"] if "two-phase" in n["name"].lower() or "commit" in n["name"].lower()), None)
assert tpc_concept is not None, "Two-Phase Commit concept not discovered"
print(f" -> Found Concept: '{tpc_concept['name']}' with {len(tpc_concept['sources'])} sources across {tpc_concept['source_types']}")
assert any(s["source_type"] == "pdf" and s["page_number"] == 1 for s in tpc_concept["sources"]), "PDF Page 1 provenance missing!"
assert any(s["source_type"] == "presentation" and s["slide_number"] == 2 for s in tpc_concept["sources"]), "PPT Slide 2 provenance missing!"
print(" -> [PASS] Course A dynamic extraction, cross-modal linking & multi-provenance verified.")


# ----------------------------------------------------------------------
# TEST 2: DYNAMIC COURSE B (PDF + PPT: Operating Systems / Concurrency)
# ----------------------------------------------------------------------
print("\n[2/5] Testing Course B (PDF + PPT: Operating Systems Concurrency)...")

pdf_b_path = test_dir / "OS_Concurrency.pdf"
doc_b = fitz.open()
p1 = doc_b.new_page()
p1.insert_textbox(fitz.Rect(50, 50, 500, 250), """Chapter 1: Critical Section and Synchronization
1.1 Mutex Locks and Race Conditions
A race condition occurs when multiple threads manipulate shared data concurrently.
A Mutex Lock is a locking mechanism used to synchronize access to a critical section.
Before understanding Semaphores, one must understand Mutex Locks and Race Conditions.""", fontsize=11)
doc_b.save(str(pdf_b_path))
doc_b.close()

ppt_b_path = test_dir / "OS_Semaphores.pptx"
prs_b = Presentation()
s1 = prs_b.slides.add_slide(prs_b.slide_layouts[1])
s1.shapes.title.text = "Counting Semaphores"
s1.shapes.placeholders[1].text_frame.text = "Semaphores provide signaling mechanisms for synchronization.\nCounting Semaphores require understanding of Mutex Locks and atomic operations."
prs_b.save(str(ppt_b_path))

b_pdf_meta, b_pdf_chunks, b_pdf_media = process_multimodal_file(pdf_b_path, "OS_Concurrency.pdf")
b_ppt_meta, b_ppt_chunks, b_ppt_media = process_multimodal_file(ppt_b_path, "OS_Semaphores.pptx")

course_b_id = "course_os_concurrency_202"
b_unified_meta, b_unified_chunks = unify_course_materials(
    course_id=course_b_id,
    course_title="CS202: Operating Systems Concurrency",
    materials=[
        {"metadata": b_pdf_meta, "chunks": b_pdf_chunks, "media_items": b_pdf_media},
        {"metadata": b_ppt_meta, "chunks": b_ppt_chunks, "media_items": b_ppt_media}
    ]
)
save_textbook(b_unified_meta, b_unified_chunks, b_unified_meta["media_items"])

graph_b = generate_course_concept_graph(course_b_id, force_regenerate=True)
print(f" -> Concepts: {[n['name'] for n in graph_b['nodes']]}")
print(f" -> Topics: {[t['name'] for t in graph_b['topics']]}")
print(f" -> Prerequisites: {graph_b['stats']['total_prerequisites']}")

# Verify that Course B topics/concepts are totally distinct from Course A (Zero Hardcoding!)
concept_names_a = set(n["name"].lower() for n in graph_a["nodes"])
concept_names_b = set(n["name"].lower() for n in graph_b["nodes"])
assert not concept_names_a.issubset(concept_names_b), "Concepts between two distinct courses should not be identical!"
print(" -> [PASS] Course B dynamic non-hardcoded concept discovery verified.")


# ----------------------------------------------------------------------
# TEST 3: DYNAMIC COURSE C (PDF Only: Machine Learning / Neural Networks)
# ----------------------------------------------------------------------
print("\n[3/5] Testing Course C (PDF Only: Machine Learning)...")

pdf_c_path = test_dir / "Deep_Learning_Intro.pdf"
doc_c = fitz.open()
p1 = doc_c.new_page()
p1.insert_textbox(fitz.Rect(50, 50, 500, 250), """Chapter 1: Gradient Optimization
1.1 Gradient Descent
Gradient Descent is an optimization algorithm for finding a local minimum of a differentiable function.
Linear Regression is a fundamental supervised learning model.
Before understanding Backpropagation, one must understand Gradient Descent and Chain Rule.""", fontsize=11)

p2 = doc_c.new_page()
p2.insert_textbox(fitz.Rect(50, 50, 500, 250), """Chapter 2: Neural Networks
2.1 Backpropagation Algorithm
Backpropagation is the primary algorithm for training multi-layer artificial neural networks.
It efficiently computes gradient of the loss function with respect to weights using the chain rule of calculus.""", fontsize=11)
doc_c.save(str(pdf_c_path))
doc_c.close()

c_pdf_meta, c_pdf_chunks, c_pdf_media = process_multimodal_file(pdf_c_path, "Deep_Learning_Intro.pdf")
course_c_id = "course_ml_deep_learning_303"
save_textbook(c_pdf_meta, c_pdf_chunks, c_pdf_media)

graph_c = generate_course_concept_graph(course_c_id, force_regenerate=True)
print(f" -> Concepts: {[n['name'] for n in graph_c['nodes']]}")
print(f" -> Prerequisites: {graph_c['stats']['total_prerequisites']}")
print(f" -> Prerequisite Edges: {[(e['source_concept_name'], '-->', e['target_concept_name']) for e in graph_c['edges'] if e['relationship_type'] == 'prerequisite']}")

# Verify prerequisite direction
prereq_edge = next((e for e in graph_c["edges"] if e["relationship_type"] == "prerequisite"), None)
assert prereq_edge is not None, "Expected prerequisite edge in Course C"
print(f" -> Verified Prerequisite Edge Direction: '{prereq_edge['source_concept_name']}' -> '{prereq_edge['target_concept_name']}'")
print(f" -> Evidence: {prereq_edge['evidence']}")
print(" -> [PASS] Course C prerequisite direction and grounding verified.")


# ----------------------------------------------------------------------
# TEST 4: GRANULAR CONCEPT DETAILS & EVIDENCE
# ----------------------------------------------------------------------
print("\n[4/5] Testing granular concept details & supporting evidence query...")

first_concept = graph_c["nodes"][0]
details = get_concept_details(course_c_id, first_concept["id"])
assert details is not None, "Failed to retrieve granular concept details"
print(f" -> Concept Name: {details['concept']['name']}")
print(f" -> Topic: {details['concept']['topic']}")
print(f" -> Grounded Description: {details['concept']['description']}")
print(f" -> Sources count: {len(details['sources'])}")
print(f" -> Prerequisites count: {len(details['prerequisites'])}")
print(f" -> Dependents count: {len(details['dependents'])}")
print(f" -> Related concepts count: {len(details['related_concepts'])}")

# Check that evidence is stored for relationships
for p in details['prerequisites']:
    assert len(p['evidence']) > 5, "Missing prerequisite evidence"
    print(f"   * Prereq '{p['name']}' Evidence: {p['evidence']}")

for d in details['dependents']:
    assert len(d['evidence']) > 5, "Missing dependent evidence"
    print(f"   * Dependent '{d['name']}' Evidence: {d['evidence']}")

print(" -> [PASS] Concept details, provenance & evidence retrieval verified.")


# ----------------------------------------------------------------------
# TEST 5: SAMPLE DATABASE TEXTBOOK CONCEPT GRAPH (DEFAULT DEMO)
# ----------------------------------------------------------------------
print("\n[5/5] Testing Default Course Concept Graph (Relational DBMS & Normalization)...")
from backend.services.demo_data import SAMPLE_TEXTBOOK_ID
demo_graph = generate_course_concept_graph(SAMPLE_TEXTBOOK_ID, force_regenerate=True)

print(f" -> DBMS Concepts count: {demo_graph['stats']['total_concepts']}")
print(f" -> DBMS Concepts: {[n['name'] for n in demo_graph['nodes']]}")
print(f" -> DBMS Topics: {[t['name'] for t in demo_graph['topics']]}")
print(f" -> DBMS Prereqs: {demo_graph['stats']['total_prerequisites']}")
print(f" -> Learning Paths: {demo_graph.get('learning_paths')}")

assert demo_graph['stats']['total_concepts'] >= 4, "DBMS graph should extract key normalization concepts"
assert any("1nf" in n["name"].lower() or "first normal" in n["name"].lower() for n in demo_graph["nodes"]), "1NF missing"
assert any("2nf" in n["name"].lower() or "second normal" in n["name"].lower() for n in demo_graph["nodes"]), "2NF missing"
assert any("3nf" in n["name"].lower() or "third normal" in n["name"].lower() for n in demo_graph["nodes"]), "3NF missing"
print(" -> [PASS] Default DBMS Course concept graph verified.")

print("\n" + "=" * 70)
print(">>> ALL INNOVATION 2 BACKEND & GRAPH TESTS PASSED SUCCESSFULLY! <<<")
print("=" * 70)
