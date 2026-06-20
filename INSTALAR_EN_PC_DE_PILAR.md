# 🟢 Instalar en el PC de Pilar (todo en un solo ordenador)

Caso real: **el único Windows es el de Pilar**. Así que ahí haces TODO:
instalas lo necesario, creas el programa (`.exe`) y ahí mismo se queda para que
ella lo use. No hay que pasar nada a otro equipo.

> Los pasos 1 y 2 (Python y Poppler) son **solo para construir** el programa,
> una sola vez. Después, Pilar solo abre el `.exe`.
>
> **Para la pestaña "Preparar PDF"** (convertir Word a PDF): el PC necesita tener
> **Microsoft Word o LibreOffice** instalado. El de Pilar normalmente ya tiene
> uno de los dos; si no, instala LibreOffice gratis desde https://es.libreoffice.org.
> (Esto NO va dentro del `.exe`; los PDF que ya sean PDF se unen sin necesidad de
> Word/LibreOffice.)

Tardarás unos 20 minutos la primera vez. Sigue el orden.

---

## 1) Instalar Python

1. Entra en **https://www.python.org/downloads/**
2. Pulsa el botón amarillo **«Download Python 3.x»**.
3. Abre el archivo descargado.
4. 🔴 **MUY IMPORTANTE:** abajo del todo marca **«Add Python to PATH»**.
5. Pulsa **«Install Now»**, espera a *Setup was successful* y cierra.

---

## 2) Instalar Poppler

1. Entra en **https://github.com/oschwartz10612/poppler-windows/releases**
2. En la versión de arriba, descarga el archivo **`Release-XX.XX.X-X.zip`**.
3. En Descargas: clic derecho al ZIP → **«Extraer todo…»** → **Extraer**.
4. Entra en la carpeta extraída; dentro hay una carpeta tipo `poppler-XX.XX.X`.
5. Renómbrala a **`poppler`** y muévela a `C:\`.
   Tiene que quedar exactamente:
   **`C:\poppler\Library\bin\pdftoppm.exe`**

---

## 3) Descargar el programa

1. Entra en **https://github.com/dtabuyodesigner/generador_flipbook**
2. Botón verde **`<> Code`** → **Download ZIP**.
3. Clic derecho al ZIP → **«Extraer todo…»** → **Extraer**.
4. Renombra la carpeta a **`GeneradorPeriodico`** y muévela a `C:\`.
   Debe quedar: **`C:\GeneradorPeriodico`**

---

## 4) Poner la contraseña secreta (token)

1. Entra en **`C:\GeneradorPeriodico`**.
2. Clic derecho en zona vacía → **Nuevo → Documento de texto**.
3. Renómbralo exactamente a **`tokengenerarflipbook.txt`**
   (si avisa de la extensión, di que **sí**).
4. Ábrelo, **pega solo el token** (empieza por `github_pat_...`), guarda y cierra.

> El token está guardado en tu Zorin, en el archivo
> `tokengenerarflipbook.txt` del proyecto. Cópialo de ahí a un USB o email
> para tenerlo en el PC de Pilar.

---

## 5) Crear el programa (.exe)

1. En **`C:\GeneradorPeriodico`**, doble clic en **`build.bat`**.
2. Se abre una ventana negra que trabaja sola. **No la cierres** (1-2 min).
3. Cuando ponga **`EXITO!`**, ya está. Pulsa una tecla para cerrar.

El programa terminado queda en:
**`C:\GeneradorPeriodico\dist\GeneradorPeriodico.exe`** (con su token al lado).

---

## 6) Dejarlo listo para Pilar

1. Entra en **`C:\GeneradorPeriodico\dist`**.
2. Copia los **dos** archivos juntos al **Escritorio** de Pilar:
   - `GeneradorPeriodico.exe`
   - `tokengenerarflipbook.txt`
3. Pilar abre el programa con **doble clic en `GeneradorPeriodico.exe`**.

Uso diario de Pilar: archivo **`GUIA_PILAR.md`**.

---

## ❓ Si algo falla

- **"Python no esta instalado"** → repite el paso 1 y marca **«Add Python to
  PATH»**. Reinicia el PC y prueba otra vez.
- **"falta github_pages.py"** → bajaste mal; repite el paso 3 (ZIP completo).
- **"no encontre Poppler"** → revisa el paso 2: debe existir
  `C:\poppler\Library\bin\pdftoppm.exe`.
- **Abre pero no da enlace** → falta `tokengenerarflipbook.txt` junto al `.exe`,
  o el token caducó. Repite el paso 4.
