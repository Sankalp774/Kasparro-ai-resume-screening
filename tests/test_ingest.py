from pypdf import PdfWriter

from src.extract import extract_text
from src.ingest import ingest_folder


def test_corrupt_pdf_does_not_stop_the_next_file(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.7\nthis is not a readable resume")
    good = tmp_path / "good.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with good.open("wb") as handle:
        writer.write(handle)

    documents = ingest_folder(str(tmp_path))
    by_name = {document.filename: document for document in documents}
    assert by_name["bad.pdf"].status == "failed"
    assert by_name["good.pdf"].status == "parsed"


def test_camel_case_github_username_and_glued_email_stay_readable():
    resume = extract_text(
        "Ada Lovelace\nada@example.com\ngithub.com/AbhinavMishra32\nProjects\nBuilt a LangGraph agent in Python.\n",
        "a.pdf",
    )
    assert resume.name == "Ada Lovelace"
    assert resume.github_username == "AbhinavMishra32"

    glued = extract_text(
        "Sumaiya Sultana Shaiksultanasumaiya623@gmail.com\nProjects\nPython LangGraph agent\n",
        "b.pdf",
    )
    assert glued.name == "Sumaiya Sultana Shaik"
    assert glued.email == "sultanasumaiya623@gmail.com"

    glued_label = extract_text(
        "Vaibhav WakdeEmail: vaibhavwakde266@gmail.com\nProjects\nPython LangGraph\n",
        "c.pdf",
    )
    assert glued_label.name == "Vaibhav Wakde"

    city_line = extract_text(
        "Yash Maini\nNew Delhi, India|+91-8920028757|mainiyash2@gmail.com\nProjects\nPython LangGraph\n",
        "d.pdf",
    )
    assert city_line.name == "Yash Maini"


def test_name_is_recovered_from_a_numbered_header_and_from_beside_the_email():
    numbered = extract_text("1\nANJALI PATIL\nanjali@gmail.com\nProjects\nPython\n", "a.pdf")
    assert numbered.name == "ANJALI PATIL"
    assert numbered.email == "anjali@gmail.com"

    summary_first = extract_text(
        "SUMMARY\nBackend engineer\nMANOJ KUMAR K R\nmanoj@gmail.com\n",
        "b.pdf",
    )
    assert summary_first.name == "MANOJ KUMAR K R"


def test_duplicate_bytes_are_not_parsed_twice(tmp_path):
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    payload = b"%PDF-1.7\nnot a real pdf but identical"
    first.write_bytes(payload)
    second.write_bytes(payload)
    documents = ingest_folder(str(tmp_path))
    statuses = {document.filename: document.status for document in documents}
    assert statuses["a.pdf"] == "failed"
    assert statuses["b.pdf"] == "duplicate"
