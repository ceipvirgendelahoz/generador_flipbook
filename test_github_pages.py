import os
import time
import tempfile
import pytest
import github_pages as gp

def _token():
    p = os.path.join(os.path.dirname(__file__), "tokengenerarflipbook.txt")
    if not os.path.exists(p):
        pytest.skip("sin token para test real de red")
    return open(p).read().strip()

def _flipbook_tmp(n_paginas):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "index.html"), "w").write("<h1>test</h1>")
    os.makedirs(os.path.join(d, "pages"))
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108"
                        "060000001f15c4890000000a49444154789c63000100000500"
                        "010d0a2db40000000049454e44ae426082")
    for i in range(1, n_paginas + 1):
        open(os.path.join(d, "pages", f"page_{i:03d}.png"), "wb").write(png)
    return d

def _esperar(cond, timeout=25, intervalo=1.5):
    """Reintenta cond() hasta que sea verdadera o se agote el tiempo.
    La API de GitHub tiene latencia de lectura-tras-escritura: tras mover la
    ref, una lectura inmediata puede ver aún el estado anterior. Las funciones
    reciben el token por cierre, NO como argumento de un assert, para que el
    token nunca aparezca en la salida de pytest si una aserción falla."""
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            if cond():
                return True
        except Exception:
            pass
        time.sleep(intervalo)
    return False

def test_ciclo_real_publicar_listar_borrar():
    tok = _token()
    nombre = f"zz-test-{int(time.time())}"
    s = gp.slug(nombre)

    def _solo_una_pagina():
        _, blobs = gp._arbol_actual(tok)
        pgs = [b["path"] for b in blobs if b["path"].startswith(f"{s}/pages/")]
        return pgs == [f"{s}/pages/page_001.png"]

    try:
        url = gp.publicar(tok, nombre, _flipbook_tmp(3))
        assert url == f"{gp.PAGES_URL}/{s}/"
        assert _esperar(lambda: gp.existe(tok, nombre) is True), "no apareció tras publicar"
        assert _esperar(lambda: any(it["nombre"] == s for it in gp.listar(tok))), "no aparece en listar"
        # republish con menos páginas -> sin huérfanos
        gp.publicar(tok, nombre, _flipbook_tmp(1))
        assert _esperar(_solo_una_pagina), "quedaron páginas huérfanas tras republish"
    finally:
        gp.borrar(tok, nombre)
    assert _esperar(lambda: gp.existe(tok, nombre) is False), "sigue existiendo tras borrar"
    assert _esperar(lambda: all(it["nombre"] != s for it in gp.listar(tok))), "sigue en listar tras borrar"

def test_slug_basico():
    assert gp.slug("Periódico Marzo 2025") == "periodico-marzo-2025"

def test_slug_acentos_y_enie():
    assert gp.slug("Edición Niños") == "edicion-ninos"

def test_slug_simbolos_y_guiones_dobles():
    assert gp.slug("Hola!!  ¿Qué tal??") == "hola-que-tal"

def test_slug_recorta_extremos():
    assert gp.slug("  ___hola___  ") == "hola"

def test_slug_vacio_por_defecto():
    assert gp.slug("   ") == "periodico"
    assert gp.slug("") == "periodico"

def test_slug_conserva_guion_bajo_interno():
    assert gp.slug("periodico_20_06_2026") == "periodico_20_06_2026"

def test_repo_desde_archivo_lee_owner_repo(tmp_path):
    import github_pages as gp
    (tmp_path / "repositorio.txt").write_text("miorg/mirepo")
    assert gp._repo_desde_archivo([str(tmp_path)]) == ("miorg", "mirepo")

def test_repo_desde_archivo_sin_archivo(tmp_path):
    import github_pages as gp
    assert gp._repo_desde_archivo([str(tmp_path)]) is None

def test_repo_por_defecto():
    import github_pages as gp
    # Sin repositorio.txt junto al módulo -> valores por defecto
    assert gp.OWNER == "dtabuyodesigner" and gp.REPO == "generador_flipbook"
    assert gp.PAGES_URL == "https://dtabuyodesigner.github.io/generador_flipbook"
