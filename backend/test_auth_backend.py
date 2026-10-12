from fastapi.testclient import TestClient
from main import app
from database import init_db
import uuid

client = TestClient(app)

def test_full_auth_lifecycle():
    init_db()
    
    uid = uuid.uuid4().hex[:6]
    test_email = f"test.student.{uid}@university.edu"
    test_password = "SecurePassword123!"
    
    # 1. Test unauthenticated request to protected endpoint (should return 401)
    res = client.get("/api/textbooks")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "Authentication required" in res.json()["detail"]
    
    # 2. Test registration validation failure (password too short)
    bad_reg = {
        "name": "Test Student",
        "email": test_email,
        "password": "123",
        "confirm_password": "123",
        "organisation": "National University",
        "org_type": "University",
        "department": "Computer Science",
        "role_year": "3rd Year",
        "preferred_language": "en"
    }
    res = client.post("/api/auth/register", json=bad_reg)
    assert res.status_code == 400
    assert "at least 6 characters" in res.json()["detail"]
    
    # 3. Test registration validation failure (password mismatch)
    bad_reg["password"] = test_password
    bad_reg["confirm_password"] = "Mismatch123!"
    res = client.post("/api/auth/register", json=bad_reg)
    assert res.status_code == 400
    assert "do not match" in res.json()["detail"]
    
    # 4. Test valid registration
    valid_reg = {
        "name": "Dr. Aruna Sundaram",
        "email": test_email,
        "password": test_password,
        "confirm_password": test_password,
        "organisation": "PSG Tech",
        "org_type": "College",
        "department": "Data Science",
        "role_year": "Professor",
        "preferred_language": "ta"
    }
    res = client.post("/api/auth/register", json=valid_reg)
    assert res.status_code == 200, f"Registration failed: {res.text}"
    user_data = res.json()
    assert user_data["email"] == test_email
    assert user_data["name"] == "Dr. Aruna Sundaram"
    assert user_data["organisation"] == "PSG Tech"
    assert user_data["org_type"] == "College"
    assert user_data["preferred_language"] == "ta"
    assert "token" in user_data and user_data["token"] is not None
    user_token = user_data["token"]
    
    # 5. Test duplicate registration (should return 400)
    res = client.post("/api/auth/register", json=valid_reg)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]
    
    # 6. Test incorrect password login (should return 401)
    res = client.post("/api/auth/login", json={"email": test_email, "password": "WrongPassword!"})
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]
    
    # 7. Test successful login
    res = client.post("/api/auth/login", json={"email": test_email, "password": test_password, "remember_me": True})
    assert res.status_code == 200
    login_data = res.json()
    assert login_data["email"] == test_email
    assert login_data["token"] is not None
    auth_headers = {"Authorization": f"Bearer {login_data['token']}"}
    
    # 8. Test /api/auth/me with Bearer token
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    me_data = res.json()
    assert me_data["name"] == "Dr. Aruna Sundaram"
    assert me_data["department"] == "Data Science"
    
    # 9. Test protected textbook listing with token
    res = client.get("/api/textbooks", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    
    # 10. Test updating user profile
    update_payload = {
        "name": "Dr. Aruna Sundaram Ph.D",
        "organisation": "IIT Madras",
        "org_type": "University",
        "department": "Artificial Intelligence",
        "role_year": "Senior Research Scientist",
        "preferred_language": "en"
    }
    res = client.put("/api/auth/profile", json=update_payload, headers=auth_headers)
    assert res.status_code == 200
    updated_data = res.json()
    assert updated_data["name"] == "Dr. Aruna Sundaram Ph.D"
    assert updated_data["organisation"] == "IIT Madras"
    assert updated_data["department"] == "Artificial Intelligence"
    assert updated_data["preferred_language"] == "en"
    
    # 11. Test forgot-password and reset-password flow
    res = client.post("/api/auth/forgot-password", json={"email": test_email})
    assert res.status_code == 200
    reset_token = res.json()["reset_token"]
    assert len(reset_token) == 6
    
    # Reset with wrong code
    res = client.post("/api/auth/reset-password", json={"email": test_email, "reset_token": "000000", "new_password": "NewSecretPass456!"})
    assert res.status_code == 400
    
    # Reset with valid code
    res = client.post("/api/auth/reset-password", json={"email": test_email, "reset_token": reset_token, "new_password": "NewSecretPass456!"})
    assert res.status_code == 200
    assert "successfully reset" in res.json()["message"]
    
    # Verify login with new password
    res = client.post("/api/auth/login", json={"email": test_email, "password": "NewSecretPass456!"})
    assert res.status_code == 200
    
    # Verify old password is now rejected
    res = client.post("/api/auth/login", json={"email": test_email, "password": test_password})
    assert res.status_code == 401
    
    print("ALL BACKEND AUTH LIFECYCLE TESTS PASSED PERFECTLY!")

def test_user_isolation():
    uid = uuid.uuid4().hex[:6]
    # User A
    user_a_email = f"user_a_{uid}@test.edu"
    res_a = client.post("/api/auth/register", json={
        "name": "User Alpha",
        "email": user_a_email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    token_a = res_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # User B
    user_b_email = f"user_b_{uid}@test.edu"
    res_b = client.post("/api/auth/register", json={
        "name": "User Beta",
        "email": user_b_email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    token_b = res_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # User A records concept progress
    res_prog_a = client.post("/api/learning-path/progress", json={
        "course_id": "tb_dbms_norm_001",
        "concept_id": "c_bcnf_001",
        "concept_name": "Boyce-Codd Normal Form",
        "status": "mastered",
        "notes": "Alpha secret study notes"
    }, headers=headers_a)
    assert res_prog_a.status_code == 200
    
    # User B queries their progress (should NOT see User A's progress)
    res_prog_b = client.get("/api/learning-path/progress/tb_dbms_norm_001", headers=headers_b)
    assert res_prog_b.status_code == 200
    b_items = res_prog_b.json()["progress_items"]
    assert len(b_items) == 0, f"Expected 0 items for User B, found {len(b_items)}"
    
    # User A queries their progress (should see their own item)
    res_check_a = client.get("/api/learning-path/progress/tb_dbms_norm_001", headers=headers_a)
    assert res_check_a.status_code == 200
    a_items = res_check_a.json()["progress_items"]
    assert len(a_items) == 1
    assert a_items[0]["notes"] == "Alpha secret study notes"
    
    print("USER DATA ISOLATION TEST PASSED PERFECTLY!")

if __name__ == "__main__":
    test_full_auth_lifecycle()
    test_user_isolation()
