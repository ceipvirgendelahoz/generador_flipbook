# Preparar PDF del periódico (convertir + ordenar + unir) y pestañas

Fecha: 2026-06-20
Rama: `feature/preparar-pdf`

## Contexto y objetivo

Hoy la app parte de **un PDF ya hecho**. Pilar recibe las noticias en **Word y
PDF** y quiere prepararlas **dentro de la app**: convertir los Word a PDF,
**ordenarlos libremente** (p. ej. 6º, 4º, 3º, 1º, 2º…) y **unirlos en un solo
PDF** que será el periódico. Ese PDF combinado alimenta directamente el flujo
actual (vista previa → generar enlace).

Además, para que la ventana no crezca demasiado, la app se reorganiza en
**pestañas**: 1) Preparar PDF, 2) Generar flipbook, 3) Mis periódicos.

## Alcance

- Módulo nuevo `pdf_tools.py`: detectar convertidor, convertir Word→PDF, unir PDFs.
- Reorganizar la GUI en `ttk.Notebook` con 3 pestañas.
- Pestaña 1 nueva: añadir archivos (Word/PDF), ordenar (subir/bajar/quitar), unir.
- Encadenar: al unir, cargar el PDF combinado en la pestaña 2 y saltar a ella.
- Mover el panel "Mis periódicos" de ventana aparte (Toplevel) a la pestaña 3.

Fuera de alcance: arrastrar-soltar para ordenar (futuro), edición de páginas
sueltas, otros formatos (solo `.doc`, `.docx`, `.pdf`), generar el .exe.

## Arquitectura

### Módulo `pdf_tools.py` (lógica pura, sin tkinter, testeable)

- `detectar_convertidor() -> "word" | "libreoffice" | None`
  - Windows: si hay MS Word disponible (COM) → `"word"`; si no, si existe
    `soffice.exe` (rutas habituales de LibreOffice) → `"libreoffice"`; si no → `None`.
  - Linux/Mac: si existe `soffice`/`libreoffice` en PATH → `"libreoffice"`; si no → `None`.
  - Preferencia en Windows: Word primero (mejor fidelidad), luego LibreOffice.
- `convertir_a_pdf(archivo, carpeta_salida) -> str`
  - Si `archivo` ya es `.pdf`: lo copia a `carpeta_salida` y devuelve la ruta.
  - Si es `.doc`/`.docx`: lo convierte con el motor detectado y devuelve el `.pdf`.
  - Word: vía COM (`win32com`/`pywin32`), `SaveAs` formato PDF (17).
  - LibreOffice: `soffice --headless --convert-to pdf --outdir <carpeta> <archivo>`.
  - Si no hay convertidor y el archivo es Word: lanza `ConversionError` (mensaje legible).
- `unir_pdfs(rutas_ordenadas, ruta_salida) -> str`
  - Une los PDFs en el orden EXACTO de la lista (con `pypdf`). Devuelve `ruta_salida`.
- `preparar_periodico(archivos_ordenados, carpeta_salida, nombre_pdf) -> str`
  - Orquesta: convierte cada archivo a PDF (en orden) y los une en
    `carpeta_salida/<nombre_pdf>.pdf`. Devuelve la ruta del PDF combinado.
- Excepción `PdfToolsError` (base) / `ConversionError` con mensaje legible.

Dependencias: `pypdf` (unir, pura Python) y, solo en Windows con Word, `pywin32`.
LibreOffice se invoca por subproceso (sin dependencia Python).

### GUI `crear_flipbook.py` → `ttk.Notebook` con 3 pestañas

La ventana principal pasa a tener un `ttk.Notebook`. Cada pestaña es un `Frame`:

- **Pestaña 1 — "1. Preparar PDF"** (nueva, método `_construir_tab_preparar`):
  - Botón **➕ Añadir archivos** (`filedialog.askopenfilenames`, filtro Word/PDF).
  - `tk.Listbox` con los archivos añadidos (muestra el nombre de fichero).
  - Botones **🔼 Subir / 🔽 Bajar / 🗑 Quitar** que reordenan/eliminan el item
    seleccionado del Listbox (y de la lista interna `self.archivos_preparar`).
  - Etiqueta de estado + barra de progreso.
  - Botón **«Unir y crear el PDF del periódico»**: en un hilo, llama a
    `pdf_tools.preparar_periodico(...)`; al terminar (vía `root.after`), guarda la
    ruta, la carga en la pestaña 2 (`self.pdf_path`/`nombre_output`) y **cambia a
    la pestaña 2** (`notebook.select(tab2)`).
  - Si no hay convertidor y hay Word en la lista: mensaje amable y no une.
- **Pestaña 2 — "2. Generar flipbook"** (método `_construir_tab_flipbook`):
  - El formulario actual (selección de PDF, nombre+slug, título, descripción,
    botón "Generar enlace para la web", estado, URL+copiar) y la vista previa.
  - Es el contenido que hoy está en las columnas izquierda/derecha; se mueve tal
    cual dentro de esta pestaña.
- **Pestaña 3 — "3. Mis periódicos"** (método `_construir_tab_periodicos`):
  - El contenido del panel actual (lista con copiar/abrir/actualizar/borrar),
    movido del `Toplevel` a un `Frame` de pestaña, con un botón **🔄 Recargar**.
  - "Actualizar" pone el nombre en la pestaña 2 y **cambia a la pestaña 2**.

El botón "📚 Mis periódicos" que abría el Toplevel se elimina (ahora es pestaña).

## Flujo de datos

1. Pestaña 1: Pilar añade Word/PDF, los ordena, pulsa "Unir y crear el PDF".
2. `preparar_periodico` convierte y une → PDF combinado en `~/Descargas`.
3. La app carga ese PDF en la pestaña 2 y salta a ella.
4. Pilar genera vista previa; si le gusta, "Generar enlace para la web"; si no,
   vuelve a la pestaña 1, reordena y repite.

## Manejo de errores

- Conversión sin Word/LibreOffice → mensaje: "No encuentro Word ni LibreOffice
  para convertir los archivos de Word. Pásalos a PDF a mano, o instala
  LibreOffice." Los archivos que ya sean PDF se podrían unir igualmente.
- Fallo al convertir/unir un archivo → mensaje legible indicando qué archivo, sin
  trazas técnicas; no se rompe la app.
- Todo el trabajo de conversión/unión corre en hilo; la UI no se congela; los
  widgets se tocan solo vía `root.after`.

## Tests (`test_pdf_tools.py`)

Pura lógica, sin GUI. En el PC de desarrollo (Zorin) hay LibreOffice, así que la
conversión se puede probar de verdad.

- `unir_pdfs`: crear 2-3 PDFs pequeños (con PIL: `Image.save(..., "PDF")`), unir y
  verificar que el resultado tiene la suma de páginas y es un PDF válido (`pypdf`).
- `convertir_a_pdf` con un `.pdf` de entrada: devuelve un `.pdf` (passthrough/copia).
- `detectar_convertidor`: devuelve un valor no-None en un entorno con LibreOffice.
- `convertir_a_pdf` con un `.docx` mínimo (generado en el test): si
  `detectar_convertidor()` != None, convierte y produce un `.pdf` válido; si no,
  se salta (`pytest.skip`).
- `preparar_periodico`: mezcla de PDF + (docx si hay convertidor) → PDF combinado
  con el nº de páginas esperado.

La GUI se valida con smoke test (construir la ventana con las 3 pestañas, sin
bucle de eventos).

## Plan de ramas/agentes

- Rama `feature/preparar-pdf`.
- Implementación: (1) módulo `pdf_tools.py` + tests; (2) refactor GUI a Notebook
  moviendo el formulario actual a la pestaña 2 y el panel a la pestaña 3;
  (3) pestaña 1 (añadir/ordenar/unir) + encadenado a la pestaña 2.
  Las tareas 2 y 3 tocan `crear_flipbook.py` → secuenciales.
- `build.bat` y docs: añadir `pypdf` y `pywin32` a las dependencias.
