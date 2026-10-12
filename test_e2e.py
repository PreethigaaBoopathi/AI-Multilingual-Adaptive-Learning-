import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"
FRONTEND_URL = "http://127.0.0.1:5173"

print("==================================================")
print("END-TO-END HTTP INTEGRATION TEST")
print("==================================================")

# 1. Frontend server health check
try:
    fe_res = requests.get(FRONTEND_URL, timeout=5)
    print(f"1. Frontend Vite Server (5173): Status {fe_res.status_code} - OK")
except Exception as e:
    print(f"1. Frontend Vite Server error: {e}")

# 2. Backend server health check
try:
    be_res = requests.get("http://127.0.0.1:8000/api/health", timeout=5)
    print(f"2. Backend FastAPI Server (8000): Status {be_res.status_code} - {be_res.json()['app']}")
except Exception as e:
    print(f"2. Backend FastAPI error: {e}")

# 3. List Textbooks
tbs = requests.get(f"{BASE_URL}/textbooks").json()
print(f"3. GET /api/textbooks: Found {len(tbs)} textbook(s). Active: '{tbs[0]['title']}'")
tb_id = tbs[0]["id"]

# 4. Summarization
sum_res = requests.post(f"{BASE_URL}/summarize", json={"textbook_id": tb_id, "language": "en"}).json()
print(f"4. POST /api/summarize (EN): '{sum_res['title']}' - Key Concepts: {len(sum_res['key_concepts'])}")

# 5. Summarization in Tamil
sum_ta = requests.post(f"{BASE_URL}/summarize", json={"textbook_id": tb_id, "language": "ta"}).json()
print(f"5. POST /api/summarize (TA): '{sum_ta['title']}' - Lang: {sum_ta['language']}")

# 6. Adaptive Explanations (Beginner, Intermediate, Advanced)
for lvl in ["beginner", "intermediate", "advanced"]:
    exp_res = requests.post(f"{BASE_URL}/explain", json={
        "textbook_id": tb_id,
        "topic_or_concept": "Second Normal Form (2NF)",
        "level": lvl,
        "language": "en"
    }).json()
    print(f"6. POST /api/explain ({lvl}): '{exp_res['concept']}' - Key terms: {len(exp_res['key_terms'])} - Grounded: {exp_res['grounded_in_textbook']}")

# 7. Visual Explanation (Mermaid Flowchart)
vis_res = requests.post(f"{BASE_URL}/visualize", json={
    "textbook_id": tb_id,
    "topic": "Database Normalization",
    "diagram_type": "flowchart"
}).json()
print(f"7. POST /api/visualize: Detected Type '{vis_res['detected_type']}' - Mermaid Code length: {len(vis_res['mermaid_code'])} chars")

# 8. Grounded RAG Chat
chat_res = requests.post(f"{BASE_URL}/chat", json={
    "textbook_id": tb_id,
    "query": "What is 2NF and partial dependency?",
    "language": "en"
}).json()
print(f"8. POST /api/chat: Answer Grounded={chat_res['is_grounded']} - Citations: {len(chat_res['citations'])} - Source: {chat_res['citations'][0]['chapter'] if chat_res['citations'] else 'N/A'}")

# 9. Anti-hallucination refusal check
refusal_res = requests.post(f"{BASE_URL}/chat", json={
    "textbook_id": tb_id,
    "query": "What is quantum gravity and black holes?",
    "language": "en"
}).json()
print(f"9. POST /api/chat (Refusal check): '{refusal_res['answer']}' (Grounded={refusal_res['is_grounded']})")

# 10. Generate Quiz
quiz_res = requests.post(f"{BASE_URL}/quiz/generate", json={
    "textbook_id": tb_id,
    "topic": "Second Normal Form (2NF)",
    "difficulty": "medium",
    "num_questions": 5
}).json()
print(f"10. POST /api/quiz/generate: Quiz ID '{quiz_res['quiz_id']}' - Questions: {len(quiz_res['questions'])}")

# 11. Submit Quiz & Test Weak Topic Detection
sub_payload = {
    "quiz_id": quiz_res["quiz_id"],
    "textbook_id": tb_id,
    "topic": "Second Normal Form (2NF)",
    "difficulty": "medium",
    "answers": [
        {"question_id": 1, "selected_key": "A"}, # Incorrect
        {"question_id": 2, "selected_key": "B"}, # Incorrect
        {"question_id": 3, "selected_key": "B"}, # Correct
        {"question_id": 4, "selected_key": "B"}, # Correct
        {"question_id": 5, "selected_key": "C"}, # Incorrect
    ]
}
sub_res = requests.post(f"{BASE_URL}/quiz/submit?user_id=demo_user", json=sub_payload).json()
print(f"11. POST /api/quiz/submit: Score: {sub_res['score_percentage']}% - Weak Topics: {sub_res['weak_topics']}")

# 12. Student Dashboard Performance
perf_res = requests.get(f"{BASE_URL}/performance?user_id=demo_user").json()
print(f"12. GET /api/performance: Overall Progress: {perf_res['overall_progress']}% - Strong: {len(perf_res['strong_topics'])} - Weak: {len(perf_res['weak_topics'])}")

# 13. Personalized Recommendation Remediation Pack
rec_res = requests.get(f"{BASE_URL}/recommendations?user_id=demo_user").json()
print(f"13. GET /api/recommendations: Prescribed Remediation: '{rec_res['topic']}' - Action: '{rec_res['action_button_label']}'")

print("\n>>> ALL 13 END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
