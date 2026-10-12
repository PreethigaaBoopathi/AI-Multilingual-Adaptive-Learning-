import sys
import io
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.main import app
from backend.config import DATA_DIR

client = TestClient(app)

print("=" * 60)
print("TESTING FASTAPI HTTP ENDPOINTS & MULTIMODAL UPLOADS")
print("=" * 60)

# 1. Health check
res = client.get("/api/health")
assert res.status_code == 200, f"Health check failed: {res.status_code}"
print("1. GET /api/health -> Status 200 OK")

# 2. List textbooks / materials
res = client.get("/api/textbooks")
assert res.status_code == 200, f"List textbooks failed: {res.status_code}"
materials = res.json()
print(f"2. GET /api/textbooks -> Found {len(materials)} materials in knowledge base")

test_dir = DATA_DIR / "test_multimodal"

# 3. Test HTTP Upload of PDF
pdf_file = test_dir / "Computer_Networks_Principles.pdf"
if pdf_file.exists():
    with open(pdf_file, "rb") as f:
        res = client.post("/api/upload", files={"file": ("Computer_Networks_Principles.pdf", f, "application/pdf")})
    assert res.status_code == 200, f"PDF Upload failed: {res.text}"
    pdf_resp = res.json()
    print(f"3. POST /api/upload (PDF) -> '{pdf_resp['metadata']['title']}' (Pages: {pdf_resp['metadata']['total_pages']}, Images: {pdf_resp['metadata']['extracted_images_count']})")

# 4. Test HTTP Upload of PPTX
pptx_file = test_dir / "Operating_Systems_Concurrency.pptx"
if pptx_file.exists():
    with open(pptx_file, "rb") as f:
        res = client.post("/api/upload", files={"file": ("Operating_Systems_Concurrency.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")})
    assert res.status_code == 200, f"PPTX Upload failed: {res.text}"
    ppt_resp = res.json()
    print(f"4. POST /api/upload (PPTX) -> '{ppt_resp['metadata']['title']}' (Slides: {ppt_resp['metadata']['total_slides']}, Tables: {ppt_resp['metadata']['extracted_tables_count']})")

# 5. Test HTTP Upload of MP4
mp4_file = test_dir / "Machine_Learning_Lecture_01.mp4"
if mp4_file.exists():
    with open(mp4_file, "rb") as f:
        res = client.post("/api/upload", files={"file": ("Machine_Learning_Lecture_01.mp4", f, "video/mp4")})
    assert res.status_code == 200, f"MP4 Upload failed: {res.text}"
    mp4_resp = res.json()
    print(f"5. POST /api/upload (MP4) -> '{mp4_resp['metadata']['title']}' (Duration: {mp4_resp['metadata']['duration_str']}, Keyframes: {mp4_resp['metadata']['extracted_images_count']})")

# 6. Test HTTP Upload of Invalid/Unsupported format
with open(pdf_file, "rb") as f:
    res = client.post("/api/upload", files={"file": ("unsupported.docx", f, "application/octet-stream")})
assert res.status_code == 400, "Should have returned 400 for unsupported file format"
print(f"6. POST /api/upload (Unsupported .docx) -> Status 400 Error handled: {res.json()['detail']}")

# 7. Test RAG Chat query with newly uploaded PPT material
ppt_id = ppt_resp['metadata']['id']
res = client.post("/api/chat", json={"textbook_id": ppt_id, "query": "What are the deadlock conditions?", "language": "en"})
assert res.status_code == 200, f"Chat query failed: {res.text}"
chat_data = res.json()
print(f"7. POST /api/chat (Query on uploaded PPTX) -> Grounded={chat_data['is_grounded']}, Citations={len(chat_data['citations'])}")
if chat_data['citations']:
    c = chat_data['citations'][0]
    print(f"   Citation: Slide {c.get('slide') or c.get('page')} | Chapter: {c['chapter']}")

print("\n" + "=" * 60)
print(">>> ALL HTTP UPLOAD & MULTIMODAL API TESTS PASSED! <<<")
print("=" * 60)
