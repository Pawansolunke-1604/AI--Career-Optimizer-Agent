"""Turns an OptimizedResume into a clean, ATS-friendly .docx (single column, plain headings, real bullets)."""
import re
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt

from app.schemas.agent import OptimizedResume

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
USABLE_WIDTH = Inches(6.87)  # A4 width minus 0.7" margins


def safe_filename(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "resume"
    return f"{base}_optimized_resume.docx"


def _heading(doc, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(11)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "808080")):
        bottom.set(qn(key), value)
    border.append(bottom)
    p._p.get_or_add_pPr().append(border)


def _line(doc, left_bold: str, left_rest: str = "", right: str = "") -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.tab_stops.add_tab_stop(USABLE_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    p.add_run(left_bold).bold = True
    if left_rest:
        p.add_run(left_rest)
    if right:
        p.add_run("\t" + right)


def _bullets(doc, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(item, style="List Bullet")
        p.paragraph_format.space_after = Pt(0)


def build_docx(r: OptimizedResume) -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)  # A4
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(0.7))
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(r.name)
    run.bold = True
    run.font.size = Pt(18)
    if r.contact_line:
        contact = doc.add_paragraph(r.contact_line)
        contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact.paragraph_format.space_after = Pt(0)

    if r.summary:
        _heading(doc, "Summary")
        doc.add_paragraph(r.summary)
    if r.skill_groups:
        _heading(doc, "Skills")
        for g in r.skill_groups:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.add_run(f"{g.name}: ").bold = True
            p.add_run(", ".join(g.skills))
    if r.experience:
        _heading(doc, "Experience")
        for job in r.experience:
            _line(doc, job.role, f", {job.company}", job.dates)
            _bullets(doc, job.bullets)
    if r.projects:
        _heading(doc, "Projects")
        for pr in r.projects:
            _line(doc, pr.name, f"  ({', '.join(pr.technologies)})" if pr.technologies else "")
            _bullets(doc, pr.bullets)
    if r.education:
        _heading(doc, "Education")
        for e in r.education:
            _line(doc, e.institution, f", {e.degree}" if e.degree else "", e.dates)
            if e.detail:
                doc.add_paragraph(e.detail).paragraph_format.space_after = Pt(0)
    if r.extras:
        _heading(doc, "Certificates & Achievements")
        _bullets(doc, r.extras)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()