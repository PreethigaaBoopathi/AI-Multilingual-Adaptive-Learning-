import sqlite3
import json

conn = sqlite3.connect('data/learning_system.db')
c = conn.cursor()
c.execute("PRAGMA table_info(textbooks)")
cols = [c[1] for c in c.fetchall()]
print("Textbooks columns:", cols)
c.execute("SELECT chapters_json FROM textbooks WHERE id = 'pdf_370779'")
ch_json = c.fetchone()[0]
print(json.dumps(json.loads(ch_json), indent=2))

c.execute("SELECT id, chapter_title, section_title, page, length(content) FROM chunks WHERE textbook_id = 'pdf_370779'")
chunks = c.fetchall()
print(f"\nTotal chunks: {len(chunks)}")
for ch in chunks:
    print(ch)
