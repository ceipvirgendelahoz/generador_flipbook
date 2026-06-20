# 🚀 Crear el .EXE en Windows (paso a paso)

Guía para **descargar el proyecto desde GitHub** y generar el ejecutable
`GeneradorPeriodico.exe` que usará Pilar. Esto se hace **una sola vez** (o cada
vez que haya cambios nuevos).

> ℹ️ El `.exe` SOLO se puede crear desde Windows (PyInstaller no compila para
> Windows desde Linux/Mac). Por eso estos pasos van en el PC con Windows.

---

## PASO 1 — Descargar el proyecto desde GitHub

Tienes dos formas. La más sencilla:

### Opción A — Descargar ZIP (sin instalar nada extra)
1. Abre en el navegador: **https://github.com/dtabuyodesigner/generador_flipbook**
2. Botón verde **`<> Code`** → **Download ZIP**.
3. Extrae el ZIP, por ejemplo en `C:\GeneradorPeriodico\`.
   (Dentro tendrás `crear_flipbook.py`, `github_pages.py`, `build.bat`, etc.)

### Opción B — Con Git (si lo tienes instalado)
```cmd
cd C:\
git clone https://github.com/dtabuyodesigner/generador_flipbook.git GeneradorPeriodico
```

> ⚠️ El archivo **`tokengenerarflipbook.txt` NO viene en GitHub** (es secreto, está
> excluido a propósito). Tienes que **crearlo tú** en esa misma carpeta — ver PASO 3.

---

## PASO 2 — Instalar requisitos (una sola vez en ese PC)

### 2.1 Python
- Descarga Python 3.11+ desde https://www.python.org/downloads/
- **IMPORTANTE:** al instalar marca **"Add Python to PATH"**.

### 2.2 Poppler (necesario para leer PDFs)
- Descarga el ZIP más reciente de https://github.com/oschwartz10612/poppler-windows/releases
- Extrae en `C:\Program Files\poppler-XX.XX.X\`
  (la app busca Poppler automáticamente en rutas habituales de `C:\Program Files`).

---

## PASO 3 — Poner el token (secreto) en la carpeta

El programa publica en internet usando un **token de GitHub**. Sin él, genera el
periódico en local pero no lo sube.

1. En la carpeta del proyecto (`C:\GeneradorPeriodico\`), crea un archivo de texto
   llamado exactamente **`tokengenerarflipbook.txt`**.
2. Pega dentro **solo el token** (una línea, sin espacios ni saltos).
   - El token empieza por `github_pat_...` (fine-grained) y tiene permisos
     **Contents: Read and write** y **Pages: Read and write** sobre el repo
     `generador_flipbook`.
   - Si no lo tienes, créalo en GitHub → Settings → Developer settings →
     Personal access tokens → Fine-grained tokens.
3. Guarda el archivo.

---

## PASO 4 — Crear el .EXE

1. Abre la carpeta del proyecto en el Explorador.
2. **Doble clic en `build.bat`**.
   - Instala dependencias, construye el `.exe` y copia el token a `dist\`.
   - Tarda 1-2 minutos. Al final dirá `EXITO!`.
3. El resultado está en:
   ```
   C:\GeneradorPeriodico\dist\GeneradorPeriodico.exe
   C:\GeneradorPeriodico\dist\tokengenerarflipbook.txt
   ```

> El `.exe` ya lleva dentro `github_pages.py` (no hace falta repartirlo aparte).
> Pero el **token** sí debe ir SIEMPRE en la misma carpeta que el `.exe`.

---

## PASO 5 — Entregar a Pilar

Copia a su equipo la **carpeta `dist\` completa** (o crea una carpeta con los dos
archivos juntos):

```
GeneradorPeriodico\
├── GeneradorPeriodico.exe
└── tokengenerarflipbook.txt   ← imprescindible para publicar
```

Pilar solo tiene que **hacer doble clic en `GeneradorPeriodico.exe`**.
Cómo lo usa ella en el día a día: ver **`GUIA_PILAR.md`**.

---

## Resumen rápido

| Paso | Qué haces |
|------|-----------|
| 1 | Descargas el proyecto de GitHub (Code → Download ZIP) |
| 2 | Instalas Python (+PATH) y Poppler |
| 3 | Creas `tokengenerarflipbook.txt` con el token dentro |
| 4 | Doble clic en `build.bat` → se crea `dist\GeneradorPeriodico.exe` |
| 5 | Entregas a Pilar la carpeta `dist\` (exe + token) |

## Problemas comunes

- **"Python no esta instalado"** → instálalo y marca *Add to PATH*; reinicia el CMD.
- **Falla al leer el PDF** → Poppler no está instalado o no en `C:\Program Files`.
- **Genera pero no publica el enlace** → falta `tokengenerarflipbook.txt` junto al
  `.exe`, o el token caducó/no tiene permisos Contents+Pages.
- **`build.bat` dice que falta `github_pages.py`** → descargaste solo un archivo;
  baja el proyecto completo (ZIP).
