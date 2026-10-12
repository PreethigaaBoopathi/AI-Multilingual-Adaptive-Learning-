import sqlite3

conn = sqlite3.connect('data/learning_system.db')
c = conn.cursor()
c.execute("SELECT id, title, filename FROM textbooks WHERE title LIKE '%22IT%' OR filename LIKE '%22IT%' OR title LIKE '%DATA STRUCTURES%'")
rows = c.fetchall()
print(f"Matches in textbooks: {len(rows)}")
for r in rows:
    print(r)

c.execute("SELECT id, textbook_id, chapter_title, section_title, page, content FROM chunks WHERE content LIKE '%Trie data structure%' LIMIT 3")
chunks = c.fetchall()
print(f"\nMatching chunks: {len(chunks)}")
for ch in chunks:
    print(ch[0], ch[1], ch[2], ch[3], ch[4], ch[5][:100])
