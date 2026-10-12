import sys
import io
from pathlib import Path
from fastapi.testclient import TestClient

# Force UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.main import app

client = TestClient(app)

print("=" * 70)
print("TESTING INNOVATION 2: FASTAPI HTTP ENDPOINTS & PROVENANCE INTEGRATION")
print("=" * 70)

# 1. Test Health Check endpoint
print("\n[1/4] Testing /api/health...")
res = client.get("/api/health")
assert res.status_code == 200
data = res.json()
assert any("concept-graph" in ep for ep in data["endpoints"]), "Concept graph endpoints not advertised in health check"
print(" -> [PASS] Health check verified.")

# 2. Test Concept Graph for default textbook
print("\n[2/4] Testing GET /api/concept-graph/tb_dbms_norm_001...")
res = client.get("/api/concept-graph/tb_dbms_norm_001")
assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
graph = res.json()
print(f" -> Course ID: {graph['course_id']}")
print(f" -> Total Nodes: {len(graph['nodes'])}")
print(f" -> Total Edges: {len(graph['edges'])}")
print(f" -> Total Topics: {len(graph['topics'])}")
print(f" -> Prerequisites: {graph['stats']['total_prerequisites']}")
print(f" -> Learning Paths: {graph.get('learning_paths')}")

assert len(graph["nodes"]) > 0, "No nodes returned"
assert len(graph["edges"]) > 0, "No edges returned"
assert len(graph["topics"]) > 0, "No topics returned"
print(" -> [PASS] Concept graph endpoint verified.")

# 3. Test Granular Concept Details & Evidence
print("\n[3/4] Testing GET /api/concept-graph/tb_dbms_norm_001/concept/{concept_id}...")
first_node = graph["nodes"][0]
concept_id = first_node["id"]
res = client.get(f"/api/concept-graph/tb_dbms_norm_001/concept/{concept_id}")
assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
details = res.json()
print(f" -> Concept Name: {details['concept']['name']}")
print(f" -> Sources Count: {len(details['sources'])}")
print(f" -> Prerequisites: {len(details['prerequisites'])}")
print(f" -> Dependents: {len(details['dependents'])}")
print(f" -> Related: {len(details['related_concepts'])}")

assert details["concept"]["name"] == first_node["name"]
assert len(details["sources"]) > 0, "Sources missing"
print(" -> [PASS] Granular concept details and provenance verified.")

# 4. Test Learning Paths endpoint
print("\n[4/4] Testing GET /api/concept-graph/tb_dbms_norm_001/learning-paths...")
res = client.get("/api/concept-graph/tb_dbms_norm_001/learning-paths")
assert res.status_code == 200
paths_data = res.json()
print(f" -> Learning Paths returned: {paths_data['learning_paths']}")
assert "learning_paths" in paths_data
print(" -> [PASS] Learning paths endpoint verified.")

print("\n" + "=" * 70)
print(">>> ALL HTTP ENDPOINT INTEGRATION TESTS PASSED! <<<")
print("=" * 70)
