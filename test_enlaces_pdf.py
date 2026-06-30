import os
import tempfile
import pytest

from enlaces_pdf import extraer_enlaces

reportlab = pytest.importorskip("reportlab")
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

URL = "https://bolsainterinos.app"


def _pdf_con_enlaces(path):
    """PDF A4 de 2 páginas: enlace en pág 1 (abajo-izq) y pág 2 (arriba-der).
    Pág 3 sin enlaces. Devuelve (W, H)."""
    W, H = A4
    c = canvas.Canvas(path, pagesize=A4)
    # Pág 1: rect (60,195)-(60+200,195+24)
    c.drawString(60, 200, "Ver video")
    c.linkURL(URL, (60, 195, 260, 219), relative=0, thickness=0)
    c.showPage()
    # Pág 2: rect (W-220,H-305)-(W-220+120,H-305+24)
    c.drawString(W - 220, H - 300, "Mas info")
    c.linkURL(URL, (W - 220, H - 305, W - 100, H - 281), relative=0, thickness=0)
    c.showPage()
    # Pág 3: sin enlaces
    c.drawString(60, 200, "Sin enlaces")
    c.showPage()
    c.save()
    return W, H


@pytest.fixture
def pdf(tmp_path):
    p = str(tmp_path / "enlaces.pdf")
    W, H = _pdf_con_enlaces(p)
    return p, float(W), float(H)


def test_extrae_url_y_pagina(pdf):
    path, W, H = pdf
    res = extraer_enlaces(path)
    assert set(res.keys()) == {1, 2}  # pág 3 sin enlaces no aparece
    assert res[1][0]["url"] == URL
    assert res[2][0]["url"] == URL


def test_coordenadas_pagina1(pdf):
    path, W, H = pdf
    e = extraer_enlaces(path)[1][0]
    # rect PDF (60,195)-(260,219) -> CSS con origen arriba-izq
    assert e["left"] == pytest.approx(60 / W, abs=0.005)
    assert e["top"] == pytest.approx(1 - 219 / H, abs=0.005)
    assert e["width"] == pytest.approx(200 / W, abs=0.005)
    assert e["height"] == pytest.approx(24 / H, abs=0.005)


def test_coordenadas_dentro_de_rango(pdf):
    path, W, H = pdf
    for enlaces in extraer_enlaces(path).values():
        for e in enlaces:
            for k in ("left", "top", "width", "height"):
                assert 0.0 <= e[k] <= 1.0


def test_pdf_sin_enlaces_devuelve_vacio(tmp_path):
    p = str(tmp_path / "vacio.pdf")
    c = canvas.Canvas(p, pagesize=A4)
    c.drawString(60, 200, "Hola")
    c.showPage()
    c.save()
    assert extraer_enlaces(p) == {}


def test_pdf_inexistente_no_revienta():
    # Robustez: no debe lanzar; devuelve dict vacío.
    assert extraer_enlaces("/no/existe/x.pdf") == {}
