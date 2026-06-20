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

echo Instalando dependencias (pdf2image, pillow, pyinstaller)...
pip install --quiet pdf2image pillow pyinstaller

echo Construyendo el .exe (esto tarda 1-2 minutos)...
pyinstaller --onefile --windowed --name "GeneradorPeriodico" --clean crear_flipbook.py

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

if exist build rmdir /s /q build
if exist GeneradorPeriodico.spec del GeneradorPeriodico.spec

echo.
echo ============================================
echo  EXITO!
echo  El .exe esta en: dist\GeneradorPeriodico.exe
echo  Reparte la carpeta dist\ completa
echo  (GeneradorPeriodico.exe + tokengenerarflipbook.txt).
echo ============================================
pause
