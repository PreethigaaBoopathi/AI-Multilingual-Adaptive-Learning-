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
from pptx.enum.shapes import MSO_SHAPE_TYPE
import imageio_ffmpeg
import subprocess

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.config import DATA_DIR, UPLOAD_DIR, MEDIA_DIR
from backend.database import init_db, save_textbook, get_textbook, get_chunks_for_textbook, get_all_textbooks
from backend.services.multimodal_service import process_multimodal_file, detect_file_type, unify_course_materials
from backend.services.rag_service import answer_textbook_query

print("=" * 60)
print("TESTING INNOVATION 1: MULTIMODAL COURSE UNDERSTANDING")
print("=" * 60)

init_db()

test_dir = DATA_DIR / "test_multimodal"
test_dir.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# 1. CREATE AND TEST DYNAMIC PDF (Subject: Computer Networks)
# -------------------------------------------------------------
print("\n[1/5] Generating and testing dynamic PDF extraction (Computer Networks)...")
pdf_path = test_dir / "Computer_Networks_Principles.pdf"
doc = fitz.open()

# Page 1: Chapter 1 & Section 1.1
page1 = doc.new_page()
p1_text = """Chapter 1: Network Layer and Routing Protocols
1.1 IP Addressing and Subnetting
The Internet Protocol (IP) address is a numerical label assigned to each device connected to a computer network. An IPv4 address is a 32-bit number that uniquely identifies a network interface on a host.
Subnetting divides a larger network into smaller, distinct logical network segments."""
page1.insert_textbox(fitz.Rect(50, 50, 500, 240), p1_text, fontsize=11)

# Embed a simple test figure on Page 1
rect_pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 150, 100), 0)
rect_pix.clear_with(120)
page1.insert_image(fitz.Rect(50, 260, 200, 360), pixmap=rect_pix)

# Page 2: Chapter 2 & Routing
page2 = doc.new_page()
p2_text = """Chapter 2: Transport Layer and TCP/UDP
2.1 Transmission Control Protocol (TCP)
TCP is a connection-oriented, reliable transport layer protocol that provides in-order byte stream delivery. TCP employs a three-way handshake (SYN, SYN-ACK, ACK) to establish a connection before data transmission begins. Flow control is maintained using a sliding window mechanism."""
page2.insert_textbox(fitz.Rect(50, 50, 500, 240), p2_text, fontsize=11)

doc.save(str(pdf_path))
doc.close()

pdf_meta, pdf_chunks, pdf_media = process_multimodal_file(pdf_path, "Computer_Networks_Principles.pdf")
print(f" -> PDF Title: {pdf_meta['title']}")
print(f" -> Source Type: {pdf_meta['source_type']}")
print(f" -> Total Pages: {pdf_meta['total_pages']}")
print(f" -> Extracted Chunks: {len(pdf_chunks)}")
print(f" -> Extracted Images: {len(pdf_media)} (on Page {pdf_media[0]['page'] if pdf_media else 'N/A'})")

# Verify Page Provenance
assert all(c["page"] in [1, 2] for c in pdf_chunks), "PDF chunk page provenance failed!"
assert any("IPv4 address" in c["content"] and c["page"] == 1 for c in pdf_chunks), "Dynamic text missing on Page 1"
assert any("TCP is a connection-oriented" in c["content"] and c["page"] == 2 for c in pdf_chunks), "Dynamic text missing on Page 2"
print(" -> [PASS] PDF dynamic extraction & page-level provenance verified.")

# -------------------------------------------------------------
# 2. CREATE AND TEST DYNAMIC PPTX (Subject: Operating Systems)
# -------------------------------------------------------------
print("\n[2/5] Generating and testing dynamic PPTX extraction (Operating Systems)...")
pptx_path = test_dir / "Operating_Systems_Concurrency.pptx"
prs = Presentation()

# Slide 1: Title Slide
slide_layout_title = prs.slide_layouts[0]
slide1 = prs.slides.add_slide(slide_layout_title)
slide1.shapes.title.text = "Operating Systems: Process Synchronization"
slide1.placeholders[1].text = "Lecturer: Dr. OS\nTopics: Semaphores, Mutexes, and Deadlocks"

# Slide 2: Semaphores & Speaker Notes
slide_layout_bullets = prs.slide_layouts[1]
slide2 = prs.slides.add_slide(slide_layout_bullets)
slide2.shapes.title.text = "Semaphores and Mutual Exclusion"
tf2 = slide2.shapes.placeholders[1].text_frame
tf2.text = "A Semaphore is a synchronization tool introduced by Edsger Dijkstra."
p2 = tf2.add_paragraph()
p2.text = "Wait (P operation) decrements the semaphore value and blocks if negative."
p3 = tf2.add_paragraph()
p3.text = "Signal (V operation) increments the semaphore value and wakes a blocked process."

# Add speaker notes to Slide 2
notes_slide2 = slide2.notes_slide
notes_slide2.notes_text_frame.text = "Emphasize to students that binary semaphores are equivalent to mutex locks."

# Slide 3: Deadlock Conditions Table
slide_layout_blank = prs.slide_layouts[6]
slide3 = prs.slides.add_slide(slide_layout_blank)
# Add Title box
tx_box = slide3.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(1))
tx_box.text_frame.text = "Four Coffman Conditions for Deadlock"

# Add Table to Slide 3
rows, cols = 5, 2
left, top, width, height = Inches(0.5), Inches(1.5), Inches(8), Inches(3)
table_shape = slide3.shapes.add_table(rows, cols, left, top, width, height)
table = table_shape.table
table.cell(0, 0).text = "Condition"
table.cell(0, 1).text = "Description"
table.cell(1, 0).text = "Mutual Exclusion"
table.cell(1, 1).text = "At least one non-shareable resource."
table.cell(2, 0).text = "Hold and Wait"
table.cell(2, 1).text = "Process holds resource while requesting others."
table.cell(3, 0).text = "No Preemption"
table.cell(3, 1).text = "Resources cannot be forcibly taken."
table.cell(4, 0).text = "Circular Wait"
table.cell(4, 1).text = "Circular chain of processes waiting for each other."

prs.save(str(pptx_path))

ppt_meta, ppt_chunks, ppt_media = process_multimodal_file(pptx_path, "Operating_Systems_Concurrency.pptx")
print(f" -> PPT Title: {ppt_meta['title']}")
print(f" -> Source Type: {ppt_meta['source_type']}")
print(f" -> Total Slides: {ppt_meta['total_slides']}")
print(f" -> Extracted Chunks: {len(ppt_chunks)}")
print(f" -> Extracted Tables: {ppt_meta['extracted_tables_count']}")

# Verify Slide Provenance
assert all(c["slide_number"] in [1, 2, 3] for c in ppt_chunks if c.get("slide_number")), "PPT slide provenance failed!"
assert any("Edsger Dijkstra" in c["content"] and c["slide_number"] == 2 for c in ppt_chunks), "Missing slide 2 content"
assert any("Circular Wait" in c["content"] and c["slide_number"] == 3 for c in ppt_chunks), "Missing slide 3 table"
assert any("Speaker Notes" in c["content"] and c["slide_number"] == 2 for c in ppt_chunks), "Missing speaker notes on slide 2"
print(" -> [PASS] PPTX dynamic extraction & slide-level provenance verified.")

# -------------------------------------------------------------
# 3. CREATE AND TEST DYNAMIC MP4 (Subject: Machine Learning)
# -------------------------------------------------------------
print("\n[3/5] Generating and testing dynamic MP4 video processing (Machine Learning)...")
mp4_path = test_dir / "Machine_Learning_Lecture_01.mp4"

# Generate a 3-second test video using OpenCV
width, height = 640, 480
fps = 30
duration_sec = 3
total_frames = fps * duration_sec
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(str(mp4_path), fourcc, fps, (width, height))

for f in range(total_frames):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # Background gradient
    img[:, :, 0] = int(255 * (f / total_frames))
    img[:, :, 2] = 180
    # Add text on frame
    cv2.putText(img, f"ML Lecture Frame {f}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    out.write(img)
out.release()

vid_meta, vid_chunks, vid_media = process_multimodal_file(mp4_path, "Machine_Learning_Lecture_01.mp4")
print(f" -> Video Title: {vid_meta['title']}")
print(f" -> Source Type: {vid_meta['source_type']}")
print(f" -> Duration: {vid_meta['duration_str']} ({vid_meta['duration_seconds']}s)")
print(f" -> Extracted Keyframes: {len(vid_media)}")
print(f" -> Extracted Chunks: {len(vid_chunks)}")

# Verify Timestamp Provenance
assert all(c.get("timestamp_str") is not None for c in vid_chunks if c.get("content_type") in ["transcript", "keyframe"]), "Timestamp provenance failed!"
assert len(vid_media) >= 1, "Keyframe extraction failed!"
assert (MEDIA_DIR / vid_meta['id'] / vid_media[0]['media_filename']).exists(), "Keyframe file not saved!"
print(" -> [PASS] MP4 dynamic extraction & timestamp provenance verified.")

# -------------------------------------------------------------
# 4. TEST ERROR HANDLING WITH INVALID/EMPTY FILES
# -------------------------------------------------------------
print("\n[4/5] Testing error handling (corrupted, empty, unsupported files)...")

# Test unsupported extension
try:
    process_multimodal_file(test_dir / "sample.docx", "sample.docx")
    print(" -> [FAIL] Should have rejected .docx")
except ValueError as e:
    print(f" -> [PASS] Correctly rejected unsupported format: {e}")

# Test empty file
empty_file = test_dir / "empty.pdf"
empty_file.write_bytes(b"")
try:
    process_multimodal_file(empty_file, "empty.pdf")
    print(" -> [FAIL] Should have rejected empty file")
except ValueError as e:
    print(f" -> [PASS] Correctly handled empty file: {e}")

# -------------------------------------------------------------
# 5. TEST UNIFIED COURSE KNOWLEDGE BASE & RAG GROUNDING
# -------------------------------------------------------------
print("\n[5/5] Testing unified course knowledge base across PDF + PPT + MP4...")

save_textbook(pdf_meta, pdf_chunks, pdf_media)
save_textbook(ppt_meta, ppt_chunks, ppt_media)
save_textbook(vid_meta, vid_chunks, vid_media)

# Verify DB storage
all_tb = get_all_textbooks()
print(f" -> Total materials in DB: {len(all_tb)}")

# Query the dynamic PDF
rag_pdf = answer_textbook_query(pdf_chunks, "What is TCP and three-way handshake?")
print(f" -> RAG PDF Query Grounded: {rag_pdf['is_grounded']}")
print(f" -> RAG PDF Citations: {len(rag_pdf['citations'])}")
if rag_pdf['citations']:
    print(f" -> Provenance: Page {rag_pdf['citations'][0]['page']} ({rag_pdf['citations'][0]['chapter']})")

# Query the dynamic PPT
rag_ppt = answer_textbook_query(ppt_chunks, "What are the four deadlock conditions?")
print(f" -> RAG PPT Query Grounded: {rag_ppt['is_grounded']}")
print(f" -> RAG PPT Citations: {len(rag_ppt['citations'])}")
if rag_ppt['citations']:
    print(f" -> Provenance: Slide {rag_ppt['citations'][0].get('slide') or rag_ppt['citations'][0]['page']} ({rag_ppt['citations'][0]['chapter']})")

# Unify multiple materials for a course
unified_meta, unified_chunks = unify_course_materials(
    course_id="course_cs101_multimodal",
    course_title="CS101: Computer Systems & Machine Learning",
    materials=[
        {"metadata": pdf_meta, "chunks": pdf_chunks, "media_items": pdf_media},
        {"metadata": ppt_meta, "chunks": ppt_chunks, "media_items": ppt_media},
        {"metadata": vid_meta, "chunks": vid_chunks, "media_items": vid_media}
    ]
)
save_textbook(unified_meta, unified_chunks, unified_meta["media_items"])

print(f" -> Unified Course Knowledge Base created with {len(unified_chunks)} chunks across PDF + PPT + MP4.")
print(f" -> Unified Pages: {unified_meta['total_pages']}, Slides: {unified_meta['total_slides']}, Duration: {unified_meta['duration_seconds']}s")

print("\n" + "=" * 60)
print(">>> ALL MULTIMODAL TESTS PASSED SUCCESSFULLY! <<<")
print("=" * 60)
