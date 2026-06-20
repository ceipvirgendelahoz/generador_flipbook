# Gestión de periódicos publicados (P1 + P2)

Fecha: 2026-06-20
Rama: `feature/gestion-periodicos`

## Contexto y objetivo

La app genera flipbooks de periódicos y los publica en GitHub Pages
(`https://dtabuyodesigner.github.io/generador_flipbook/<slug>/`). La usaria
final es **Pilar**, sin conocimientos técnicos, que solo copia el enlace y lo
pega en el Drupal del colegio.

Huecos actuales que se resuelven:

- **Modificar** un periódico: hoy solo funciona si se regenera con el nombre
  exacto, sin aviso, y deja imágenes huérfanas si la nueva versión tiene menos
  páginas.
- **Borrar** un periódico: hoy imposible desde la app.
- **Bug**: el nombre no se sanea → con espacios/acentos la URL sale rota.
- **UX**: la subida congela la ventana; Pilar ve campos técnicos (token) que no
  entiende.

## Alcance

**P1**: panel de periódicos publicados (listar/copiar/abrir/actualizar/borrar),
saneo de nombre (slug), aviso de sobrescritura.
**P2**: subida en segundo plano (hilo), republish sin huérfanos, manejo de token
y errores sin tecnicismos.

Fuera de alcance: generar el .exe, merge a main, token fine-grained (P3),
publicar directo en Drupal, QR.

## Arquitectura

Se extrae la capa de red a un módulo nuevo **`github_pages.py`** (funciones
puras, sin tkinter, testeable de forma aislada). `crear_flipbook.py` se queda
con la GUI e importa el módulo. Las funciones GitHub actuales (`_gh_*`,
`gh_publicar_flipbook`, `gh_asegurar_*`) se mueven al módulo.

### `github_pages.py` (interfaz pública)

Constantes: `OWNER="dtabuyodesigner"`, `REPO="generador_flipbook"`,
`BRANCH="gh-pages"`.

- `slug(nombre) -> str`
  Minúsculas, sin acentos (NFKD), espacios → `-`, solo `[a-z0-9-_]`, colapsa
  guiones repetidos, recorta extremos. Cadena vacía → `"periodico"`.
- `publicar(token, nombre, output_dir) -> str`
  `s = slug(nombre)`. Sube `index.html` + `pages/*.png` bajo `s/`,
  **reemplazando por completo** la carpeta `s/` (sin huérfanos). Devuelve la URL
  pública. Asegura la rama y GitHub Pages.
- `listar(token) -> list[dict]`
  Carpetas de primer nivel en `gh-pages` (excluye `.gitkeep`). Cada item:
  `{"nombre": s, "url": ".../<s>/"}`. Ordenado por nombre.
- `borrar(token, nombre) -> None`
  Elimina la carpeta `slug(nombre)/` de `gh-pages` (commit que reconstruye el
  árbol sin esa carpeta).
- `existe(token, nombre) -> bool`
  True si `slug(nombre)/` ya está publicado (para el aviso de sobrescritura).

Helpers internos: `_headers`, `_request`, `_error_legible`, `_get_ref_sha`,
`_asegurar_rama`, `_asegurar_pages`, `_arbol_actual` (lista blobs del último
commit). Excepción propia opcional `GitHubError` con mensaje legible.

**Republish/borrado limpio**: ambos parten del árbol actual completo
(`_arbol_actual`), filtran los blobs bajo `s/` y crean un tree nuevo **sin
`base_tree`** con el resto + (en publicar) los archivos nuevos. Así nunca quedan
huérfanos.

## GUI (`crear_flipbook.py`)

### Saneo de nombre
Al generar: `s = github_pages.slug(nombre)`. Se muestra a Pilar el nombre final
debajo del campo: *"Se publicará como: `<s>`"* (label que se actualiza en vivo o
al generar). Carpeta local y URL usan el mismo slug → siempre coinciden.

### Token oculto (Pilar no lo ve)
- Se **elimina de la interfaz** la sección "Publicar en la web" y el campo de
  token, junto con `self.gh_token` y "Recordar token".
- El token se lee en silencio con `_leer_token_github()` (campo eliminado →
  solo archivo `tokengenerarflipbook.txt` junto al ejecutable/script o config).
- Mensajes **sin tecnicismos**. Si falta token / 401 / fallo de subida:
  > "No se ha podido publicar en internet. Revisa tu conexión a internet. Si el
  > problema sigue, avisa a Dani."
  Nunca aparece "token". El flipbook local siempre se crea.

### Publicar en segundo plano (hilo)
- La subida corre en `threading.Thread`. Durante la subida: botón principal
  deshabilitado, `progress` activo, status "Publicando en internet…".
- El hilo NO toca widgets directamente: al terminar usa `self.root.after(0, cb)`
  para volver al hilo de tkinter y rellenar URL/estado/errores.
- Aviso de sobrescritura **antes** de lanzar el hilo: si `existe(slug)` →
  `askyesno` *"Ya hay un periódico con este nombre. ¿Actualizarlo? (se
  sobrescribe el anterior)"*. Si "no", se cancela la publicación (el flipbook
  local queda hecho igual).

### Panel "📚 Mis periódicos publicados" (ventana aparte)
- Botón nuevo en la ventana principal abre un `tk.Toplevel`.
- Al abrir, carga la lista en un hilo (muestra "Cargando…"); si falla la red →
  mensaje amable y lista vacía.
- Cada fila: **nombre** · **URL** (readonly) · **📋 Copiar** · **🌐 Abrir** ·
  **🔄 Actualizar** · **🗑 Borrar**.
  - Copiar → portapapeles. Abrir → navegador.
  - Actualizar → cierra el panel, escribe ese nombre en `nombre_output` del
    formulario principal y enfoca el botón Examinar (Pilar elige PDF y Genera →
    sobrescribe; saltará el aviso de sobrescritura, confirmando la intención).
  - Borrar → `askyesno` *"¿Seguro? El enlace dejará de funcionar y tendrás que
    quitarlo del Drupal."* → `borrar()` en hilo → refresca la lista.

## Manejo de errores

- Toda llamada de red (publicar/listar/borrar) captura HTTPError/URLError/genéricas.
- 401/403 y ausencia de token → mensaje amable "avisa a Dani".
- Otros → "No se ha podido publicar/cargar/borrar. Revisa tu conexión…".
- El resultado local (carpeta + index.html) nunca depende de la red.

## Tests

`test_github_pages.py` (ejecutable con el token real del entorno):

- `slug()`: acentos, espacios, mayúsculas, símbolos, vacío, guiones repetidos.
- Ciclo real contra `gh-pages` con un nombre de prueba único
  (`zz-test-<timestamp>`):
  1. `publicar` → devuelve URL.
  2. `existe` == True; `listar` lo incluye.
  3. Republish con menos páginas → no quedan huérfanos (verificar árbol).
  4. `borrar` → `existe` == False; ya no está en `listar`.
  - `finally`: borrar el nombre de prueba pase lo que pase.

La GUI se valida con smoke test (construir la ventana, abrir el panel) sin
bucle de eventos.

## Plan de ramas/agentes

- Rama: `feature/gestion-periodicos` (ya creada, parte de `feature/github-pages`).
- Implementación repartida en agentes (Sonnet): (1) módulo `github_pages.py` +
  tests; (2) integración GUI (slug, hilos, quitar token de UI); (3) panel
  Toplevel. Coordinados para no pisarse (el panel depende del módulo).
