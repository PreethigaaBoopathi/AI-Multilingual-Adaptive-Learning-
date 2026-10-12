import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv()

sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()

if not sarvam_key:
    print("[ERROR] SARVAM_API_KEY is missing or empty in .env.")
    sys.exit(1)

print(f"[INFO] SARVAM_API_KEY found (length: {len(sarvam_key)} chars, prefix: {sarvam_key[:4]}...)")

url = "https://api.sarvam.ai/translate"
headers = {
    "Content-Type": "application/json",
    "api-subscription-key": sarvam_key
}

payload = {
    "input": "Hello, welcome to the adaptive learning system.",
    "source_language_code": "en-IN",
    "target_language_code": "ta-IN",
    "mode": "formal",
    "model": "mayura:v1"
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req, timeout=15) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
        parsed = json.loads(body)
        print(f"[SUCCESS EN->TA] HTTP Status: {status_code}")
        print(f"[SUCCESS EN->TA] Translated Text: {parsed.get('translated_text')}")
        
    # Test reverse: ta-IN -> en-IN
    reverse_payload = {
        "input": "இரண்டாம் இயல்பு வடிவம் பகுதி செயல்பாட்டு சார்புநிலையை நீக்குகிறது.",
        "source_language_code": "ta-IN",
        "target_language_code": "en-IN",
        "mode": "formal",
        "model": "mayura:v1"
    }
    rev_req = urllib.request.Request(url, data=json.dumps(reverse_payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(rev_req, timeout=15) as rev_resp:
        rev_parsed = json.loads(rev_resp.read().decode("utf-8"))
        print(f"[SUCCESS TA->EN] HTTP Status: {rev_resp.getcode()}")
        print(f"[SUCCESS TA->EN] Translated Text: {rev_parsed.get('translated_text')}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode("utf-8", errors="ignore")
    print(f"[HTTP ERROR] Code: {e.code}, Reason: {e.reason}, Body: {err_body}")
    sys.exit(2)
except Exception as e:
    print(f"[EXCEPTION] {e}")
    sys.exit(3)
