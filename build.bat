@echo off
echo ============================================
echo  Construyendo Generador de Periodicos...
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado.
    echo Instalalo desde https://www.python.org/downloads/ y marca "Add Python to PATH".
    pause
    exit /b 1
)

if not exist crear_flipbook.py (
    echo ERROR: no encuentro crear_flipbook.py en esta carpeta.
    pause
    exit /b 1
)

if not exist github_pages.py (
    echo ERROR: falta github_pages.py en esta carpeta.
    echo Descarga el proyecto COMPLETO desde GitHub, no solo crear_flipbook.py.
    pause
    exit /b 1
)

rem --- Detectar Poppler para empaquetarlo DENTRO del .exe ---
rem Asi el equipo de Pilar no necesita instalar nada (solo el .exe + el token).
set "POPPLER_BIN="
if exist "C:\poppler\Library\bin\pdftoppm.exe" set "POPPLER_BIN=C:\poppler\Library\bin"
if not defined POPPLER_BIN if exist "C:\poppler\bin\pdftoppm.exe" set "POPPLER_BIN=C:\poppler\bin"
if not defined POPPLER_BIN if exist "C:\Program Files\poppler\Library\bin\pdftoppm.exe" set "POPPLER_BIN=C:\Program Files\poppler\Library\bin"

if not defined POPPLER_BIN (
    echo AVISO: no encontre Poppler en C:\poppler.
    echo El .exe se creara SIN Poppler dentro, y el equipo de Pilar necesitaria
    echo instalar Poppler aparte. Para empaquetarlo, instala Poppler en C:\poppler
    echo - mira INSTRUCCIONES_WINDOWS.md - y vuelve a ejecutar este build.
    echo.
    pause
)

echo Instalando dependencias: pdf2image, pillow, pyinstaller, pypdf, pywin32...
pip install --quiet pdf2image pillow pyinstaller pypdf pywin32

set "ICON_ARG="
if exist icono.ico set "ICON_ARG=--icon=icono.ico"

echo Construyendo el .exe, esto tarda 1-2 minutos...
if defined POPPLER_BIN (
    echo Empaquetando Poppler desde: %POPPLER_BIN%
    pyinstaller --onefile --windowed --name "GeneradorPeriodico" --clean %ICON_ARG% --add-data "%POPPLER_BIN%;poppler/bin" crear_flipbook.py
) else (
    pyinstaller --onefile --windowed --name "GeneradorPeriodico" --clean %ICON_ARG% crear_flipbook.py
)

if errorlevel 1 (
    echo.
    echo ERROR: fallo la construccion del .exe.
    pause
    exit /b 1
)

rem El token es necesario para publicar en internet; va JUNTO al .exe.
if exist tokengenerarflipbook.txt (
    copy /Y tokengenerarflipbook.txt dist\tokengenerarflipbook.txt >nul
    echo Token copiado a dist\tokengenerarflipbook.txt
) else (
    echo AVISO: no encontre tokengenerarflipbook.txt.
    echo Debes copiarlo a la carpeta dist\ junto al .exe antes de usarlo.
)

rem Opcional: repositorio.txt (owner/repo) para publicar en otra cuenta/organizacion
rem sin recompilar. Si no existe, se usa el repo por defecto.
if exist repositorio.txt (
    copy /Y repositorio.txt dist\repositorio.txt >nul
    echo repositorio.txt copiado a dist\
)

if exist build rmdir /s /q build
if exist GeneradorPeriodico.spec del GeneradorPeriodico.spec

echo.
echo ============================================
echo  EXITO!
echo  El .exe esta en: dist\GeneradorPeriodico.exe
if defined POPPLER_BIN echo  Poppler va dentro del .exe, Pilar no instala nada.
echo  Reparte la carpeta dist\ completa:
echo  GeneradorPeriodico.exe + tokengenerarflipbook.txt
echo ============================================
pause
