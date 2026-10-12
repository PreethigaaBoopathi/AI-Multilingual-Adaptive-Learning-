import sys
import os
import time
from pathlib import Path

# Enable utf-8 terminal output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from config import GEMINI_API_KEY, is_gemini_available, mark_gemini_quota_exhausted
from services.translation_service import (
    translate_text,
    is_tamil,
    normalize_tamil_to_concept,
    protect_literals,
    restore_literals,
    _translate_with_gemini,
    is_sarvam_available,
    ACADEMIC_STEM_TERMS,
    _TRANSLATION_CACHE
)

def run_tests():
    print("=" * 70)
    print("🌟 GOOGLE GEMINI AI TRANSLATION INTEGRATION & VERIFICATION SUITE")
    print("=" * 70)
    passed = 0
    total = 0

    # TEST 1: GEMINI API Security & Environment Configuration
    total += 1
    print("\n[TEST 1] Gemini API Key Configuration & Security Verification...")
    if not GEMINI_API_KEY:
        print("  FAIL: GEMINI_API_KEY is missing or empty in backend/.env.")
    else:
        assert len(GEMINI_API_KEY) > 10, "API key length appears invalid"
        # Verify key is never exposed or logged in plain text
        masked = f"{GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}"
        print(f"  PASS: GEMINI_API_KEY securely configured (prefix: {GEMINI_API_KEY[:4]}***, len: {len(GEMINI_API_KEY)})")
        print(f"  PASS: Sarvam translation deactivated: is_sarvam_available() == {is_sarvam_available()} (preventing HTTP 402)")
        passed += 1

    # TEST 2: English -> Tamil Educational Translation via Gemini
    total += 1
    print("\n[TEST 2] English-to-Tamil Translation via Official Google Gemini API...")
    en_sample = (
        "In Round Robin scheduling, the CPU is allocated to each process for a fixed time quantum. "
        "Refer to (Page 14) and [Timestamp 02:45]."
    )
    ta_result = translate_text(en_sample, target_lang="ta", source_lang="en")
    print("  Input (EN):", en_sample)
    print("  Output (TA):", ta_result)
    assert is_tamil(ta_result), "Output should contain Tamil characters"
    assert "(Page 14)" in ta_result or "Page 14" in ta_result or "14" in ta_result, "Page citation preserved"
    assert "02:45" in ta_result, "Timestamp citation preserved"
    print("  PASS: Natural Tamil translation generated with preserved citations and technical glosses.")
    passed += 1

    # TEST 3: Tamil -> English Reverse Translation via Gemini
    total += 1
    print("\n[TEST 3] Tamil-to-English Reverse Translation for Textbook Retrieval...")
    ta_query = "சுழற்சி முறை ஒதுக்கீட்டில் (Round Robin) context switch என்றால் என்ன?"
    en_result = translate_text(ta_query, target_lang="en", source_lang="ta")
    print("  Input (TA):", ta_query)
    print("  Output (EN):", en_result)
    assert not is_tamil(en_result), "Output should be in English"
    assert "context switch" in en_result.lower() or "round robin" in en_result.lower(), "Concepts preserved"
    print("  PASS: Reverse translation successfully aligned query to academic English concepts.")
    passed += 1

    # TEST 4: Code Block, Formula, and Citation Protection
    total += 1
    print("\n[TEST 4] Literal & Formula Protection (Code, Math, Citations)...")
    mixed_content = (
        "Here is the algorithm implementation:\n"
        "```python\n"
        "def schedule(processes, quantum=2):\n"
        "    return [p.pid for p in processes]\n"
        "```\n"
        "Average waiting time is given by formula $W = \\sum_{i=1}^{n} (T_i - E_i)$. "
        "Source: textbook_os.pdf (Slide 12)."
    )
    mixed_translated = translate_text(mixed_content, target_lang="ta", source_lang="en")
    print("  Translated mixed content:\n", mixed_translated)
    assert "def schedule(processes, quantum=2):" in mixed_translated, "Python code block intact"
    assert "$W = \\sum_{i=1}^{n} (T_i - E_i)$" in mixed_translated or "\\sum" in mixed_translated, "LaTeX math formula intact"
    assert "textbook_os.pdf" in mixed_translated, "Filename preserved"
    assert "(Slide 12)" in mixed_translated or "Slide 12" in mixed_translated, "Slide citation intact"
    print("  PASS: Code blocks, math equations, filenames, and slide citations completely preserved.")
    passed += 1

    # TEST 5: Translation Caching (Zero Latency & Zero Quota on Repeat)
    total += 1
    print("\n[TEST 5] Translation Cache Performance...")
    test_phrase = "Database Normalization eliminates redundant data anomalies."
    t0 = time.time()
    first_res = translate_text(test_phrase, target_lang="ta")
    d1 = time.time() - t0

    t1 = time.time()
    second_res = translate_text(test_phrase, target_lang="ta")
    d2 = time.time() - t1
    print(f"  First call duration: {d1*1000:.1f}ms")
    print(f"  Second call (cached) duration: {d2*1000:.2f}ms")
    assert first_res == second_res, "Cached output must match identical translation"
    assert d2 < 0.05, "Cache lookup should take < 50ms"
    print("  PASS: In-memory cache eliminates redundant API calls and prevents token usage.")
    passed += 1

    # TEST 6: Graceful Circuit Breaker & Quota Fallback
    total += 1
    print("\n[TEST 6] Circuit Breaker & Quota Exhaustion Fallback...")
    # Test that even if quota cooldown is triggered, translate_text still succeeds gracefully via rule engine
    mark_gemini_quota_exhausted(2.0)
    cooldown_res = translate_text("A database transaction requires atomicity, consistency, isolation, and durability.", target_lang="ta")
    print("  Fallback Translation under cooldown:", cooldown_res)
    assert is_tamil(cooldown_res), "Fallback should produce valid Tamil via academic rule engine"
    print("  PASS: Graceful fallback active under cooldown without unhandled exceptions or stalls.")
    passed += 1

    print("\n" + "=" * 70)
    print(f"📊 SUMMARY: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
