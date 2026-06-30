"""Extrae los hipervínculos reales de un PDF con su posición en cada página.

Las páginas del flipbook son imágenes, así que para que un enlace del PDF sea
pinchable hay que superponer una zona `<a>` encima de la imagen, en el sitio
exacto. Este módulo devuelve esas posiciones en fracciones 0–1 con origen
arriba-izquierda (listas para CSS: left/top/width/height en %).
"""
from pypdf import PdfReader


def extraer_enlaces(pdf_path):
    """Devuelve {pagina(1-based): [ {url, left, top, width, height}, ... ]}.

    Solo enlaces externos reales (anotación /Link con acción /URI). Las páginas
    sin enlaces no aparecen en el dict. Nunca lanza: ante un PDF ilegible o una
    anotación rara, devuelve lo que haya podido leer (o {}).
    """
    resultado = {}
    try:
        lector = PdfReader(pdf_path)
    except Exception:
        return resultado

    for i, pagina in enumerate(lector.pages, 1):
        try:
            enlaces = _enlaces_de_pagina(pagina)
        except Exception:
            enlaces = []
        if enlaces:
            resultado[i] = enlaces
    return resultado


def _enlaces_de_pagina(pagina):
    annots = pagina.get("/Annots")
    if not annots:
        return []
    caja = pagina.mediabox
    pw, ph = float(caja.width), float(caja.height)
    x0, y0 = float(caja.left), float(caja.bottom)
    if pw <= 0 or ph <= 0:
        return []

    enlaces = []
    for ref in annots:
        try:
            obj = ref.get_object()
            if obj.get("/Subtype") != "/Link":
                continue
            accion = obj.get("/A") or {}
            uri = accion.get("/URI")
            rect = obj.get("/Rect")
            if not uri or not rect:
                continue
            x1, y1, x2, y2 = (float(v) for v in rect)
            # Normalizar respecto al origen de la mediabox y a su tamaño.
            left = (min(x1, x2) - x0) / pw
            right = (max(x1, x2) - x0) / pw
            top = 1 - (max(y1, y2) - y0) / ph
            bottom = 1 - (min(y1, y2) - y0) / ph
            enlaces.append({
                "url": str(uri),
                "left": _clamp(left),
                "top": _clamp(top),
                "width": _clamp(right - left),
                "height": _clamp(bottom - top),
            })
        except Exception:
            continue
    return enlaces


def _clamp(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v
