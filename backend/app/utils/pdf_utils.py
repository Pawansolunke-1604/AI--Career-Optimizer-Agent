import pymupdf


def extract_text_from_pdf(data: bytes) -> str:
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        if doc.needs_pass:
            raise ValueError("PDF is password protected")
        return "\n".join(page.get_text() for page in doc)