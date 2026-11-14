import io
from docx import Document
from apps.handovers.input_handler.document_reader import DocumentReader


def test_document_reader_extracts_paragraphs_and_tables():
    doc = Document()
    doc.add_paragraph("Employee Handover Document")
    
    table = doc.add_table(rows=2, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Task Name"
    hdr_cells[1].text = "Owner"
    hdr_cells[2].text = "Deadline"

    row_cells = table.rows[1].cells
    row_cells[0].text = "Database Migration"
    row_cells[1].text = "Alice Tan"
    row_cells[2].text = "15/12/2026"

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    buffer.name = "handover.docx"
    buffer.size = buffer.getbuffer().nbytes

    reader = DocumentReader()
    content = reader.read_document(buffer)

    assert "Employee Handover Document" in content
    assert "Database Migration" in content
    assert "Alice Tan" in content
    assert "15/12/2026" in content


def test_non_word_uploads_are_rejected_by_form_and_reader():
    import pytest
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.handovers.forms import HandoverUploadForm
    for filename in ["handover.txt", "handover.TXT", "handover.doc", "handover.pdf"]:
        upload = SimpleUploadedFile(filename, b"Sample handover", content_type="text/plain")
        form = HandoverUploadForm(files={"document": upload})
        assert not form.is_valid()
        assert ".docx" in str(form.errors["document"])
        with pytest.raises(ValueError, match="Only Word"):
            DocumentReader().read_document(upload)


def test_word_upload_remains_supported_and_invalid_docx_content_is_rejected():
    import pytest
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.handovers.forms import HandoverUploadForm
    buffer = io.BytesIO()
    document = Document()
    document.add_paragraph("Review the weekly report")
    document.save(buffer)
    upload = SimpleUploadedFile("handover.DOCX", buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert HandoverUploadForm(files={"document": upload}).is_valid()
    assert "Review the weekly report" in DocumentReader().read_document(upload)
    disguised = SimpleUploadedFile("handover.docx", b"This is plain text")
    with pytest.raises(ValueError, match="Unable to read DOCX"):
        DocumentReader().read_document(disguised)
