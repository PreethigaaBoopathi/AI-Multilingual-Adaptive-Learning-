import requests

BASE_URL = "http://localhost:8000"

def test_delete_endpoints():
    # 1. Login to get token
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "alex.rivera@college.edu",
        "password": "DemoPassword123!"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json().get("token") or login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check textbooks list
    list_res = requests.get(f"{BASE_URL}/api/textbooks", headers=headers)
    assert list_res.status_code == 200
    textbooks = list_res.json()
    print(f"Current textbooks count: {len(textbooks)}")

    # 3. Create a sample textbook to test deletion
    sample_res = requests.post(f"{BASE_URL}/api/sample-textbook", headers=headers)
    assert sample_res.status_code == 200
    sample_id = sample_res.json()["textbook"]["id"]
    print(f"Loaded sample textbook for deletion test: {sample_id}")

    # 4. Test deleting that specific textbook
    del_res = requests.delete(f"{BASE_URL}/api/textbooks/{sample_id}", headers=headers)
    assert del_res.status_code == 200, f"Delete failed: {del_res.text}"
    assert del_res.json()["status"] == "success"
    print(f"Successfully deleted specific textbook: {sample_id}")

    # 5. Verify it's no longer present
    get_res = requests.get(f"{BASE_URL}/api/textbook/{sample_id}", headers=headers)
    assert get_res.status_code == 404
    print("Verified textbook no longer exists (HTTP 404).")

    print("\nALL DELETE & REMOVE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_delete_endpoints()
