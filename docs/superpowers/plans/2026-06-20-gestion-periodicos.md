# Gestión de periódicos publicados — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir a Pilar listar, actualizar y borrar periódicos publicados en GitHub Pages desde la app, con nombres URL-seguros, subida en segundo plano y sin ver nada técnico (token).

**Architecture:** Se extrae toda la red a un módulo puro `github_pages.py` (sin tkinter, testeable). `crear_flipbook.py` importa ese módulo y añade: saneo de nombre (slug), aviso de sobrescritura, subida en hilo y un panel `Toplevel` de gestión. Republish y borrado reconstruyen el árbol completo (sin `base_tree`) para no dejar imágenes huérfanas.

**Tech Stack:** Python 3.12, `urllib` (sin deps externas para la red), `tkinter`, `threading`, `pytest` 7.4.

## Global Constraints

- Sin nuevas dependencias externas: la red usa solo `urllib` (stdlib).
- Constantes del repo: `OWNER="dtabuyodesigner"`, `REPO="generador_flipbook"`, `BRANCH="gh-pages"`.
- URL pública: `https://dtabuyodesigner.github.io/generador_flipbook/<slug>/`.
- El token NUNCA aparece en la UI ni en mensajes a Pilar. Se lee en silencio (archivo `tokengenerarflipbook.txt` o config). Mensajes de error sin la palabra "token": usar *"No se ha podido publicar en internet. Revisa tu conexión a internet. Si el problema sigue, avisa a Dani."*
- El flipbook local debe crearse siempre, aunque falle la red.
- El token para tests reales se lee de `tokengenerarflipbook.txt` en la raíz del proyecto; si no existe, los tests de red se saltan (`pytest.skip`).
- Trabajar en la rama `feature/gestion-periodicos`.

---

### Task 1: Módulo `github_pages.py` con `slug()`

**Files:**
- Create: `github_pages.py`
- Test: `test_github_pages.py`

**Interfaces:**
- Consumes: nada.
- Produces: `slug(nombre: str) -> str` (URL-segura: minúsculas, sin acentos, `[a-z0-9_-]`, sin guiones dobles ni extremos; vacío → `"periodico"`). Constantes `OWNER`, `REPO`, `BRANCH`, `PAGES_URL`, excepción `GitHubError`.

- [ ] **Step 1: Write the failing test**

```python
# test_github_pages.py
import github_pages as gp

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_github_pages.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'github_pages'` (o AttributeError).

- [ ] **Step 3: Write minimal implementation**

```python
# github_pages.py
"""Capa de red para publicar flipbooks en GitHub Pages. Sin tkinter."""
import os
import re
import json
import base64
import unicodedata
import urllib.request
import urllib.error

OWNER = "dtabuyodesigner"
REPO = "generador_flipbook"
BRANCH = "gh-pages"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
PAGES_URL = f"https://{OWNER}.github.io/{REPO}"


class GitHubError(Exception):
    """Error legible de la capa GitHub (para mostrar al usuario)."""


def slug(nombre):
    """Convierte un nombre en una cadena URL-segura."""
    s = unicodedata.normalize("NFKD", nombre or "")
    s = s.encode("ascii", "ignore").decode("ascii").lower().strip()
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-_")
    return s or "periodico"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest test_github_pages.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add github_pages.py test_github_pages.py
git commit -m "feat(github_pages): módulo con slug() URL-seguro"
```

---

### Task 2: Capa de red en `github_pages.py` (publicar/listar/borrar/existe)

**Files:**
- Modify: `github_pages.py`
- Modify: `test_github_pages.py`

**Interfaces:**
- Consumes: `slug`, `OWNER/REPO/BRANCH/API/PAGES_URL`, `GitHubError` (Task 1).
- Produces:
  - `publicar(token, nombre, output_dir) -> str` — sube `index.html` + `pages/*.png` bajo `<slug>/` **reemplazando la carpeta entera** (sin huérfanos); asegura rama y Pages; devuelve URL pública.
  - `listar(token) -> list[dict]` — `[{"nombre": str, "url": str}]` de las carpetas de primer nivel en `gh-pages` (excluye `.gitkeep`), ordenado por nombre. Lista vacía si la rama no existe.
  - `borrar(token, nombre) -> None` — elimina la carpeta `<slug>/` de `gh-pages`.
  - `existe(token, nombre) -> bool` — True si `<slug>/` ya está publicado.

- [ ] **Step 1: Write the failing test** (test real, se salta sin token)

```python
# añadir a test_github_pages.py
import os, time, tempfile, pytest

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

def test_ciclo_real_publicar_listar_borrar():
    import github_pages as gp
    tok = _token()
    nombre = f"zz-test-{int(time.time())}"
    s = gp.slug(nombre)
    try:
        url = gp.publicar(tok, nombre, _flipbook_tmp(3))
        assert url == f"{gp.PAGES_URL}/{s}/"
        assert gp.existe(tok, nombre) is True
        assert any(it["nombre"] == s for it in gp.listar(tok))
        # republish con menos páginas -> sin huérfanos
        gp.publicar(tok, nombre, _flipbook_tmp(1))
        _, blobs = gp._arbol_actual(tok)
        pgs = [b["path"] for b in blobs if b["path"].startswith(f"{s}/pages/")]
        assert pgs == [f"{s}/pages/page_001.png"], pgs
    finally:
        gp.borrar(tok, nombre)
    assert gp.existe(tok, nombre) is False
    assert all(it["nombre"] != s for it in gp.listar(tok))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_github_pages.py::test_ciclo_real_publicar_listar_borrar -v`
Expected: FAIL con `AttributeError: module 'github_pages' has no attribute 'publicar'` (o skip si no hay token — en ese caso, el implementador debe colocar el token para validar de verdad).

- [ ] **Step 3: Write minimal implementation** (añadir a `github_pages.py`)

```python
def _headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "flipbook-generator",
        "Content-Type": "application/json",
    }


def _request(token, method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in _headers(token).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _error_legible(err):
    """Mensaje legible (interno) a partir de un HTTPError."""
    try:
        data = json.loads(err.read().decode("utf-8"))
        return data.get("message", str(err))
    except Exception:
        return str(err)


def _get_ref_sha(token):
    """SHA del último commit de BRANCH; None si la rama no existe."""
    try:
        data = _request(token, "GET", f"{API}/git/ref/heads/{BRANCH}")
        return data["object"]["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _asegurar_rama(token):
    """Crea BRANCH como rama huérfana (con .gitkeep) si no existe. Devuelve SHA."""
    sha = _get_ref_sha(token)
    if sha:
        return sha
    blob = _request(token, "POST", f"{API}/git/blobs",
                    {"content": "", "encoding": "utf-8"})
    tree = _request(token, "POST", f"{API}/git/trees", {
        "tree": [{"path": ".gitkeep", "mode": "100644",
                  "type": "blob", "sha": blob["sha"]}]})
    commit = _request(token, "POST", f"{API}/git/commits", {
        "message": "Inicializar gh-pages", "tree": tree["sha"], "parents": []})
    _request(token, "POST", f"{API}/git/refs",
             {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    return commit["sha"]


def _asegurar_pages(token):
    """Activa GitHub Pages si no está. Ignora 409 (ya activo) y 422."""
    try:
        _request(token, "POST", f"{API}/pages",
                 {"source": {"branch": BRANCH, "path": "/"}})
    except urllib.error.HTTPError as e:
        if e.code in (409, 422):
            return
        raise


def _arbol_actual(token):
    """Devuelve (parent_sha, blobs) del último commit de BRANCH.
    blobs: lista de dicts {path, mode, type, sha} solo de type=='blob'.
    Si la rama no existe: (None, [])."""
    sha = _get_ref_sha(token)
    if not sha:
        return None, []
    commit = _request(token, "GET", f"{API}/git/commits/{sha}")
    tree = _request(token, "GET",
                    f"{API}/git/trees/{commit['tree']['sha']}?recursive=1")
    blobs = [{"path": e["path"], "mode": e["mode"],
              "type": "blob", "sha": e["sha"]}
             for e in tree.get("tree", []) if e["type"] == "blob"]
    return sha, blobs


def _archivos_flipbook(output_dir, s):
    """Pares (ruta_en_repo, ruta_local) de index.html + pages/*.png."""
    out = []
    idx = os.path.join(output_dir, "index.html")
    if os.path.exists(idx):
        out.append((f"{s}/index.html", idx))
    pages = os.path.join(output_dir, "pages")
    if os.path.isdir(pages):
        for f in sorted(os.listdir(pages)):
            if f.lower().endswith(".png"):
                out.append((f"{s}/pages/{f}", os.path.join(pages, f)))
    return out


def _commit_arbol(token, parent_sha, tree_entries, mensaje):
    """Crea un tree COMPLETO (sin base_tree), un commit y mueve la ref."""
    tree = _request(token, "POST", f"{API}/git/trees", {"tree": tree_entries})
    commit = _request(token, "POST", f"{API}/git/commits", {
        "message": mensaje, "tree": tree["sha"], "parents": [parent_sha]})
    _request(token, "PATCH", f"{API}/git/refs/heads/{BRANCH}",
             {"sha": commit["sha"]})


def existe(token, nombre):
    s = slug(nombre)
    _, blobs = _arbol_actual(token)
    return any(b["path"].startswith(f"{s}/") for b in blobs)


def listar(token):
    _, blobs = _arbol_actual(token)
    nombres = set()
    for b in blobs:
        parte = b["path"].split("/", 1)
        if len(parte) == 2:  # está dentro de una carpeta
            nombres.add(parte[0])
    return [{"nombre": n, "url": f"{PAGES_URL}/{n}/"} for n in sorted(nombres)]


def publicar(token, nombre, output_dir):
    s = slug(nombre)
    _asegurar_pages(token)
    _asegurar_rama(token)
    parent_sha, blobs = _arbol_actual(token)
    # conservar todo lo que NO sea de esta carpeta (reemplazo limpio)
    keep = [b for b in blobs if not b["path"].startswith(f"{s}/")]
    nuevos = []
    for repo_path, local in _archivos_flipbook(output_dir, s):
        with open(local, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")
        blob = _request(token, "POST", f"{API}/git/blobs",
                        {"content": content, "encoding": "base64"})
        nuevos.append({"path": repo_path, "mode": "100644",
                       "type": "blob", "sha": blob["sha"]})
    _commit_arbol(token, parent_sha, keep + nuevos, f"Publicar: {s}")
    return f"{PAGES_URL}/{s}/"


def borrar(token, nombre):
    s = slug(nombre)
    parent_sha, blobs = _arbol_actual(token)
    if parent_sha is None:
        return
    keep = [b for b in blobs if not b["path"].startswith(f"{s}/")]
    if len(keep) == len(blobs):
        return  # no había nada que borrar
    _commit_arbol(token, parent_sha, keep, f"Borrar: {s}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest test_github_pages.py -v`
Expected: PASS (7 passed). Si el test de red sale "skipped", coloca el token en `tokengenerarflipbook.txt` y vuelve a ejecutar para validarlo de verdad — debe pasar.

- [ ] **Step 5: Commit**

```bash
git add github_pages.py test_github_pages.py
git commit -m "feat(github_pages): publicar/listar/borrar/existe con reemplazo limpio"
```

---

### Task 3: Integrar el módulo en la GUI (slug visible, token fuera de la UI)

**Files:**
- Modify: `crear_flipbook.py`

**Interfaces:**
- Consumes: `github_pages.publicar/existe/slug` (Tasks 1-2).
- Produces: `subir_a_github` usa `github_pages.publicar`; label `self.slug_label` que muestra "Se publicará como: `<slug>`"; sección de token eliminada de la UI.

- [ ] **Step 1: Importar el módulo y eliminar las funciones gh_* migradas**

En la cabecera de `crear_flipbook.py`, tras los imports stdlib, añadir:

```python
import github_pages
```

Eliminar de `crear_flipbook.py` las funciones que ahora viven en el módulo: `_gh_headers`, `_gh_request`, `_gh_error_legible`, `_gh_get_ref_sha`, `gh_asegurar_rama`, `gh_asegurar_pages`, `gh_publicar_flipbook` (todo el bloque). NO tocar las funciones `wp_*`/`subir_a_wordpress` (quedan muertas pero presentes).

- [ ] **Step 2: Quitar la sección de token de la UI**

Localizar la sección `"3. Publicar en la web"` en `__init__` (el `LabelFrame` `sec_gh` con `self.gh_token` y el Checkbutton "Recordar token") y **eliminarla por completo**, junto con cualquier uso de `self.gh_token` y `self.recordar` fuera de `subir_a_wordpress`. La numeración de filas del grid de la columna izquierda debe seguir siendo correcta (el botón principal, progress, status, url_frame y button_frame mantienen su orden).

- [ ] **Step 3: Añadir el label de slug bajo el campo de nombre**

Tras el `self.nombre_output` (sección 1), añadir un label que muestre el slug en vivo:

```python
self.slug_label = ttk.Label(sec_pdf, text="", foreground="gray")
self.slug_label.grid(row=4, column=0, sticky=tk.W, pady=(0, 2))
self.nombre_output.bind("<KeyRelease>", self._actualizar_slug_label)
self._actualizar_slug_label()
```

Y el método:

```python
def _actualizar_slug_label(self, event=None):
    s = github_pages.slug(self.nombre_output.get())
    self.slug_label.config(text=f"Se publicará como:  {s}")
```

- [ ] **Step 4: Reescribir `subir_a_github` para usar el módulo**

Reemplazar el cuerpo de `subir_a_github` por:

```python
def subir_a_github(self, nombre, output_dir):
    """Publica en GitHub Pages. Devuelve la URL o None. El flipbook local
    nunca se rompe aunque falle la subida."""
    token = self._leer_token_github()
    if not token:
        messagebox.showwarning(
            "No se pudo publicar",
            "No se ha podido publicar en internet.\n\n"
            "Revisa tu conexión a internet. Si el problema sigue, avisa a Dani.\n\n"
            "El periódico se ha creado igualmente en tu equipo.")
        return None
    try:
        self.status_label.config(text="Publicando en internet...", foreground="orange")
        self.root.update()
        return github_pages.publicar(token, nombre, output_dir)
    except Exception:
        messagebox.showwarning(
            "No se pudo publicar",
            "No se ha podido publicar en internet.\n\n"
            "Revisa tu conexión a internet. Si el problema sigue, avisa a Dani.\n\n"
            "El periódico se ha creado igualmente en tu equipo.")
        return None
```

Nota: `_leer_token_github` ya no lee del campo UI (eliminado). Ajustarlo para que solo lea del archivo/config:

```python
def _leer_token_github(self):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    for path in (os.path.join(exe_dir, "tokengenerarflipbook.txt"),
                 os.path.join(script_dir, "tokengenerarflipbook.txt"),
                 os.path.join(os.path.dirname(script_dir), "tokengenerarflipbook.txt")):
        if os.path.exists(path):
            try:
                tok = open(path, encoding="utf-8").read().strip()
                if tok:
                    return tok
            except Exception:
                pass
    cfg = cargar_config()
    if cfg.get("github_token"):
        return _desofuscar(cfg["github_token"])
    return None
```

- [ ] **Step 5: Smoke test (construye la ventana sin bucle)**

Run:
```bash
python3 -c "import ast;ast.parse(open('crear_flipbook.py').read());print('parse OK')"
python3 - <<'PY'
import importlib.util, tkinter as tk
spec=importlib.util.spec_from_file_location("cf","crear_flipbook.py")
cf=importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
r=tk.Tk(); a=cf.CreadorFlipbook(r); r.update()
a.nombre_output.delete(0,"end"); a.nombre_output.insert(0,"Edición Marzo 2025")
a._actualizar_slug_label()
assert "edicion-marzo-2025" in a.slug_label.cget("text"), a.slug_label.cget("text")
assert not hasattr(a,"gh_token"), "gh_token debería haberse eliminado"
print("smoke OK:", a.slug_label.cget("text"))
r.destroy()
PY
```
Expected: `parse OK` y `smoke OK: Se publicará como:  edicion-marzo-2025`.

- [ ] **Step 6: Commit**

```bash
git add crear_flipbook.py
git commit -m "feat(gui): usar github_pages, mostrar slug y ocultar token a Pilar"
```

---

### Task 4: Subida en segundo plano + aviso de sobrescritura

**Files:**
- Modify: `crear_flipbook.py`

**Interfaces:**
- Consumes: `github_pages.existe/publicar`, `subir_a_github` (Task 3).
- Produces: `generar_flipbook` lanza la publicación en un `threading.Thread`; aviso `askyesno` si el slug ya existe; UI actualizada vía `self.root.after`.

- [ ] **Step 1: Aviso de sobrescritura antes de publicar**

En `generar_flipbook`, justo antes de llamar a la publicación, tras crear el flipbook local, añadir:

```python
token = self._leer_token_github()
if token and github_pages.existe(token, nombre):
    if not messagebox.askyesno(
        "Ya existe",
        f"Ya hay un periódico publicado con el nombre «{github_pages.slug(nombre)}».\n\n"
        "¿Quieres actualizarlo? Se sobrescribirá el anterior y el enlace "
        "seguirá siendo el mismo."):
        self.progress.stop()
        self.status_label.config(text="Publicación cancelada (flipbook local creado).",
                                 foreground="blue")
        return
```

(Importante: este chequeo es de red; si no hay token, se omite y sigue el flujo normal de `subir_a_github`, que ya avisa amablemente.)

- [ ] **Step 2: Publicar en un hilo (no congelar la UI)**

Reemplazar la llamada síncrona `self.post_url = self.subir_a_github(nombre, output_dir)` y el bloque de mensajes posterior por un arranque en hilo:

```python
self.status_label.config(text="Publicando en internet...", foreground="orange")
self._set_controles(False)  # deshabilita el botón principal mientras sube

def _trabajo():
    url = self._publicar_seguro(nombre, output_dir)
    self.root.after(0, lambda: self._fin_publicacion(url, len(images), output_dir))

threading.Thread(target=_trabajo, daemon=True).start()
```

Añadir los helpers (y `import threading` en cabecera):

```python
def _set_controles(self, activo):
    estado = tk.NORMAL if activo else tk.DISABLED
    self.btn_generar.config(state=estado)

def _publicar_seguro(self, nombre, output_dir):
    """Publica devolviendo URL o None; nunca lanza (corre en hilo)."""
    token = self._leer_token_github()
    if not token:
        return None
    try:
        return github_pages.publicar(token, nombre, output_dir)
    except Exception:
        return None

def _fin_publicacion(self, url, n_paginas, output_dir):
    self.progress.stop()
    self._set_controles(True)
    self.post_url = url
    if url:
        self.url_var.set(url)
        self.btn_copiar.config(state=tk.NORMAL)
        self.btn_post.config(state=tk.NORMAL)
        self.status_label.config(text=f"¡Publicado! ({n_paginas} páginas)", foreground="green")
        messagebox.showinfo("Publicado",
            "Tu periódico está publicado en internet.\n\n"
            f"Enlace:\n{url}\n\n"
            "Pulsa «Copiar enlace» y pégalo en la web del colegio.")
    else:
        self.status_label.config(text=f"Flipbook creado ({n_paginas} páginas). No publicado.", foreground="blue")
        messagebox.showwarning("No se pudo publicar",
            "No se ha podido publicar en internet.\n\n"
            "Revisa tu conexión a internet. Si el problema sigue, avisa a Dani.\n\n"
            f"El periódico está en tu equipo:\n{output_dir}")
    self._limpiar_preview_temp()
```

Requisito: el botón principal debe guardarse como `self.btn_generar` (hoy es anónimo). Cambiar su creación a:

```python
self.btn_generar = ttk.Button(left, text="🔗 Generar enlace para la web", command=self.generar_flipbook)
self.btn_generar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(6, 3))
```

`webbrowser.open(f"file://{html_path}")` (abrir el flipbook local) puede quedarse antes de lanzar el hilo, igual que ahora.

- [ ] **Step 3: Smoke test**

Run:
```bash
python3 -c "import ast;ast.parse(open('crear_flipbook.py').read());print('parse OK')"
python3 - <<'PY'
import importlib.util, tkinter as tk
spec=importlib.util.spec_from_file_location("cf","crear_flipbook.py")
cf=importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
r=tk.Tk(); a=cf.CreadorFlipbook(r); r.update()
assert hasattr(a,"btn_generar") and hasattr(a,"_fin_publicacion")
print("smoke OK")
r.destroy()
PY
```
Expected: `parse OK` y `smoke OK`.

- [ ] **Step 4: Commit**

```bash
git add crear_flipbook.py
git commit -m "feat(gui): publicar en segundo plano + aviso de sobrescritura"
```

---

### Task 5: Panel "Mis periódicos publicados" (ventana aparte)

**Files:**
- Modify: `crear_flipbook.py`

**Interfaces:**
- Consumes: `github_pages.listar/borrar` (Task 2), `self.nombre_output` (Task 3).
- Produces: botón `self.btn_panel` en la ventana principal; método `abrir_panel_periodicos` que crea un `Toplevel` con la lista y acciones.

- [ ] **Step 1: Botón para abrir el panel**

En `button_frame` de `__init__`, añadir (siempre habilitado):

```python
self.btn_panel = ttk.Button(button_frame, text="📚 Mis periódicos", command=self.abrir_panel_periodicos)
self.btn_panel.pack(side=tk.LEFT, padx=4)
```

- [ ] **Step 2: Implementar el panel**

Añadir a la clase:

```python
def abrir_panel_periodicos(self):
    win = tk.Toplevel(self.root)
    win.title("Mis periódicos publicados")
    win.geometry("720x420")
    cont = ttk.Frame(win, padding=10)
    cont.pack(fill=tk.BOTH, expand=True)
    estado = ttk.Label(cont, text="Cargando...", foreground="blue")
    estado.pack(anchor=tk.W)
    filas = ttk.Frame(cont)
    filas.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    def pintar(items, error=None):
        for w in filas.winfo_children():
            w.destroy()
        if error:
            estado.config(text="No se pudo cargar la lista. Revisa tu conexión "
                               "a internet. Si sigue, avisa a Dani.", foreground="red")
            return
        if not items:
            estado.config(text="Aún no hay periódicos publicados.", foreground="blue")
            return
        estado.config(text=f"{len(items)} periódico(s) publicado(s):", foreground="green")
        for it in items:
            fila = ttk.Frame(filas)
            fila.pack(fill=tk.X, pady=2)
            ttk.Label(fila, text=it["nombre"], width=26, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Button(fila, text="📋 Copiar", width=10,
                       command=lambda u=it["url"]: self._copiar_url(u)).pack(side=tk.LEFT, padx=2)
            ttk.Button(fila, text="🌐 Abrir", width=9,
                       command=lambda u=it["url"]: webbrowser.open(u)).pack(side=tk.LEFT, padx=2)
            ttk.Button(fila, text="🔄 Actualizar", width=12,
                       command=lambda n=it["nombre"]: self._actualizar_desde_panel(win, n)).pack(side=tk.LEFT, padx=2)
            ttk.Button(fila, text="🗑 Borrar", width=10,
                       command=lambda n=it["nombre"]: self._borrar_desde_panel(win, n, recargar)).pack(side=tk.LEFT, padx=2)

    def recargar():
        estado.config(text="Cargando...", foreground="blue")
        def _w():
            token = self._leer_token_github()
            try:
                items = github_pages.listar(token) if token else None
                err = None if token else "sin-token"
            except Exception:
                items, err = None, "error"
            self.root.after(0, lambda: pintar(items or [], error=err))
        threading.Thread(target=_w, daemon=True).start()

    recargar()

def _copiar_url(self, url):
    self.root.clipboard_clear()
    self.root.clipboard_append(url)
    self.root.update()

def _actualizar_desde_panel(self, win, nombre):
    self.nombre_output.delete(0, tk.END)
    self.nombre_output.insert(0, nombre)
    self._actualizar_slug_label()
    win.destroy()
    messagebox.showinfo("Actualizar periódico",
        f"Para actualizar «{nombre}»: elige el PDF nuevo con «Examinar…» y pulsa "
        "«Generar enlace para la web». Se sobrescribirá manteniendo el mismo enlace.")

def _borrar_desde_panel(self, win, nombre, recargar):
    if not messagebox.askyesno("Borrar periódico",
        f"¿Seguro que quieres borrar «{nombre}»?\n\n"
        "El enlace dejará de funcionar y tendrás que quitarlo también de la web "
        "del colegio (Drupal)."):
        return
    def _w():
        token = self._leer_token_github()
        ok = False
        try:
            if token:
                github_pages.borrar(token, nombre)
                ok = True
        except Exception:
            ok = False
        self.root.after(0, lambda: _fin(ok))
    def _fin(ok):
        if not ok:
            messagebox.showwarning("No se pudo borrar",
                "No se ha podido borrar. Revisa tu conexión a internet. "
                "Si el problema sigue, avisa a Dani.")
        recargar()
    threading.Thread(target=_w, daemon=True).start()
```

- [ ] **Step 3: Smoke test**

Run:
```bash
python3 -c "import ast;ast.parse(open('crear_flipbook.py').read());print('parse OK')"
python3 - <<'PY'
import importlib.util, tkinter as tk
spec=importlib.util.spec_from_file_location("cf","crear_flipbook.py")
cf=importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
r=tk.Tk(); a=cf.CreadorFlipbook(r); r.update()
assert hasattr(a,"btn_panel") and hasattr(a,"abrir_panel_periodicos")
a.abrir_panel_periodicos(); r.update()  # abre el Toplevel sin error
print("smoke OK")
r.destroy()
PY
```
Expected: `parse OK` y `smoke OK` (el Toplevel se crea; la carga real va en hilo).

- [ ] **Step 4: Verificación manual (con la app abierta)**

Lanzar `python3 crear_flipbook.py`, abrir "📚 Mis periódicos", comprobar que lista lo publicado, que Copiar/Abrir funcionan, que Actualizar rellena el nombre y cierra el panel, y que Borrar pide confirmación y refresca.

- [ ] **Step 5: Commit**

```bash
git add crear_flipbook.py
git commit -m "feat(gui): panel de periódicos (listar/copiar/abrir/actualizar/borrar)"
```

---

## Notas de coordinación de agentes

- **Task 1 y 2** (módulo) son independientes de la GUI → un agente.
- **Tasks 3, 4, 5** tocan todas `crear_flipbook.py` → **secuenciales** (mismo archivo), en orden. No paralelizar entre ellas para evitar conflictos.
- Recomendado: Agente A hace 1-2; tras revisar, Agente B hace 3→4→5 en serie. Revisión entre tareas.
