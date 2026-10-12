import sys
import io
from pathlib import Path

# Force UTF-8 output encoding for console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from database import init_db, get_all_textbooks, get_user_performance
from services.demo_data import get_demo_textbook_data
from services.summarization_service import summarize_textbook_content
from services.explanation_service import generate_adaptive_explanation
from services.visualization_service import generate_visual_explanation
from services.rag_service import answer_textbook_query
from services.quiz_service import generate_quiz, evaluate_quiz_submission
from services.adaptive_service import get_personalized_recommendation
from services.translation_service import translate_text

print("1. Testing DB initialization...")
init_db()
print("   DB initialized.")

print("2. Testing Demo Data...")
data = get_demo_textbook_data()
print(f"   Loaded textbook: {data['metadata']['title']} with {len(data['chunks'])} chunks.")

print("3. Testing Summarization (EN & TA)...")
sum_en = summarize_textbook_content(data['chunks'], "First Normal Form (1NF)", language="en")
print(f"   Summary (EN): {sum_en['title']} - Key concepts: {len(sum_en['key_concepts'])}")
sum_ta = summarize_textbook_content(data['chunks'], "First Normal Form (1NF)", language="ta")
print(f"   Summary (TA): {sum_ta['title']}")

print("4. Testing 3-Tier Adaptive Explanation (Beginner, Intermediate, Advanced)...")
exp_beg = generate_adaptive_explanation(data['chunks'], "Second Normal Form (2NF)", level="beginner")
print(f"   Beginner Analogy: {exp_beg['analogy'][:60]}...")
exp_adv = generate_adaptive_explanation(data['chunks'], "Second Normal Form (2NF)", level="advanced")
print(f"   Advanced Key Terms: {[t['term'] for t in exp_adv['key_terms']]}")

print("5. Testing Visualization (Mermaid Flowchart)...")
vis = generate_visual_explanation(data['chunks'], "Database Normalization", diagram_type="flowchart")
print(f"   Detected Type: {vis['detected_type']}")
print(f"   Mermaid Code Lines: {len(vis['mermaid_code'].splitlines())}")

print("6. Testing Grounded Q&A (RAG)...")
qa = answer_textbook_query(data['chunks'], "What is 2NF?", language="en")
print(f"   Answer Grounded: {qa['is_grounded']}, Citations: {len(qa['citations'])}")

print("7. Testing Anti-Hallucination refusal...")
qa_unknown = answer_textbook_query(data['chunks'], "What is quantum gravity and black holes?", language="en")
print(f"   Unknown query refusal: '{qa_unknown['answer']}' (Grounded: {qa_unknown['is_grounded']})")

print("8. Testing Quiz & Adaptive Weak Topic Evaluation...")
quiz = generate_quiz(data['metadata']['id'], "Second Normal Form (2NF)", num_questions=5)
print(f"   Generated {len(quiz['questions'])} questions.")
answers = [
    {"question_id": 1, "selected_key": "A"}, # Incorrect
    {"question_id": 2, "selected_key": "C"}, # Incorrect
    {"question_id": 3, "selected_key": "B"}, # Correct
    {"question_id": 4, "selected_key": "B"}, # Correct
    {"question_id": 5, "selected_key": "C"}, # Incorrect
]
result = evaluate_quiz_submission("demo_user", data['metadata']['id'], quiz['quiz_id'], "Normalization", "medium", answers)
print(f"   Quiz Score: {result['score_percentage']}%, Weak Topics: {result['weak_topics']}")

print("9. Testing Personalized Adaptive Recommendation...")
rec = get_personalized_recommendation("demo_user")
print(f"   Recommended Remediation Topic: {rec['topic']}")
print(f"   Action Button: {rec['action_button_label']}")

print("\n--- ALL BACKEND SERVICES VALIDATED SUCCESSFULLY ---")
