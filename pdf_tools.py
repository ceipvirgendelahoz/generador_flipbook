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
