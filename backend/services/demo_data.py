import json
from pathlib import Path
from typing import Dict, Any, List

SAMPLE_TEXTBOOK_ID = "tb_dbms_norm_001"
SAMPLE_TEXTBOOK_TITLE = "Database System Concepts & Relational Normalization"
SAMPLE_FILENAME = "Database_System_Concepts_Chapter3_Normalization.pdf"

SAMPLE_CHAPTERS = [
    {
        "id": "ch_1",
        "number": 1,
        "title": "Introduction to Relational Databases & Functional Dependencies",
        "page_start": 1,
        "page_end": 15,
        "sections": [
            {
                "id": "sec_1_1",
                "title": "Relational Model & Anomalies (Insertion, Update, Deletion)",
                "page_start": 1,
                "page_end": 7,
                "content": """A relational database stores data in relations (tables). When tables are designed poorly without proper decomposition, databases suffer from three severe anomalies:
1. Insertion Anomaly: Inability to insert a new entity record without artificially introducing attributes of another unrelated entity.
2. Update / Modification Anomaly: Inconsistent updates where modifying a repeated value in one row leaves contradictory values across other rows.
3. Deletion Anomaly: Deleting one piece of data inadvertently destroys other essential data because both are stored together in the same unnormalized relation.

Functional Dependency (FD) is a relationship between attributes in a relation. An attribute Y is functionally dependent on X (written as X -> Y) if each value of X determines exactly one value of Y. Functional dependencies form the foundational mathematics of database normalization."""
            },
            {
                "id": "sec_1_2",
                "title": "Candidate Keys, Primary Keys, and Superkeys",
                "page_start": 8,
                "page_end": 15,
                "content": """A Superkey is a set of one or more attributes that uniquely identifies a tuple within a relation. A Candidate Key is a minimal superkey—a superkey from which no attribute can be removed without losing the uniqueness property. The Primary Key is the candidate key explicitly chosen by the database designer. Prime attributes are attributes that are part of any candidate key, whereas Non-prime attributes are attributes that do not belong to any candidate key."""
            }
        ]
    },
    {
        "id": "ch_2",
        "number": 2,
        "title": "First Normal Form (1NF) & Atomic Values",
        "page_start": 16,
        "page_end": 30,
        "sections": [
            {
                "id": "sec_2_1",
                "title": "Definition of 1NF & Eliminating Repeating Groups",
                "page_start": 16,
                "page_end": 30,
                "content": """A relation is in First Normal Form (1NF) if and only if the domain of each attribute contains only atomic (indivisible) values, and the value of each attribute in every tuple is a single value from that domain.
To achieve 1NF:
1. Eliminate repeating groups and multivalued attributes (e.g., multiple phone numbers stored in a single comma-separated string column).
2. Create a separate table for each set of related data or flatten the multi-valued entries by creating separate tuples for each value.
3. Ensure every column contains atomic data types and each record is identifiable by a unique primary key."""
            }
        ]
    },
    {
        "id": "ch_3",
        "number": 3,
        "title": "Second Normal Form (2NF) & Partial Dependencies",
        "page_start": 31,
        "page_end": 50,
        "sections": [
            {
                "id": "sec_3_1",
                "title": "Understanding Partial Functional Dependency",
                "page_start": 31,
                "page_end": 41,
                "content": """A relation R is in Second Normal Form (2NF) if:
1. It is already in First Normal Form (1NF).
2. No non-prime attribute is partially dependent on any candidate key of the relation.

A Partial Dependency occurs when a non-prime attribute is functionally dependent on only a proper subset of a composite candidate key rather than the entire composite key.
For instance, in a table Student_Course(StudentID, CourseID, CourseFee, StudentGrade), the primary key is the composite key (StudentID, CourseID). However, CourseFee depends solely on CourseID (a proper subset of the primary key). This is a partial dependency and causes data redundancy."""
            },
            {
                "id": "sec_3_2",
                "title": "Decomposition into 2NF Relations",
                "page_start": 42,
                "page_end": 50,
                "content": """To convert a 1NF relation into 2NF, identify all partial dependencies. Remove the partially dependent attributes from the original table and place them into a new relation along with a copy of their determinant attribute (the subset of the primary key).
Example decomposition:
- Original: Enrolment(StudentID, CourseID, CourseName, Instructor, Grade) where (StudentID, CourseID) -> Grade and CourseID -> (CourseName, Instructor).
- 2NF Relations:
  1. Enrolment_Grade(StudentID, CourseID, Grade)
  2. Course_Details(CourseID, CourseName, Instructor)
This eliminates update and deletion anomalies associated with course information."""
            }
        ]
    },
    {
        "id": "ch_4",
        "number": 4,
        "title": "Third Normal Form (3NF) & Boyce-Codd Normal Form (BCNF)",
        "page_start": 51,
        "page_end": 75,
        "sections": [
            {
                "id": "sec_4_1",
                "title": "Transitive Dependencies & 3NF Rules",
                "page_start": 51,
                "page_end": 62,
                "content": """A relation R is in Third Normal Form (3NF) if:
1. It is in Second Normal Form (2NF).
2. No non-prime attribute is transitively dependent on the primary key.

A Transitive Dependency occurs when X -> Y and Y -> Z (where Y does not functionally determine X), leading to the indirect functional dependency X -> Z. In simpler terms, a non-prime attribute determines another non-prime attribute.
Example: Employee(EmpID, DeptID, DeptName). Here EmpID -> DeptID and DeptID -> DeptName. Therefore EmpID -> DeptName is transitive.
Decomposition: Split into Employee(EmpID, DeptID) and Department(DeptID, DeptName)."""
            },
            {
                "id": "sec_4_2",
                "title": "Boyce-Codd Normal Form (BCNF)",
                "page_start": 63,
                "page_end": 75,
                "content": """Boyce-Codd Normal Form (BCNF) is a stricter version of 3NF, often called 3.5NF.
A relation R is in BCNF if for every non-trivial functional dependency X -> Y, X is a Superkey.
While 3NF permits non-prime attributes to be determined by a candidate key or Y being a prime attribute, BCNF requires that the determinant X MUST always be a superkey without exception."""
            }
        ]
    },
    {
        "id": "ch_5",
        "number": 5,
        "title": "Transactions and ACID Properties",
        "page_start": 76,
        "page_end": 95,
        "sections": [
            {
                "id": "sec_5_1",
                "title": "ACID Properties (Atomicity, Consistency, Isolation, Durability)",
                "page_start": 76,
                "page_end": 95,
                "content": """A Transaction is a logical unit of database processing that includes one or more database access operations (read, write, update). To preserve database integrity, every transaction must obey the ACID properties:
- Atomicity ('All or Nothing'): Either all operations of the transaction are executed and committed successfully, or none are executed (rolled back in event of failure).
- Consistency: A transaction must transform the database from one consistent state to another consistent state, respecting all constraints and business rules.
- Isolation: Concurrent execution of transactions yields the same system state as if transactions were executed serially one after another without mutual interference.
- Durability: Once a transaction is committed, its modifications persist permanently in storage even in the event of power outage or system crash."""
            }
        ]
    }
]

def get_demo_textbook_data() -> Dict[str, Any]:
    chunks = []
    chunk_counter = 1
    for ch in SAMPLE_CHAPTERS:
        for sec in ch["sections"]:
            paragraphs = sec["content"].strip().split("\n\n")
            for idx, p in enumerate(paragraphs):
                chunks.append({
                    "id": f"chk_{chunk_counter}",
                    "textbook_id": SAMPLE_TEXTBOOK_ID,
                    "chapter_id": ch["id"],
                    "chapter_title": ch["title"],
                    "section_id": sec["id"],
                    "section_title": sec["title"],
                    "page": sec["page_start"] + idx,
                    "content": p.strip()
                })
                chunk_counter += 1
                
    metadata = {
        "id": SAMPLE_TEXTBOOK_ID,
        "title": SAMPLE_TEXTBOOK_TITLE,
        "filename": SAMPLE_FILENAME,
        "total_pages": 95,
        "file_size_bytes": 1024 * 1024 * 3 + 450 * 1024,  # ~3.45 MB
        "chapters": SAMPLE_CHAPTERS,
        "created_at": "2026-09-15T12:00:00"
    }
    
    return {
        "metadata": metadata,
        "chunks": chunks
    }

def generate_sample_pdf_if_needed(target_path: Path):
    """Generate a physical sample PDF file using reportlab if target_path does not exist."""
    if target_path.exists():
        return
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(target_path), pagesize=letter)
        width, height = letter
        
        # Cover page
        c.setFont("Helvetica-Bold", 22)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.drawString(50, height - 100, "Database System Concepts")
        c.setFont("Helvetica", 14)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawString(50, height - 130, "Specialized Module: Relational Normalization & Transactions")
        c.drawString(50, height - 155, "College Course Textbook Edition")
        
        c.setStrokeColor(colors.HexColor("#3b82f6"))
        c.setLineWidth(2)
        c.line(50, height - 170, width - 50, height - 170)
        
        y = height - 210
        for ch in SAMPLE_CHAPTERS:
            c.setFont("Helvetica-Bold", 14)
            c.setFillColor(colors.HexColor("#1e3a8a"))
            c.drawString(50, y, f"Chapter {ch['number']}: {ch['title']}")
            y -= 20
            
            for sec in ch["sections"]:
                c.setFont("Helvetica-Bold", 11)
                c.setFillColor(colors.HexColor("#0f172a"))
                c.drawString(65, y, f"Section: {sec['title']} (Pages {sec['page_start']}-{sec['page_end']})")
                y -= 16
                
                c.setFont("Helvetica", 9)
                c.setFillColor(colors.HexColor("#334155"))
                lines = sec["content"].split("\n")
                for line in lines:
                    if len(line.strip()) > 0:
                        # wrap text briefly
                        wrapped = [line[i:i+85] for i in range(0, len(line), 85)]
                        for w in wrapped:
                            c.drawString(80, y, w)
                            y -= 12
                            if y < 60:
                                c.showPage()
                                y = height - 60
                y -= 10
            y -= 15
            if y < 100:
                c.showPage()
                y = height - 60
                
        c.showPage()
        c.save()
    except Exception as e:
        print(f"Sample PDF generation note: {e}")
