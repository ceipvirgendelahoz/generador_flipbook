# Preparar PDF del periódico + pestañas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir preparar el PDF del periódico dentro de la app (convertir Word→PDF, ordenar y unir varios PDFs) y reorganizar la interfaz en 3 pestañas.

**Architecture:** Módulo nuevo `pdf_tools.py` (lógica pura, testeable) para detectar convertidor, convertir Word→PDF y unir PDFs con `pypdf`. La GUI `crear_flipbook.py` pasa a un `ttk.Notebook` de 3 pestañas: Preparar PDF (nueva), Generar flipbook (la actual), Mis periódicos (el panel, antes Toplevel).

**Tech Stack:** Python 3.12, tkinter (ttk.Notebook), `pypdf` (unir), LibreOffice por subproceso o MS Word por COM (`pywin32`) para convertir, `threading`, `pytest`.

## Global Constraints

- Sin red en este módulo; es preparación local de archivos.
- Formatos de entrada: solo `.doc`, `.docx`, `.pdf`.
- Conversión Word→PDF: auto-detección. En Windows preferir **Word** (COM,
  `pywin32`); si no, **LibreOffice** (`soffice.exe`). En Linux/Mac: LibreOffice
  (`soffice`/`libreoffice` en PATH). Si no hay ninguno y hay Word que convertir →
  error legible: "No encuentro Word ni LibreOffice para convertir los archivos de
  Word. Pásalos a PDF a mano, o instala LibreOffice."
- `unir_pdfs` respeta el orden EXACTO de la lista recibida.
- Trabajo pesado (convertir/unir) en `threading.Thread`; los widgets tkinter se
  tocan solo vía `self.root.after(0, ...)`.
- Dependencias nuevas: `pypdf` (siempre) y `pywin32` (solo Windows con Word).
- El flipbook local y el flujo actual no deben romperse por este cambio.

---

### Task 1: Módulo `pdf_tools.py` (detectar / convertir / unir / preparar)

**Files:**
- Create: `pdf_tools.py`
- Test: `test_pdf_tools.py`

**Interfaces:**
- Consumes: nada (usa `pypdf`, stdlib, y opcionalmente LibreOffice/Word del sistema).
- Produces:
  - `detectar_convertidor() -> "word" | "libreoffice" | None`
  - `convertir_a_pdf(archivo: str, carpeta_salida: str) -> str` (ruta del .pdf)
  - `unir_pdfs(rutas_ordenadas: list[str], ruta_salida: str) -> str`
  - `preparar_periodico(archivos_ordenados: list[str], carpeta_salida: str, nombre_pdf: str) -> str`
  - Excepciones `PdfToolsError`, `ConversionError`.

- [ ] **Step 1: Preparar tooling de test**

Run:
```bash
pip install --break-system-packages --quiet pypdf python-docx
python3 -c "import pypdf, docx; print('ok')"
```
Expected: `ok` (pypdf para unir; python-docx solo para generar un .docx en los tests).

- [ ] **Step 2: Write the failing tests**

```python
# test_pdf_tools.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest test_pdf_tools.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'pdf_tools'`.

- [ ] **Step 4: Write the implementation**

```python
# pdf_tools.py
"""Preparar el PDF del periódico: detectar convertidor, convertir Word->PDF
y unir varios PDFs en el orden dado. Sin tkinter."""
import os
import shutil
import platform
import tempfile
import subprocess
from shutil import which


class PdfToolsError(Exception):
    """Error legible de la preparación de PDF."""


class ConversionError(PdfToolsError):
    """No se pudo convertir un archivo a PDF."""


_LIBRE_PATHS_WIN = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


def _buscar_soffice():
    if platform.system() == "Windows":
        for p in _LIBRE_PATHS_WIN:
            if os.path.exists(p):
                return p
        return which("soffice")
    return which("soffice") or which("libreoffice")


def _word_disponible():
    if platform.system() != "Windows":
        return False
    try:
        import winreg
        try:
            winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application")
            return True
        except OSError:
            return False
    except Exception:
        return False


def detectar_convertidor():
    """Devuelve 'word', 'libreoffice' o None segun lo instalado."""
    if _word_disponible():
        return "word"
    if _buscar_soffice():
        return "libreoffice"
    return None


def _convertir_word(archivo, carpeta_salida):
    import win32com.client  # solo Windows con Word
    salida = os.path.join(
        carpeta_salida,
        os.path.splitext(os.path.basename(archivo))[0] + ".pdf")
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(os.path.abspath(archivo))
        doc.SaveAs(os.path.abspath(salida), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close()
    finally:
        word.Quit()
    if not os.path.exists(salida):
        raise ConversionError(f"No se pudo convertir: {os.path.basename(archivo)}")
    return salida


def _convertir_libreoffice(archivo, carpeta_salida):
    soffice = _buscar_soffice()
    if not soffice:
        raise ConversionError("No encuentro LibreOffice para convertir.")
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir",
         os.path.abspath(carpeta_salida), os.path.abspath(archivo)],
        check=True, timeout=180,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    salida = os.path.join(
        carpeta_salida,
        os.path.splitext(os.path.basename(archivo))[0] + ".pdf")
    if not os.path.exists(salida):
        raise ConversionError(f"No se pudo convertir: {os.path.basename(archivo)}")
    return salida


def convertir_a_pdf(archivo, carpeta_salida):
    """Devuelve la ruta a un PDF: copia si ya es PDF, o convierte si es Word."""
    os.makedirs(carpeta_salida, exist_ok=True)
    ext = os.path.splitext(archivo)[1].lower()
    if ext == ".pdf":
        destino = os.path.join(carpeta_salida, os.path.basename(archivo))
        if os.path.abspath(archivo) != os.path.abspath(destino):
            shutil.copy(archivo, destino)
        return destino
    if ext in (".doc", ".docx"):
        motor = detectar_convertidor()
        if motor == "word":
            return _convertir_word(archivo, carpeta_salida)
        if motor == "libreoffice":
            return _convertir_libreoffice(archivo, carpeta_salida)
        raise ConversionError(
            "No encuentro Word ni LibreOffice para convertir los archivos de "
            "Word. Pásalos a PDF a mano, o instala LibreOffice.")
    raise ConversionError(f"Formato no soportado: {ext}")


def unir_pdfs(rutas_ordenadas, ruta_salida):
    """Une los PDFs en el orden EXACTO de la lista. Devuelve ruta_salida."""
    from pypdf import PdfWriter
    carpeta = os.path.dirname(os.path.abspath(ruta_salida))
    os.makedirs(carpeta, exist_ok=True)
    writer = PdfWriter()
    try:
        for r in rutas_ordenadas:
            writer.append(r)
        with open(ruta_salida, "wb") as f:
            writer.write(f)
    finally:
        writer.close()
    return ruta_salida


def preparar_periodico(archivos_ordenados, carpeta_salida, nombre_pdf):
    """Convierte cada archivo a PDF (en orden) y los une en
    carpeta_salida/<nombre_pdf>.pdf. Devuelve la ruta del PDF combinado."""
    os.makedirs(carpeta_salida, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="prep_periodico_")
    pdfs = []
    for i, archivo in enumerate(archivos_ordenados):
        sub = os.path.join(tmp, str(i))  # subcarpeta por índice: evita choques de nombre
        os.makedirs(sub, exist_ok=True)
        pdfs.append(convertir_a_pdf(archivo, sub))
    nombre = nombre_pdf if nombre_pdf.lower().endswith(".pdf") else nombre_pdf + ".pdf"
    salida = os.path.join(carpeta_salida, nombre)
    unir_pdfs(pdfs, salida)
    return salida
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest test_pdf_tools.py -v`
Expected: PASS (5 passed; el test de docx usa LibreOffice real en el PC de desarrollo).

- [ ] **Step 6: Commit**

```bash
git add pdf_tools.py test_pdf_tools.py
git commit -m "feat(pdf_tools): convertir Word->PDF, unir PDFs y preparar periodico"
```

---

### Task 2: Reorganizar la GUI en 3 pestañas (ttk.Notebook)

**Files:**
- Modify: `crear_flipbook.py`

**Interfaces:**
- Consumes: nada nuevo.
- Produces: `self.notebook`, `self.tab_preparar`, `self.tab_flipbook`,
  `self.tab_periodicos`; métodos `_construir_tab_flipbook(self, parent)`,
  `_construir_tab_periodicos(self, parent)`, `_construir_tab_preparar(self, parent)`
  (este último, stub en esta tarea; lo llena la Task 3).

Esta tarea NO cambia el comportamiento: solo mete lo existente en pestañas.

- [ ] **Step 1: Crear el Notebook en `__init__`**

En `__init__`, tras `cfg = cargar_config()` y la configuración de `style`,
ELIMINA el layout actual de columnas sobre `root` (las líneas que hacen
`root.columnconfigure(...)`, `root.rowconfigure(...)`, crean `left = ttk.Frame(root, ...)`
y `right = ttk.LabelFrame(root, ...)` y todo el cuerpo que construye esas dos
columnas) y MUEVE ese cuerpo al método `_construir_tab_flipbook` (Step 2).
En su lugar, en `__init__` deja:

```python
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_preparar = ttk.Frame(self.notebook)
        self.tab_flipbook = ttk.Frame(self.notebook)
        self.tab_periodicos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_preparar, text="1. Preparar PDF")
        self.notebook.add(self.tab_flipbook, text="2. Generar flipbook")
        self.notebook.add(self.tab_periodicos, text="3. Mis periódicos")

        self._construir_tab_flipbook(self.tab_flipbook)
        self._construir_tab_periodicos(self.tab_periodicos)
        self._construir_tab_preparar(self.tab_preparar)
```

Mantén al final de `__init__` lo que ya hubiera tras construir la UI (p. ej.
`self.root.protocol("WM_DELETE_WINDOW", self._on_close)`).

- [ ] **Step 2: Mover el formulario actual a `_construir_tab_flipbook`**

Crea el método y pega DENTRO el cuerpo que construía las dos columnas, cambiando
únicamente el padre `root` por `parent`:

```python
    def _construir_tab_flipbook(self, parent):
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        left = ttk.Frame(parent, padding="12")
        # ... (TODO el contenido actual de la columna izquierda y derecha,
        #      idéntico, pero con 'parent' en lugar de 'root' como padre de
        #      'left' y 'right'.)
```

No cambies nada más de ese contenido (secciones 1/2, botón generar, estado, URL,
botones, vista previa): solo el padre pasa de `root` a `parent`.

- [ ] **Step 3: Convertir el panel (Toplevel) en `_construir_tab_periodicos`**

Sustituye el método `abrir_panel_periodicos` por `_construir_tab_periodicos`, que
construye los MISMOS widgets pero sobre `parent` (sin `Toplevel`, sin `win`). Usa
exactamente este cuerpo:

```python
    def _construir_tab_periodicos(self, parent):
        cont = ttk.Frame(parent, padding=10)
        cont.pack(fill=tk.BOTH, expand=True)
        barra = ttk.Frame(cont)
        barra.pack(fill=tk.X)
        ttk.Button(barra, text="🔄 Recargar",
                   command=lambda: self._recargar_periodicos()).pack(side=tk.LEFT)
        self._periodicos_estado = ttk.Label(cont, text="", foreground="blue")
        self._periodicos_estado.pack(anchor=tk.W, pady=(6, 0))
        self._periodicos_filas = ttk.Frame(cont)
        self._periodicos_filas.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._recargar_periodicos()

    def _pintar_periodicos(self, items, error=None):
        for w in self._periodicos_filas.winfo_children():
            w.destroy()
        if error:
            self._periodicos_estado.config(
                text="No se pudo cargar la lista. Revisa tu conexión a internet. "
                     "Si el problema sigue, avisa a Dani.", foreground="red")
            return
        if not items:
            self._periodicos_estado.config(text="Aún no hay periódicos publicados.",
                                           foreground="blue")
            return
        self._periodicos_estado.config(text=f"{len(items)} periódico(s) publicado(s):",
                                       foreground="green")
        for it in items:
            fila = ttk.Frame(self._periodicos_filas)
            fila.pack(fill=tk.X, pady=2)
            ttk.Label(fila, text=it["nombre"], width=26, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Button(fila, text="📋 Copiar", width=10,
                       command=lambda u=it["url"]: self._copiar_url(u)).pack(side=tk.LEFT, padx=2)
            ttk.Button(fila, text="🌐 Abrir", width=9,
                       command=lambda u=it["url"]: webbrowser.open(u)).pack(side=tk.LEFT, padx=2)
            ttk.Button(fila, text="🔄 Actualizar", width=12,
                       command=lambda n=it["nombre"]: self._actualizar_desde_panel(n)).pack(side=tk.LEFT, padx=2)
            ttk.Button(fila, text="🗑 Borrar", width=10,
                       command=lambda n=it["nombre"]: self._borrar_desde_panel(n)).pack(side=tk.LEFT, padx=2)

    def _recargar_periodicos(self):
        self._periodicos_estado.config(text="Cargando...", foreground="blue")
        def _w():
            token = self._leer_token_github()
            try:
                items = github_pages.listar(token) if token else None
                err = None if token else "sin-token"
            except Exception:
                items, err = None, "error"
            self.root.after(0, lambda: self._pintar_periodicos(items or [], error=err))
        threading.Thread(target=_w, daemon=True).start()
```

- [ ] **Step 4: Adaptar `_actualizar_desde_panel` y `_borrar_desde_panel`**

Cambia sus firmas (ya no reciben `win`/`recargar`) y usa el notebook + recarga:

```python
    def _actualizar_desde_panel(self, nombre):
        self.nombre_output.delete(0, tk.END)
        self.nombre_output.insert(0, nombre)
        self._actualizar_slug_label()
        self.notebook.select(self.tab_flipbook)
        messagebox.showinfo("Actualizar periódico",
            f"Para actualizar «{nombre}»: elige el PDF nuevo con «Examinar…» y pulsa "
            "«Generar enlace para la web». Se sobrescribirá manteniendo el mismo enlace.")

    def _borrar_desde_panel(self, nombre):
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
                    objetivo = github_pages.slug(nombre)
                    for _ in range(12):
                        try:
                            if all(it["nombre"] != objetivo for it in github_pages.listar(token)):
                                break
                        except Exception:
                            pass
                        time.sleep(1.0)
            except Exception:
                ok = False
            self.root.after(0, lambda: _fin(ok))
        def _fin(ok):
            if not ok:
                messagebox.showwarning("No se pudo borrar",
                    "No se ha podido borrar. Revisa tu conexión a internet. "
                    "Si el problema sigue, avisa a Dani.")
            self._recargar_periodicos()
        threading.Thread(target=_w, daemon=True).start()
```

Elimina el botón `self.btn_panel` y cualquier referencia a `abrir_panel_periodicos`
y al antiguo `_copiar_enlace`/panel que ya no apliquen. Conserva `_copiar_url`.

- [ ] **Step 5: Stub de `_construir_tab_preparar` (lo llena la Task 3)**

```python
    def _construir_tab_preparar(self, parent):
        ttk.Label(parent, padding=20,
                  text="Preparar PDF (en construcción)").pack()
```

- [ ] **Step 6: Smoke test**

Run:
```bash
python3 -c "import ast;ast.parse(open('crear_flipbook.py').read());print('parse OK')"
python3 - <<'PY'
import importlib.util, tkinter as tk
spec=importlib.util.spec_from_file_location("cf","crear_flipbook.py")
cf=importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
r=tk.Tk(); a=cf.CreadorFlipbook(r); r.update()
assert hasattr(a,"notebook") and hasattr(a,"tab_preparar")
assert a.notebook.index("end")==3, "deben ser 3 pestañas"
assert hasattr(a,"_construir_tab_flipbook") and hasattr(a,"_recargar_periodicos")
assert hasattr(a,"btn_generar") and hasattr(a,"slug_label")
print("smoke OK")
r.destroy()
PY
```
Expected: `parse OK` y `smoke OK`.

- [ ] **Step 7: Commit**

```bash
git add crear_flipbook.py
git commit -m "refactor(gui): 3 pestañas (Notebook); panel de periodicos como pestaña"
```

---

### Task 3: Pestaña "1. Preparar PDF" (añadir, ordenar, unir, encadenar)

**Files:**
- Modify: `crear_flipbook.py`

**Interfaces:**
- Consumes: `pdf_tools.preparar_periodico/detectar_convertidor` (Task 1),
  `self.notebook`, `self.tab_flipbook`, `self.pdf_path`, `self.nombre_output`,
  `self._actualizar_slug_label` (Tasks 2 y anteriores).
- Produces: `_construir_tab_preparar` completo; `self.archivos_preparar` (lista de
  rutas en orden); helpers de añadir/subir/bajar/quitar/unir.

- [ ] **Step 1: Importar pdf_tools**

En la cabecera de `crear_flipbook.py`, junto a los demás imports locales, añade:

```python
import pdf_tools
```

- [ ] **Step 2: Reemplazar el stub por la pestaña completa**

Sustituye el método `_construir_tab_preparar` (stub de la Task 2) por:

```python
    def _construir_tab_preparar(self, parent):
        self.archivos_preparar = []  # rutas en el orden elegido
        cont = ttk.Frame(parent, padding="12")
        cont.pack(fill=tk.BOTH, expand=True)
        cont.columnconfigure(0, weight=1)
        cont.rowconfigure(2, weight=1)

        ttk.Label(cont, text="Añade los documentos (Word o PDF) y ponlos en el "
                             "orden que quieras. Se unirán en un solo PDF.",
                  wraplength=560, justify=tk.LEFT).grid(row=0, column=0, columnspan=2, sticky=tk.W)

        botones_add = ttk.Frame(cont)
        botones_add.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(6, 4))
        ttk.Button(botones_add, text="➕ Añadir archivos",
                   command=self._preparar_anadir).pack(side=tk.LEFT)

        self.lista_preparar = tk.Listbox(cont, height=10, activestyle="dotbox")
        self.lista_preparar.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        orden = ttk.Frame(cont)
        orden.grid(row=2, column=1, sticky=tk.N, padx=(8, 0))
        ttk.Button(orden, text="🔼 Subir", width=12, command=self._preparar_subir).pack(pady=2)
        ttk.Button(orden, text="🔽 Bajar", width=12, command=self._preparar_bajar).pack(pady=2)
        ttk.Button(orden, text="🗑 Quitar", width=12, command=self._preparar_quitar).pack(pady=2)

        self.preparar_estado = ttk.Label(cont, text="", foreground="blue")
        self.preparar_estado.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(6, 2))
        self.preparar_progress = ttk.Progressbar(cont, mode="indeterminate")
        self.preparar_progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)

        self.btn_unir = ttk.Button(cont, text="📎 Unir y crear el PDF del periódico",
                                   command=self._preparar_unir)
        self.btn_unir.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(4, 0))

    def _preparar_refrescar_lista(self):
        self.lista_preparar.delete(0, tk.END)
        for ruta in self.archivos_preparar:
            self.lista_preparar.insert(tk.END, os.path.basename(ruta))

    def _preparar_anadir(self):
        rutas = filedialog.askopenfilenames(
            title="Elige documentos (Word o PDF)",
            filetypes=[("Documentos", "*.pdf *.doc *.docx"),
                       ("PDF", "*.pdf"), ("Word", "*.doc *.docx")])
        for r in rutas:
            self.archivos_preparar.append(r)
        self._preparar_refrescar_lista()

    def _preparar_sel(self):
        sel = self.lista_preparar.curselection()
        return sel[0] if sel else None

    def _preparar_subir(self):
        i = self._preparar_sel()
        if i is None or i == 0:
            return
        self.archivos_preparar[i-1], self.archivos_preparar[i] = \
            self.archivos_preparar[i], self.archivos_preparar[i-1]
        self._preparar_refrescar_lista()
        self.lista_preparar.selection_set(i-1)

    def _preparar_bajar(self):
        i = self._preparar_sel()
        if i is None or i >= len(self.archivos_preparar) - 1:
            return
        self.archivos_preparar[i+1], self.archivos_preparar[i] = \
            self.archivos_preparar[i], self.archivos_preparar[i+1]
        self._preparar_refrescar_lista()
        self.lista_preparar.selection_set(i+1)

    def _preparar_quitar(self):
        i = self._preparar_sel()
        if i is None:
            return
        del self.archivos_preparar[i]
        self._preparar_refrescar_lista()

    def _preparar_unir(self):
        if not self.archivos_preparar:
            messagebox.showinfo("Sin archivos", "Añade al menos un documento.")
            return
        # Si hay Word y no hay convertidor, avisar antes de empezar.
        hay_word = any(r.lower().endswith((".doc", ".docx")) for r in self.archivos_preparar)
        if hay_word and pdf_tools.detectar_convertidor() is None:
            messagebox.showwarning("No se puede convertir Word",
                "No encuentro Word ni LibreOffice para convertir los archivos de "
                "Word. Pásalos a PDF a mano, o instala LibreOffice.")
            return
        nombre = self.nombre_output.get().strip() or "periodico"
        nombre = github_pages.slug(nombre)
        carpeta = os.path.abspath(os.path.expanduser("~/Descargas"))
        archivos = list(self.archivos_preparar)
        self.preparar_progress.start()
        self.preparar_estado.config(text="Preparando el PDF...", foreground="orange")
        self.btn_unir.config(state=tk.DISABLED)

        def _w():
            try:
                ruta = pdf_tools.preparar_periodico(archivos, carpeta, nombre)
                self.root.after(0, lambda: _ok(ruta))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda: _err(msg))

        def _ok(ruta):
            self.preparar_progress.stop()
            self.btn_unir.config(state=tk.NORMAL)
            self.preparar_estado.config(text="PDF creado ✅", foreground="green")
            self.pdf_path.set(ruta)
            self.notebook.select(self.tab_flipbook)
            messagebox.showinfo("PDF listo",
                "He unido los documentos en un PDF.\n\n"
                "Ahora pulsa «Generar vista previa» para verlo y, si te gusta, "
                "«Generar enlace para la web».")

        def _err(msg):
            self.preparar_progress.stop()
            self.btn_unir.config(state=tk.NORMAL)
            self.preparar_estado.config(text="❌ No se pudo crear el PDF", foreground="red")
            messagebox.showwarning("No se pudo crear el PDF",
                f"Hubo un problema preparando el PDF.\n\n{msg}")

        threading.Thread(target=_w, daemon=True).start()
```

Nota: `filedialog` ya está importado (se usa en `seleccionar_pdf`). `self.pdf_path`
es el `StringVar` del PDF en la pestaña 2; al hacer `self.pdf_path.set(ruta)` queda
seleccionado el PDF combinado.

- [ ] **Step 3: Smoke test**

Run:
```bash
python3 -c "import ast;ast.parse(open('crear_flipbook.py').read());print('parse OK')"
python3 - <<'PY'
import importlib.util, tkinter as tk
spec=importlib.util.spec_from_file_location("cf","crear_flipbook.py")
cf=importlib.util.module_from_spec(spec); spec.loader.exec_module(cf)
r=tk.Tk(); a=cf.CreadorFlipbook(r); r.update()
assert hasattr(a,"archivos_preparar") and hasattr(a,"lista_preparar") and hasattr(a,"btn_unir")
# simular orden interno
a.archivos_preparar=["/x/a.pdf","/x/b.pdf"]; a._preparar_refrescar_lista()
assert a.lista_preparar.size()==2
print("smoke OK")
r.destroy()
PY
```
Expected: `parse OK` y `smoke OK`.

- [ ] **Step 4: Verificación funcional real (con LibreOffice del sistema)**

Run:
```bash
python3 - <<'PY'
import os, tempfile
import pdf_tools
from PIL import Image
from docx import Document
d=tempfile.mkdtemp()
p=os.path.join(d,"hoja.pdf"); Image.new("RGB",(240,320),"white").save(p,"PDF")
doc=Document(); doc.add_paragraph("Noticia de 6º"); w=os.path.join(d,"sexto.docx"); doc.save(w)
out=pdf_tools.preparar_periodico([w,p], d, "periodico_test")  # word primero, pdf despues
from pypdf import PdfReader
print("paginas combinadas:", len(PdfReader(out).pages), "->", out)
PY
```
Expected: imprime un PDF combinado con >=2 páginas (Word convertido + PDF), confirmando orden y unión reales.

- [ ] **Step 5: Commit**

```bash
git add crear_flipbook.py
git commit -m "feat(gui): pestaña Preparar PDF (añadir/ordenar/unir) encadenada al flipbook"
```

---

## Notas de coordinación de agentes

- **Task 1** (módulo) es independiente → un agente (modelo barato; el plan trae
  el código completo).
- **Task 2 y 3** tocan `crear_flipbook.py` → **secuenciales** (Task 2 antes que 3),
  modelo estándar (refactor de GUI con cuidado). No paralelizar entre ellas.
- Tras las 3: actualizar `build.bat`, `requirements.txt` y docs para añadir
  `pypdf`/`pywin32` (se hará fuera del plan, en la fase de cierre).
