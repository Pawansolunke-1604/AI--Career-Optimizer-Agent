"""File-handling checks: sends tricky files to the upload endpoint and reports what the API does.

Uses no Gemini calls (only the /analysis/parse endpoint), so it is free and takes seconds.
Run from the backend folder:   python -m evaluation.run_file_checks
Result is printed and saved to evaluation/file_report.md.

Status meanings: PASS = behaved as expected. FAIL = wrong behaviour, fix it.
WARN = a known risk: the file is realistic, but the app may reject or garble it (decide if it matters).
"""
import base64
import io
import re
from pathlib import Path

import pymupdf
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.services import guardrails
from app.core.exceptions import InputRejectedError

PDF, DOCX = "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
REPORT_PATH = Path(__file__).parent / "file_report.md"
PARSE_URL = "/api/v1/analysis/parse"

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


# ---------- builders for the test files (all made up, nothing personal) ----------

def _save(doc: pymupdf.Document, **kwargs) -> bytes:
    data = doc.tobytes(**kwargs)
    doc.close()
    return data


def plain_pdf(lines: list[str]) -> bytes:
    doc, page, y = pymupdf.open(), None, 0
    for line in lines:
        if page is None or y > 790:
            page, y = doc.new_page(), 56
        page.insert_text((50, y), line, fontsize=10, fontname="helv")
        y += 15
    return _save(doc)


def two_column_pdf() -> bytes:
    """Left and right columns written line by line, so extracted text comes out interleaved."""
    left = ["Neha Patil", "Pune | neha.p@example.com", "", "SKILLS", "Java, Spring Boot, MySQL", "REST APIs, Git",
            "Docker, Maven, JUnit", "", "EDUCATION", "B.E. Computer Science, 2024", "Example College of Eng."]
    right = ["EXPERIENCE", "Software Developer Intern", "Example Tech Pvt Ltd (Jan 2024 - Jun 2024)",
             "- Built REST APIs using Spring Boot", "- Wrote JUnit tests for service classes",
             "- Containerised services with Docker", "", "PROJECTS", "Library Management System",
             "- Java, Spring Boot, MySQL, REST APIs"]
    doc = pymupdf.open()
    page = doc.new_page()
    for i in range(max(len(left), len(right))):
        y = 60 + i * 18
        if i < len(left):
            page.insert_text((40, y), left[i], fontsize=9, fontname="helv")
        if i < len(right):
            page.insert_text((290, y), right[i], fontsize=9, fontname="helv")
    return _save(doc)


def design_pdf(headings: dict[str, str]) -> bytes:
    """Canva-style: big headings, coloured bars, skills as separate 'tags'."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(0, 0, 595, 110), color=None, fill=(0.1, 0.2, 0.4))
    page.insert_text((40, 60), "Hi, I'm Karan Desai", fontsize=26, fontname="hebo", color=(1, 1, 1))
    page.insert_text((40, 88), "Backend developer | karan.d@example.com | Nashik", fontsize=11, fontname="helv", color=(1, 1, 1))
    y = 150
    page.insert_text((40, y), headings["about"], fontsize=15, fontname="hebo")
    page.insert_textbox(pymupdf.Rect(40, y + 8, 555, y + 70),
                        "Junior backend developer with two years of hands-on work building APIs "
                        "in Python and FastAPI, backed by PostgreSQL.", fontsize=10.5, fontname="helv")
    y += 100
    page.insert_text((40, y), headings["tools"], fontsize=15, fontname="hebo")
    x = 40
    for tag in ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "Redis", "Linux"]:
        page.draw_rect(pymupdf.Rect(x, y + 14, x + 72, y + 36), color=(0.1, 0.2, 0.4), width=1)
        page.insert_text((x + 8, y + 29), tag, fontsize=10, fontname="helv")
        x += 82
    y += 80
    page.insert_text((40, y), headings["work"], fontsize=15, fontname="hebo")
    for i, line in enumerate(["Backend Developer, Orbit Systems (2023 - 2025)",
                              "• Built FastAPI services used by 3 internal teams",
                              "• Cut report generation time by moving jobs to Redis queues"]):
        page.insert_text((40, y + 22 + i * 16), line, fontsize=10.5, fontname="helv")
    y += 100
    page.insert_text((40, y), headings["school"], fontsize=15, fontname="hebo")
    page.insert_text((40, y + 22), "B.Sc. Computer Science, Example University, 2023", fontsize=10.5, fontname="helv")
    return _save(doc)


def long_resume_pdf() -> bytes:
    lines = ["Aditi Rao", "aditi.rao@example.com | Pune", "", "SUMMARY",
             "Full stack developer with experience in Java, Spring Boot, React and MySQL.", "", "SKILLS",
             "Java, Spring Boot, React, JavaScript, MySQL, Git, Docker, REST APIs, Maven", "", "EXPERIENCE"]
    for n in range(1, 13):
        lines += [f"Software Engineer {n}, Company {n} (20{9 + n}-01 to 20{9 + n}-12)"]
        lines += [f"- Delivered feature set {n} using Java and Spring Boot with MySQL storage."] * 5
        lines += [""]
    lines += ["PROJECTS"]
    for n in range(1, 15):
        lines += [f"Project {n}: Internal tool {n} (Java, React, MySQL)"]
        lines += [f"- Built dashboards and REST APIs for team {n}; used Git and Maven for builds."] * 2
    lines += ["", "EDUCATION", "B.E. Computer Science, Example Institute, 2014"]
    return plain_pdf(lines)


def scanned_pdf() -> bytes:
    """A resume that is only a picture: no text layer, like a phone scan."""
    src = pymupdf.open()
    page = src.new_page()
    page.insert_textbox(pymupdf.Rect(50, 60, 545, 700),
                        "Vikram Joshi\nSKILLS: Java, Spring Boot, MySQL\nEXPERIENCE: Intern at Example Tech\nEDUCATION: B.E. 2025",
                        fontsize=14, fontname="helv")
    png = page.get_pixmap(dpi=72).tobytes("png")
    src.close()
    doc = pymupdf.open()
    new_page = doc.new_page()
    new_page.insert_image(new_page.rect, stream=png)
    return _save(doc)


def locked_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 80), "SKILLS: Java\nEXPERIENCE: none", fontsize=12)
    return _save(doc, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")


def docx_resume(two_column_table: bool = False) -> bytes:
    d = Document()
    d.add_heading("Pooja Nair", 1)
    d.add_paragraph("pooja.n@example.com | Mumbai")
    if two_column_table:
        t = d.add_table(rows=1, cols=2)
        t.rows[0].cells[0].text = "SKILLS\nPython, Pandas, NumPy, scikit-learn, SQL"
        t.rows[0].cells[1].text = ("EXPERIENCE\nData Analyst Intern, Example Analytics (2024-01 to 2024-06)\n"
                                   "- Cleaned sales data using Pandas\n- Trained a churn model with scikit-learn\n"
                                   "- Wrote SQL queries for weekly reports")
       
    else:
        d.add_heading("Skills", 2)
        d.add_paragraph("Python, Pandas, NumPy, scikit-learn, SQL, Git")
        d.add_heading("Experience", 2)
        d.add_paragraph("Data Analyst Intern, Example Analytics (2024-01 to 2024-06)")
        d.add_paragraph("Cleaned sales data using Pandas and trained a churn model with scikit-learn.")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ---------- the cases ----------
# (name, filename, mime, bytes, expected statuses, words that must appear in the text, soft?)
GOOD_WORDS = ["Java", "Spring Boot", "MySQL"]
VALID = plain_pdf(["Rahul Sharma", "SUMMARY", "Java developer with Spring Boot and MySQL experience.", "",
                   "SKILLS", "Java, Spring Boot, REST APIs, MySQL, Git", "", "EXPERIENCE",
                   "Software Developer Intern, Example Tech (Jun 2024 - Dec 2024)",
                   "- Built REST APIs with Spring Boot and MySQL.", "", "EDUCATION", "B.E. Computer Science, 2025"])

CASES = [
    # --- realistic files that should work ---
    ("clean one-page PDF", "resume.pdf", PDF, VALID, {200}, GOOD_WORDS, False),
    ("uppercase extension", "RESUME.PDF", PDF, VALID, {200}, GOOD_WORDS, False),
    ("spaces and accents in file name", "résumé final (2).pdf", PDF, VALID, {200}, GOOD_WORDS, False),
    ("two-column layout (interleaved)", "two_column.pdf", PDF, two_column_pdf(), {200},
     ["Spring Boot", "Docker", "Software Developer Intern"], False),
    ("Canva-style design, normal headings", "canva_normal.pdf", PDF,
     design_pdf({"about": "Profile", "tools": "Skills", "work": "Experience", "school": "Education"}), {200},
     ["FastAPI", "PostgreSQL", "Redis"], False),
    ("Canva-style design, unusual headings", "canva_unusual.pdf", PDF,
     design_pdf({"about": "Hello there", "tools": "My toolbox", "work": "Where I've worked", "school": "Where I studied"}),
     {200}, ["FastAPI", "PostgreSQL", "Redis"], True),
    ("long 3-page resume", "long_resume.pdf", PDF, long_resume_pdf(), {200}, ["Spring Boot", "Project 14"], False),
    ("Word resume (.docx)", "resume.docx", DOCX, docx_resume(), {200}, ["Python", "Pandas"], False),
    ("Word resume with a two-column table", "resume_table.docx", DOCX, docx_resume(False), {200},
     ["Python", "Pandas", "Data Analyst Intern"], True),
    # --- files that must be rejected cleanly ---
    ("empty file", "empty.pdf", PDF, b"", {400, 415, 422}, [], False),
    ("random bytes named .pdf", "fake.pdf", PDF, bytes(range(256)) * 40, {415, 422}, [], False),
    ("truncated PDF (must not crash)", "cut.pdf", PDF, VALID[: len(VALID) // 2], {200, 422}, [], False),
    ("password-protected PDF", "locked.pdf", PDF, locked_pdf(), {422}, [], False),
    ("scanned PDF (image only)", "scan.pdf", PDF, scanned_pdf(), {422}, [], False),
    ("text file renamed .pdf", "notes.pdf", PDF, b"Just some notes, not a PDF at all." * 20, {415, 422}, [], False),
    ("PNG image renamed .docx", "photo.docx", DOCX, PNG_1X1, {415, 422}, [], False),
    ("corrupt .docx", "broken.docx", DOCX, b"PK\x03\x04" + b"garbage" * 100, {422}, [], False),
    ("plain text file (.txt) is supported", "resume.txt", "text/plain", b"Java developer " * 30, {200}, [], False),
    ("unsupported type (.exe)", "setup.exe", "application/octet-stream", b"MZ" + b"\x00" * 200, {415}, [], False),
    ("file over the size limit (6 MB)", "huge.pdf", PDF, VALID + b"\x00" * (6 * 1024 * 1024), {413}, [], False),
]


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def run() -> None:
    client = TestClient(app)
    rows, counts = [], {"PASS": 0, "FAIL": 0, "WARN": 0}
    for name, filename, mime, data, expected, words, soft in CASES:
        response = client.post(PARSE_URL, files={"file": (filename, data, mime)})
        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = {}
        text = body.get("preview", "") if status == 200 else ""
        message = body.get("error") or (f"{len(text)} characters read" if status == 200 else "")

        problems = []
        if status not in expected:
            problems.append(f"expected {sorted(expected)}")
        elif status == 200 and words:  # realistic files: check the text and the guardrails
            missing = [w for w in words if squash(w) not in squash(text)]
            if missing:
                problems.append("text missing: " + ", ".join(missing))
            try:
                guardrails.validate_resume_text(text)
            except InputRejectedError as exc:
                problems.append("would be rejected by guardrails: " + exc.message)

        verdict = "PASS" if not problems else ("WARN" if soft else "FAIL")
        counts[verdict] += 1
        rows.append([name, status, verdict, (message + (" | " + "; ".join(problems) if problems else ""))[:150]])

    lines = ["# File-handling report", "",
             f"{len(CASES)} files: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail", "",
             "| File | Status | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {n} | {s} | {v} | {d.replace('|', '/')} |" for n, s, v, d in rows]
    text = "\n".join(lines)
    REPORT_PATH.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nSaved to {REPORT_PATH}")


if __name__ == "__main__":
    run()