import os
import pytest
import pdf_tools as pt
from pypdf import PdfReader


def _hacer_pdf(path, paginas=1):
    from PIL import Image
    imgs = [Image.new("RGB", (240, 320), "white") for _ in range(paginas)]
    imgs[0].save(path, "PDF", save_all=True, append_images=imgs[1:])
    return path


def test_unir_pdfs_respeta_paginas(tmp_path):
    a = _hacer_pdf(str(tmp_path / "a.pdf"), 2)
    b = _hacer_pdf(str(tmp_path / "b.pdf"), 3)
    out = pt.unir_pdfs([a, b], str(tmp_path / "out.pdf"))
    assert os.path.exists(out)
    assert len(PdfReader(out).pages) == 5


def test_convertir_a_pdf_passthrough(tmp_path):
    a = _hacer_pdf(str(tmp_path / "ya.pdf"), 1)
    out = pt.convertir_a_pdf(a, str(tmp_path / "salida"))
    assert out.lower().endswith(".pdf") and os.path.exists(out)
    assert len(PdfReader(out).pages) == 1


def test_detectar_convertidor_hay_alguno():
    # En el PC de desarrollo (Zorin) hay LibreOffice.
    assert pt.detectar_convertidor() in ("word", "libreoffice")


def test_convertir_docx_si_hay_convertidor(tmp_path):
    if pt.detectar_convertidor() is None:
        pytest.skip("sin convertidor")
    from docx import Document
    doc = Document()
    doc.add_paragraph("Hola periódico de prueba")
    src = str(tmp_path / "noticia.docx")
    doc.save(src)
    out = pt.convertir_a_pdf(src, str(tmp_path / "conv"))
    assert out.lower().endswith(".pdf") and os.path.exists(out)
    assert len(PdfReader(out).pages) >= 1


def test_preparar_periodico_combina(tmp_path):
    a = _hacer_pdf(str(tmp_path / "uno.pdf"), 2)
    b = _hacer_pdf(str(tmp_path / "dos.pdf"), 1)
    out = pt.preparar_periodico([a, b], str(tmp_path / "fin"), "periodico")
    assert out.endswith("periodico.pdf") and os.path.exists(out)
    assert len(PdfReader(out).pages) == 3
