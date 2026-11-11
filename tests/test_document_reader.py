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
