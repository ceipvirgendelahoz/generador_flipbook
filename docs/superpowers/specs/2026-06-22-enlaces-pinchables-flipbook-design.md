# Enlaces pinchables en el flipbook — diseño

## Problema
Cada página del flipbook es una imagen PNG, así que los hipervínculos reales que
trae el PDF (p. ej. "ver vídeo") no se pueden pulsar. Queremos que esos enlaces
sean pinchables en el flipbook, en su sitio.

## Alcance (Opción A)
Superponer zonas pinchables transparentes sobre la página, exactamente donde está
el enlace en el PDF. Cero trabajo extra para Pilar: si el PDF lleva el enlace,
funciona solo. Fuera de alcance: añadir enlaces a mano, lista de botones aparte.

## Componentes

### 1. `enlaces_pdf.py` (módulo puro, testeable)
`extraer_enlaces(pdf_path) -> dict[int, list[dict]]`
- Recorre las páginas; lee `/Annots` de subtipo `/Link` con acción `/A` y `/URI`.
- Convierte el `/Rect` (coords PDF, origen abajo-izquierda) a fracciones 0–1 con
  origen arriba-izquierda (CSS): `left=x1/pw`, `top=1-(y2/ph)`, `width=(x2-x1)/pw`,
  `height=(y2-y1)/ph`.
- Clave = nº de página (1-based). Páginas sin enlaces no aparecen (o lista vacía).
- Ignora enlaces internos (sin `/URI`). Nunca lanza por una anotación rara: la salta.

### 2. Integración en `crear_flipbook.py`
- En `generar_flipbook`, tras extraer las imágenes, llamar a
  `extraer_enlaces(pdf_path)` y pasar el dict a `generar_html`.

### 3. `generar_html(titulo, num_pages, ..., enlaces=None)`
- Cada página se envuelve en un contenedor `position:relative` que envuelve exactamente
  la `<img>`.
- Por cada enlace de esa página, un `<a>` absoluto en `%` (`left/top/width/height`),
  `target="_blank"`, `rel="noopener noreferrer"`, clase `.enlace-pdf`.
- CSS `.enlace-pdf`: transparente; al `:hover` leve realce (fondo translúcido +
  contorno) y `cursor:pointer`.
- Evitar que el gesto de pasar página (arrastre del visor) se trague el clic:
  `pointerdown`/`mousedown` sobre el enlace hacen `stopPropagation()`.

## Pruebas
- Unit: `test_enlaces_pdf.py` genera un PDF con reportlab con 2 enlaces en posiciones
  conocidas y verifica las fracciones (con tolerancia) y la URL.
- Visual: generar el flipbook del PDF de prueba (`bolsainterinos.app`) y comprobar
  que la zona cae sobre el texto y abre la URL en pestaña nueva.

## Casos límite
- PDF sin enlaces → flipbook idéntico al actual.
- Varios enlaces por página → varias zonas.
- Anotación malformada → se ignora, no rompe la generación.
