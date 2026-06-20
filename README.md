# Generador de Periódicos Digitales

App de escritorio (Python + tkinter) que convierte un **PDF** de periódico en un
**flipbook** HTML interactivo (efecto revista) y lo **publica en internet**
(GitHub Pages), devolviendo un **enlace público** listo para pegar.

Pensada para un colegio: la usuaria (Pilar) genera el periódico, copia el enlace
y lo pega en el portal del centro (Drupal de Castilla-La Mancha), que no admite
iframes/HTML embebido — por eso se publica fuera y se enlaza.

La app está organizada en **3 pestañas**: 1) Preparar PDF, 2) Generar flipbook,
3) Mis periódicos.

## Características

- **Preparar PDF** (pestaña 1): añadir documentos **Word y/o PDF**, **ordenarlos**
  libremente (subir/bajar/quitar) y **unirlos** en un solo PDF; los Word se
  convierten automáticamente (con MS Word o LibreOffice, lo que haya instalado).
  El PDF combinado pasa solo a la pestaña 2.
- Efecto revista realista (doble página, hojeo con animación) con StPageFlip.
- Título y descripción opcionales en la cabecera de la página publicada.
- **Publicación automática en GitHub Pages**: un enlace público por periódico.
- **Doble enlace al publicar**: uno **corto** (is.gd, recomendado) y el **largo**
  (github.io) como plan B si el corto no abre.
- **Pestaña "Mis periódicos"**: listar, copiar enlace, abrir, actualizar y borrar.
- Nombre saneado a URL-segura (slug) con vista previa "Se publicará como: …".
- Subida/conversión en segundo plano (la ventana no se congela).
- Sin tecnicismos para la usuaria: el token de GitHub no aparece en la interfaz.

## Arquitectura

- `crear_flipbook.py` — interfaz tkinter (3 pestañas) y generación del flipbook.
- `github_pages.py` — capa de red pura que habla con la API de GitHub: `slug`,
  `publicar`, `listar`, `borrar`, `existe`. Publica/borra reconstruyendo el árbol
  completo (sin huérfanos) en la rama `gh-pages`.
- `pdf_tools.py` — preparar el PDF: `detectar_convertidor`, `convertir_a_pdf`
  (Word→PDF con Word/LibreOffice), `unir_pdfs` (pypdf), `preparar_periodico`.
- `acortador.py` — `acortar(url)` con is.gd (gratis, sin clave).
- `test_github_pages.py`, `test_pdf_tools.py`, `test_acortador.py` — tests
  (incluyen ciclos reales contra GitHub / is.gd / LibreOffice).

**Conversión Word→PDF:** necesita **MS Word o LibreOffice** instalado en el PC
(se auto-detecta). No se puede empaquetar en el `.exe`; el equipo de Pilar tiene
uno de los dos.

Repo de publicación: `dtabuyodesigner/generador_flipbook`, rama `gh-pages`.
URL por periódico: `https://dtabuyodesigner.github.io/generador_flipbook/<slug>/`.

## Token (publicación)

La app lee el token de GitHub en silencio desde `tokengenerarflipbook.txt`
(junto al script o al .exe) o desde la config. Es un token **fine-grained**
limitado al repo, con permisos **Contents: RW** y **Pages: RW**. El archivo del
token está excluido de git (`.gitignore`) y nunca debe subirse.

## Uso en Linux (Zorin OS / Ubuntu)

Dependencias del sistema (Poppler para PDFs; LibreOffice para convertir Word):

    sudo apt-get install python3-tk poppler-utils libreoffice

Dependencias Python:

    pip install --break-system-packages pdf2image pillow pypdf

Ejecutar:

    python3 crear_flipbook.py

## Uso en Windows (.exe para Pilar)

- **INSTALAR_WINDOWS_FACIL.md** — guía paso a paso "para tontos" (recomendada).
- **INSTRUCCIONES_WINDOWS.md** — versión técnica (descargar de GitHub →
  `build.bat` → repartir `dist\` con el .exe + el token).
- **GUIA_PILAR.md** — uso diario de la usuaria final.

`build.bat` empaqueta Python y Poppler dentro del `.exe`, así que el equipo de
Pilar no necesita instalar nada (solo el `.exe` + `tokengenerarflipbook.txt`).

## Tests

    python3 -m pytest test_github_pages.py test_pdf_tools.py test_acortador.py -v

(Los ciclos reales usan el token de `tokengenerarflipbook.txt`, is.gd y
LibreOffice; si algo no está, esos tests se saltan.)

## Estructura del proyecto

- `crear_flipbook.py` — script principal (GUI de 3 pestañas + flipbook).
- `github_pages.py` — capa de red (GitHub Pages).
- `pdf_tools.py` — convertir Word→PDF y unir PDFs.
- `acortador.py` — acortar URLs (is.gd).
- `test_*.py` — tests de cada módulo.
- `build.bat` — constructor del .exe para Windows (empaqueta Poppler).
- `requirements.txt` — dependencias Python.
- `INSTALAR_EN_PC_DE_PILAR.md` / `INSTALAR_WINDOWS_FACIL.md` /
  `INSTRUCCIONES_WINDOWS.md` — crear el .exe en Windows.
- `GUIA_PILAR.md` — guía de uso para la usuaria final.
- `docs/superpowers/` — specs y planes.

## Licencia

MIT
