#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creador de Flipbooks desde PDF - v4 FINAL
Fixes:
- Navegación al final y vuelta atrás
- Pantalla completa funciona en cualquier momento
- Guarda HTML original para restaurar tras destroy
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import json
import base64
import shutil
import platform
import zipfile
import tempfile
import subprocess
import time
import threading
import webbrowser
import urllib.request
import urllib.error
from datetime import datetime

import github_pages
import pdf_tools

# Configuración local (URL/usuario WordPress y, opcionalmente, la password)
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".flipbook_config.json")

try:
    from pdf2image import convert_from_path
    from PIL import Image
except ImportError:
    print("Falta instalar: pip install pdf2image pillow")
    exit(1)

# ImageTk es opcional: solo se usa para la vista previa dentro de la app.
# En Linux puede faltar (paquete python3-pil.imagetk); en el .exe de Windows
# Pillow ya lo incluye. Si falta, la app funciona igual pero sin vista previa.
try:
    from PIL import ImageTk
    HAS_IMAGETK = True
except ImportError:
    ImageTk = None
    HAS_IMAGETK = False


def generar_html(titulo, num_pages, descripcion=""):
    """Genera el HTML del flipbook con StPageFlip y fixes de navegación.

    `descripcion` es texto opcional que se muestra como subtítulo en la
    cabecera de la página publicada (lo que ven las familias). Si está vacío
    se usa el subtítulo genérico."""
    
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__TITULO__</title>
    <script src="https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 20px;
            overflow-x: hidden;
        }
        
        .header {
            color: white;
            text-align: center;
            margin-bottom: 20px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        .header h1 {
            font-size: 2em;
            text-transform: uppercase;
            letter-spacing: 3px;
            margin-bottom: 5px;
        }
        
        .header p {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        #flipbook-container {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        #flipbook {
            box-shadow: 0 30px 80px rgba(0,0,0,0.5);
        }
        
        .page {
            background: white;
            overflow: hidden;
            position: relative;
        }
        
        .page-cover {
            background: white;
            box-shadow: inset -10px 0 30px -10px rgba(0,0,0,0.4);
        }
        
        .page-cover-back {
            background: white;
            box-shadow: inset 10px 0 30px -10px rgba(0,0,0,0.4);
        }
        
        .page img {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: contain;
            background: white;
        }
        
        .page-number {
            position: absolute;
            bottom: 12px;
            background: rgba(102, 126, 234, 0.85);
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.75em;
            font-weight: bold;
            font-family: 'Segoe UI', Tahoma, sans-serif;
            letter-spacing: 1px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            pointer-events: none;
            z-index: 10;
        }
        
        /* Páginas izquierdas: número en esquina inferior IZQUIERDA (exterior) */
        .page-left-side .page-number {
            left: 12px;
        }
        
        /* Páginas derechas: número en esquina inferior DERECHA (exterior) */
        .page-right-side .page-number {
            right: 12px;
        }
        
        .controls {
            display: flex;
            gap: 15px;
            margin-top: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        button {
            background: rgba(255, 255, 255, 0.95);
            color: #333;
            border: none;
            padding: 12px 24px;
            border-radius: 30px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .fullscreen-btn {
            background: #ff6b6b;
            color: white;
        }
        
        .reset-btn {
            background: #4caf50;
            color: white;
        }
        
        .page-info {
            background: rgba(255, 255, 255, 0.95);
            padding: 12px 24px;
            border-radius: 30px;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            min-width: 130px;
            text-align: center;
        }
        
        /* Modo fullscreen */
        body.fs-mode {
            padding: 10px;
            justify-content: space-between;
        }
        
        body.fs-mode .header {
            display: none;
        }
        
        body.fs-mode #flipbook-container {
            flex: 1;
        }
        
        body.fs-mode .controls {
            margin-top: 10px;
            margin-bottom: 10px;
        }
        
        @media (max-width: 768px) {
            .header h1 { font-size: 1.3em; }
            button { padding: 10px 18px; font-size: 0.9em; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>__TITULO__</h1>
        <p>__SUBTITULO__</p>
    </div>
    
    <div id="flipbook-container">
        <div id="flipbook"></div>
    </div>
    
    <div class="controls">
        <button id="prev-btn">← Anterior</button>
        <div class="page-info">
            <span id="current-page">1</span> / <span id="total-pages">__NUM_PAGES__</span>
        </div>
        <button id="next-btn">Siguiente →</button>
        <button class="fullscreen-btn" id="fullscreen-btn">⛶ Pantalla Completa</button>
        <button class="reset-btn" id="reset-btn">↺ Reiniciar</button>
    </div>
    
    <script>
        const totalPages = __NUM_PAGES__;
        let pageFlip = null;
        let currentPageIndex = 0;
        
        function calcSize() {
            const isMobile = window.innerWidth < 768;
            const isFs = document.body.classList.contains('fs-mode');
            
            let availW, availH;
            if (isFs) {
                availW = window.innerWidth - 30;
                availH = window.innerHeight - 120;
            } else {
                availW = Math.min(window.innerWidth - 60, 1100);
                availH = window.innerHeight - 280;
            }
            
            let width, height;
            const aspectRatio = 1.414;
            
            if (isMobile) {
                width = Math.min(availW, 400);
                height = width * aspectRatio;
                if (height > availH) {
                    height = availH;
                    width = height / aspectRatio;
                }
            } else {
                width = Math.min(availW / 2, 500);
                height = width * aspectRatio;
                if (height > availH) {
                    height = availH;
                    width = height / aspectRatio;
                }
            }
            
            return { 
                width: Math.floor(width), 
                height: Math.floor(height), 
                isMobile: isMobile 
            };
        }
        
        function buildPagesHTML() {
            // IMPORTANTE: recrear el div#flipbook desde cero
            // porque StPageFlip.destroy() puede haberlo eliminado/modificado
            const container = document.getElementById('flipbook-container');
            container.innerHTML = '<div id="flipbook"></div>';
            
            const fb = document.getElementById('flipbook');
            for (let i = 1; i <= totalPages; i++) {
                const div = document.createElement('div');
                div.className = 'page';
                
                // Marcar la primera como portada (sin número)
                if (i === 1) {
                    div.className = 'page page-cover';
                }
                // Marcar la última como contraportada
                if (i === totalPages) {
                    div.className = 'page page-cover-back';
                }
                
                const img = document.createElement('img');
                img.src = 'pages/page_' + String(i).padStart(3, '0') + '.png';
                img.alt = 'Página ' + i;
                div.appendChild(img);
                
                // Número de página (excepto en portada y contraportada)
                if (i !== 1 && i !== totalPages) {
                    // Páginas pares (2, 4, 6...) van a la IZQUIERDA del libro
                    // Páginas impares (3, 5, 7...) van a la DERECHA del libro
                    if (i % 2 === 0) {
                        div.classList.add('page-left-side');
                    } else {
                        div.classList.add('page-right-side');
                    }
                    
                    const num = document.createElement('div');
                    num.className = 'page-number';
                    num.textContent = i - 1;
                    div.appendChild(num);
                }
                
                fb.appendChild(div);
            }
        }
        
        function initFlipbook(goToPage) {
            const size = calcSize();
            
            // Reconstruir el HTML original de las páginas
            buildPagesHTML();
            
            pageFlip = new St.PageFlip(document.getElementById('flipbook'), {
                width: size.width,
                height: size.height,
                size: 'fixed',
                drawShadow: true,
                flippingTime: 700,
                usePortrait: size.isMobile,
                showCover: true,
                mobileScrollSupport: false,
                maxShadowOpacity: 0.5,
                useMouseEvents: true,
                swipeDistance: 30
            });
            
            pageFlip.loadFromHTML(document.querySelectorAll('.page'));
            
            pageFlip.on('flip', function(e) {
                const idx = e.data;
                currentPageIndex = idx;
                document.getElementById('current-page').textContent = idx + 1;
                document.getElementById('prev-btn').disabled = idx === 0;
                document.getElementById('next-btn').disabled = idx >= totalPages - 1;
            });
            
            // Ir a la página guardada si se especifica
            if (goToPage && goToPage > 0) {
                setTimeout(function() {
                    if (pageFlip) {
                        pageFlip.flip(goToPage, 'top');
                    }
                }, 150);
            } else {
                // Inicializar estado botones
                document.getElementById('prev-btn').disabled = true;
                document.getElementById('next-btn').disabled = totalPages <= 1;
            }
        }
        
        function reinitFlipbook(keepPage) {
            const savedPage = keepPage ? currentPageIndex : 0;
            
            if (pageFlip) {
                try {
                    pageFlip.destroy();
                } catch (e) {
                    console.log('Error al destruir:', e);
                }
                pageFlip = null;
            }
            
            // Pequeña espera para que el DOM se limpie
            setTimeout(function() {
                initFlipbook(savedPage);
            }, 50);
        }
        
        // Botón anterior
        document.getElementById('prev-btn').addEventListener('click', function() {
            if (pageFlip) pageFlip.flipPrev();
        });
        
        // Botón siguiente
        document.getElementById('next-btn').addEventListener('click', function() {
            if (pageFlip) pageFlip.flipNext();
        });
        
        // Botón reiniciar (vuelve al principio sin recrear)
        document.getElementById('reset-btn').addEventListener('click', function() {
            reinitFlipbook(false);
        });
        
        // Botón pantalla completa
        document.getElementById('fullscreen-btn').addEventListener('click', async function() {
            const isFs = document.body.classList.contains('fs-mode');
            
            if (!isFs) {
                // Entrar fullscreen
                try {
                    if (document.documentElement.requestFullscreen) {
                        await document.documentElement.requestFullscreen();
                    } else if (document.documentElement.webkitRequestFullscreen) {
                        await document.documentElement.webkitRequestFullscreen();
                    }
                } catch (e) {
                    console.log('Sin API fullscreen, modo CSS solo');
                }
                document.body.classList.add('fs-mode');
                setTimeout(function() { reinitFlipbook(true); }, 200);
            } else {
                // Salir fullscreen
                try {
                    if (document.exitFullscreen) {
                        await document.exitFullscreen();
                    } else if (document.webkitExitFullscreen) {
                        await document.webkitExitFullscreen();
                    }
                } catch (e) {}
                document.body.classList.remove('fs-mode');
                setTimeout(function() { reinitFlipbook(true); }, 200);
            }
        });
        
        // Detectar salida de fullscreen por ESC
        document.addEventListener('fullscreenchange', function() {
            if (!document.fullscreenElement && document.body.classList.contains('fs-mode')) {
                document.body.classList.remove('fs-mode');
                setTimeout(function() { reinitFlipbook(true); }, 200);
            }
        });
        
        // Teclado
        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowRight' && pageFlip) pageFlip.flipNext();
            if (e.key === 'ArrowLeft' && pageFlip) pageFlip.flipPrev();
        });
        
        // Resize con debounce
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() { reinitFlipbook(true); }, 400);
        });
        
        // Inicializar
        window.addEventListener('load', function() {
            initFlipbook(0);
        });
    </script>
</body>
</html>
"""
    
    # Subtítulo: la descripción del usuario (escapada) o el texto genérico
    desc = (descripcion or "").strip()
    if desc:
        subtitulo = (desc.replace("&", "&amp;").replace("<", "&lt;")
                        .replace(">", "&gt;").replace("\n", "<br>"))
    else:
        subtitulo = "📰 Periódico Digital Interactivo"

    # Reemplazar placeholders
    html = html.replace("__TITULO__", titulo)
    html = html.replace("__SUBTITULO__", subtitulo)
    html = html.replace("__NUM_PAGES__", str(num_pages))

    return html


# ---------------------------------------------------------------------------
# Detección de poppler (compatibilidad Windows / Linux / Mac)
# ---------------------------------------------------------------------------
def detectar_poppler():
    """Devuelve la ruta a los binarios de poppler en Windows, o None para
    Linux/Mac (donde se usa el PATH del sistema). En Windows busca poppler
    en ubicaciones habituales o en una carpeta 'poppler/bin' junto al script."""
    if platform.system() != "Windows":
        return None  # Linux/Mac: pdf2image usa pdftoppm del PATH

    # Ejecutable PyInstaller: poppler viaja empaquetado dentro del .exe
    if getattr(sys, "frozen", False):
        empaquetado = os.path.join(getattr(sys, "_MEIPASS", ""), "poppler", "bin")
        if os.path.isdir(empaquetado) and os.path.exists(os.path.join(empaquetado, "pdftoppm.exe")):
            return empaquetado
        # Si no estuviera empaquetado, buscar junto al .exe
        aqui = os.path.dirname(sys.executable)
    else:
        aqui = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(aqui, "poppler", "bin"),
        os.path.join(aqui, "poppler", "Library", "bin"),
        r"C:\poppler\bin",
        r"C:\poppler\Library\bin",
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files\poppler\Library\bin",
    ]
    for ruta in candidatos:
        if os.path.isdir(ruta) and os.path.exists(os.path.join(ruta, "pdftoppm.exe")):
            return ruta
    return None  # confiar en que esté en el PATH


# ---------------------------------------------------------------------------
# Configuración local (~/.flipbook_config.json)
# ---------------------------------------------------------------------------
def cargar_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _ofuscar(texto):
    """Codificación base64 simple (NO es cifrado; solo evita lectura casual)."""
    return base64.b64encode(texto.encode("utf-8")).decode("ascii")


def _desofuscar(texto):
    try:
        return base64.b64decode(texto.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Subida a WordPress vía REST API (sin dependencias externas, usa urllib)
# ---------------------------------------------------------------------------
def _wp_auth_header(usuario, app_password):
    token = base64.b64encode(f"{usuario}:{app_password}".encode("utf-8")).decode("ascii")
    return "Basic " + token


def _wp_error_legible(err):
    """Extrae un mensaje legible de un urllib.error.HTTPError de WordPress."""
    try:
        cuerpo = err.read().decode("utf-8", "replace")
        datos = json.loads(cuerpo)
        msg = datos.get("message") or cuerpo
        return f"{err.code}: {msg}"
    except Exception:
        return f"{getattr(err, 'code', '?')}: {err}"


def wp_subir_media(base_url, usuario, app_password, filepath, mime):
    """Sube un archivo a la mediateca (POST /wp-json/wp/v2/media).
    Envía el archivo como cuerpo crudo con Content-Disposition (no multipart).
    Devuelve el JSON de respuesta (incluye 'id' y 'source_url')."""
    url = base_url.rstrip("/") + "/wp-json/wp/v2/media"
    with open(filepath, "rb") as f:
        data = f.read()
    filename = os.path.basename(filepath)
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", _wp_auth_header(usuario, app_password))
    req.add_header("Content-Type", mime)
    req.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wp_crear_post(base_url, usuario, app_password, titulo, contenido, status="publish"):
    """Crea un post (POST /wp-json/wp/v2/posts). Devuelve el JSON de respuesta
    (incluye 'link' con la URL pública del post)."""
    url = base_url.rstrip("/") + "/wp-json/wp/v2/posts"
    payload = json.dumps({
        "title": titulo,
        "content": contenido,
        "status": status,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", _wp_auth_header(usuario, app_password))
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generar_html_embed(titulo, image_urls):
    """Genera un HTML autocontenido del flipbook usando URLs absolutas de las
    imágenes (las subidas a la mediateca). Se incrusta en el post mediante un
    <iframe srcdoc>. Misma librería StPageFlip que el flipbook principal."""
    urls_js = "[" + ",".join("'" + u.replace("'", "\\'") + "'" for u in image_urls) + "]"
    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITULO__</title>
<script src="https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 15px;
}
#flipbook-container { display: flex; justify-content: center; align-items: center; }
#flipbook { box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
.page { background: #fff; overflow: hidden; }
.page img { width: 100%; height: 100%; display: block; object-fit: contain; background: #fff; }
.controls { display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; justify-content: center; }
button {
    background: rgba(255,255,255,0.95); color: #333; border: none;
    padding: 10px 20px; border-radius: 30px; cursor: pointer;
    font-size: 0.95em; font-weight: 600; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
button:disabled { opacity: 0.5; cursor: not-allowed; }
.page-info {
    background: rgba(255,255,255,0.95); padding: 10px 20px; border-radius: 30px;
    font-weight: bold; min-width: 110px; text-align: center;
}
</style>
</head>
<body>
<div id="flipbook-container"><div id="flipbook"></div></div>
<div class="controls">
    <button id="prev-btn">&larr; Anterior</button>
    <div class="page-info"><span id="current-page">1</span> / <span id="total-pages">__NUM_PAGES__</span></div>
    <button id="next-btn">Siguiente &rarr;</button>
</div>
<script>
const pageUrls = __URLS__;
const totalPages = pageUrls.length;
let pageFlip = null;

function calcSize() {
    const availW = Math.min(window.innerWidth - 40, 1000);
    const availH = window.innerHeight - 120;
    const aspectRatio = 1.414;
    let width = Math.min(availW / 2, 460);
    let height = width * aspectRatio;
    if (height > availH) { height = availH; width = height / aspectRatio; }
    return { width: Math.floor(width), height: Math.floor(height) };
}

function buildPages() {
    const fb = document.getElementById('flipbook');
    fb.innerHTML = '';
    for (let i = 0; i < totalPages; i++) {
        const div = document.createElement('div');
        div.className = 'page';
        const img = document.createElement('img');
        img.src = pageUrls[i];
        img.alt = 'Pagina ' + (i + 1);
        div.appendChild(img);
        fb.appendChild(div);
    }
}

function initFlipbook() {
    const size = calcSize();
    buildPages();
    pageFlip = new St.PageFlip(document.getElementById('flipbook'), {
        width: size.width, height: size.height, size: 'fixed',
        drawShadow: true, flippingTime: 700, showCover: true,
        maxShadowOpacity: 0.5, useMouseEvents: true, swipeDistance: 30
    });
    pageFlip.loadFromHTML(document.querySelectorAll('.page'));
    pageFlip.on('flip', function(e) {
        const idx = e.data;
        document.getElementById('current-page').textContent = idx + 1;
        document.getElementById('prev-btn').disabled = idx === 0;
        document.getElementById('next-btn').disabled = idx >= totalPages - 1;
    });
    document.getElementById('prev-btn').disabled = true;
    document.getElementById('next-btn').disabled = totalPages <= 1;
}

document.getElementById('prev-btn').addEventListener('click', function() { if (pageFlip) pageFlip.flipPrev(); });
document.getElementById('next-btn').addEventListener('click', function() { if (pageFlip) pageFlip.flipNext(); });
document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowRight' && pageFlip) pageFlip.flipNext();
    if (e.key === 'ArrowLeft' && pageFlip) pageFlip.flipPrev();
});
let resizeTimer;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() { if (pageFlip) { try { pageFlip.destroy(); } catch (e) {} } initFlipbook(); }, 400);
});
window.addEventListener('load', initFlipbook);
</script>
</body>
</html>
"""
    html = html.replace("__TITULO__", titulo)
    html = html.replace("__NUM_PAGES__", str(len(image_urls)))
    html = html.replace("__URLS__", urls_js)
    return html


# ---------------------------------------------------------------------------
# Publicación en GitHub Pages vía Git Data API (urllib, sin dependencias extra)
def generar_preview_post_html(titulo, contenido, flipbook_src="index.html"):
    """Página local que SIMULA cómo quedará el post de WordPress: título +
    contenido + flipbook embebido (iframe al flipbook local) + botón de
    descarga. Es solo para revisar antes de publicar; no sube nada."""
    t = (titulo or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    bloque_contenido = ""
    if contenido:
        c = (contenido.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                      .replace("\n", "<br>\n"))
        bloque_contenido = f'<p class="post-content">{c}</p>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vista previa: {t}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Segoe UI', Tahoma, sans-serif; background: #eef0f5; color: #222; }}
.preview-banner {{ background: #ffc107; color: #5a4500; text-align: center; padding: 10px; font-weight: bold; letter-spacing: .5px; }}
.post {{ max-width: 900px; margin: 24px auto; background: #fff; border-radius: 14px; box-shadow: 0 10px 40px rgba(0,0,0,.12); padding: 36px; }}
.post h1 {{ font-size: 2em; margin: 0 0 18px; color: #1a1a1a; }}
.post-content {{ font-size: 1.05em; line-height: 1.6; color: #444; margin-bottom: 24px; }}
.flip-wrap iframe {{ width: 100%; height: 82vh; min-height: 480px; max-height: 920px; border: 0; border-radius: 10px; background: #667eea; }}
.descarga {{ text-align: center; margin-top: 22px; }}
.descarga a {{ display: inline-block; background: #667eea; color: #fff; padding: 12px 28px; border-radius: 30px; text-decoration: none; font-weight: bold; opacity: .6; }}
.nota {{ text-align: center; color: #999; font-size: .85em; margin-top: 8px; }}
</style>
</head>
<body>
<div class="preview-banner">👁 VISTA PREVIA — así se verá el post publicado (todavía NO publicado)</div>
<div class="post">
    <h1>{t}</h1>
    {bloque_contenido}
    <div class="flip-wrap"><iframe src="{flipbook_src}" allowfullscreen></iframe></div>
    <div class="descarga"><a href="#" onclick="return false;">⬇ Descargar flipbook (ZIP)</a></div>
    <div class="nota">El botón de descarga se activará al publicar en WordPress.</div>
</div>
</body>
</html>
"""


class CreadorFlipbook:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador de Periódicos Digitales")
        self.root.geometry("1180x668")
        self.root.minsize(960, 560)

        self.pdf_path = tk.StringVar()
        self.output_folder = None
        self.flipbook_html = None
        self.instrucciones_html = None
        self.zip_path = None
        self.post_url = None

        # Estado de la vista previa de páginas
        self.preview_images = []     # páginas como PIL.Image
        self.preview_photo = None    # referencia viva del PhotoImage (evita GC)
        self.preview_index = 0
        self.preview_temp_dir = None # carpeta temporal del flipbook de vista previa

        style = ttk.Style()
        style.theme_use('clam')

        cfg = cargar_config()

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

        # Limpiar la vista previa temporal al cerrar la ventana
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _construir_tab_flipbook(self, parent):
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # ===================== COLUMNA IZQUIERDA: formulario =====================
        left = ttk.Frame(parent, padding="12")
        left.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        left.columnconfigure(0, weight=1)

        title = ttk.Label(left, text="📰 Generador de Periódicos Digitales",
                         font=("Arial", 13, "bold"))
        title.grid(row=0, column=0, pady=(0, 5), sticky=(tk.W, tk.E))

        # --- Sección 1: PDF y carpeta ---------------------------------------
        sec_pdf = ttk.LabelFrame(left, text="1. Flipbook", padding="8")
        sec_pdf.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=3)
        sec_pdf.columnconfigure(0, weight=1)

        ttk.Label(sec_pdf, text="Selecciona el PDF:").grid(row=0, column=0, sticky=tk.W)
        pdf_frame = ttk.Frame(sec_pdf)
        pdf_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(2, 8))
        ttk.Entry(pdf_frame, textvariable=self.pdf_path, state="readonly", width=30).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(pdf_frame, text="Examinar...", command=self.seleccionar_pdf).pack(side=tk.LEFT)

        ttk.Label(sec_pdf, text="Nombre de la carpeta:").grid(row=2, column=0, sticky=tk.W)
        self.nombre_output = ttk.Entry(sec_pdf, width=44)
        self.nombre_output.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=2)
        self.nombre_output.insert(0, f"periodico_{datetime.now().strftime('%d_%m_%Y').lower()}")

        self.slug_label = ttk.Label(sec_pdf, text="", foreground="gray")
        self.slug_label.grid(row=4, column=0, sticky=tk.W, pady=(0, 2))
        self.nombre_output.bind("<KeyRelease>", self._actualizar_slug_label)
        self._actualizar_slug_label()

        # --- Sección 2: Título y descripción del periódico ----------------------
        sec_post = ttk.LabelFrame(left, text="2. Título y descripción del periódico", padding="8")
        sec_post.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=3)
        sec_post.columnconfigure(0, weight=1)

        ttk.Label(sec_post, text="Título (aparece en la cabecera de la página):").grid(row=0, column=0, sticky=tk.W)
        self.post_titulo = ttk.Entry(sec_post, width=44)
        self.post_titulo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(2, 6))

        ttk.Label(sec_post, text="Descripción (opcional, se muestra bajo el título):").grid(row=2, column=0, sticky=tk.W)
        self.post_contenido = tk.Text(sec_post, height=3, width=44, wrap=tk.WORD,
                                      font=("Segoe UI", 10), relief="solid", borderwidth=1)
        self.post_contenido.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(2, 2))

        # --- Acción y estado ------------------------------------------------
        self.btn_generar = ttk.Button(left, text="🔗 Generar enlace para la web", command=self.generar_flipbook)
        self.btn_generar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(6, 3))

        self.progress = ttk.Progressbar(left, mode='indeterminate')
        self.progress.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=2)

        self.status_label = ttk.Label(left, text="Listo para empezar", foreground="blue")
        self.status_label.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=2)

        # Enlace público (se rellena tras publicar en GitHub Pages)
        url_frame = ttk.Frame(left)
        url_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(2, 0))
        url_frame.columnconfigure(0, weight=1)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, state="readonly")
        self.url_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 4))
        self.btn_copiar = ttk.Button(url_frame, text="📋 Copiar enlace",
                                     command=self._copiar_enlace, state=tk.DISABLED)
        self.btn_copiar.grid(row=0, column=1)

        button_frame = ttk.Frame(left)
        button_frame.grid(row=8, column=0, pady=(2, 0))

        self.btn_abrir = ttk.Button(button_frame, text="📂 Abrir Flipbook", command=self.abrir_flipbook, state=tk.DISABLED)
        self.btn_abrir.pack(side=tk.LEFT, padx=4)

        self.btn_carpeta = ttk.Button(button_frame, text="📁 Ver Carpeta", command=self.abrir_carpeta, state=tk.DISABLED)
        self.btn_carpeta.pack(side=tk.LEFT, padx=4)

        self.btn_post = ttk.Button(button_frame, text="🌐 Abrir en navegador", command=self.abrir_post, state=tk.DISABLED)
        self.btn_post.pack(side=tk.LEFT, padx=4)

        self.btn_instrucciones = ttk.Button(button_frame, text="📋 Instrucciones", command=self.abrir_instrucciones, state=tk.DISABLED)
        self.btn_instrucciones.pack(side=tk.LEFT, padx=4)

        # ===================== COLUMNA DERECHA: vista previa =====================
        right = ttk.LabelFrame(parent, text="👁 Vista previa de páginas", padding="10")
        right.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=(0, 12), pady=12)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.btn_preview = ttk.Button(right, text="🔄 Generar vista previa", command=self.generar_preview)
        self.btn_preview.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 8))

        self.preview_canvas = tk.Canvas(right, bg="#2f2f45", highlightthickness=0, width=440, height=560)
        self.preview_canvas.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.preview_canvas.bind("<Configure>", lambda e: self._render_preview())

        nav = ttk.Frame(right)
        nav.grid(row=2, column=0, pady=(8, 0))
        self.btn_pv_prev = ttk.Button(nav, text="◀", width=4, command=self.preview_prev, state=tk.DISABLED)
        self.btn_pv_prev.pack(side=tk.LEFT, padx=4)
        self.preview_label = ttk.Label(nav, text="—", width=14, anchor=tk.CENTER)
        self.preview_label.pack(side=tk.LEFT, padx=6)
        self.btn_pv_next = ttk.Button(nav, text="▶", width=4, command=self.preview_next, state=tk.DISABLED)
        self.btn_pv_next.pack(side=tk.LEFT, padx=4)

        ttk.Label(right, text="El visor pasa página a página dentro de la app. Además, al pulsar\n'Generar vista previa' se abre el flipbook real (con animación) en el\nnavegador, sin publicar nada. Si está bien, pulsa 'Generar y Publicar'.",
                  foreground="gray", justify=tk.CENTER).grid(row=3, column=0, pady=(8, 0))

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

    def generar_preview(self):
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Selecciona un PDF primero")
            return
        if not os.path.exists(self.pdf_path.get()):
            messagebox.showerror("Error", "El PDF no existe")
            return

        # Borrar una vista previa temporal anterior antes de crear la nueva
        self._limpiar_preview_temp()

        self.progress.start()
        self.status_label.config(text="Generando vista previa...", foreground="orange")
        self.btn_preview.config(state=tk.DISABLED)
        self.root.update()
        try:
            nombre = self.nombre_output.get().strip() or "vista_previa"
            tmp = tempfile.mkdtemp(prefix="flipbook_preview_")
            pages_dir = os.path.join(tmp, "pages")
            os.makedirs(pages_dir, exist_ok=True)

            poppler_path = detectar_poppler()
            if poppler_path:
                imgs = convert_from_path(self.pdf_path.get(), dpi=150, poppler_path=poppler_path)
            else:
                imgs = convert_from_path(self.pdf_path.get(), dpi=150)

            # Misma lógica que la generación real: así la vista previa es
            # idéntica al flipbook que se publicará.
            for i, image in enumerate(imgs, 1):
                image.thumbnail((1200, 1600), Image.Resampling.LANCZOS)
                image.save(os.path.join(pages_dir, f"page_{i:03d}.png"), "PNG", optimize=True)

            titulo_post = self.post_titulo.get().strip() or nombre
            contenido_post = self.post_contenido.get("1.0", tk.END).strip()

            html_path = os.path.join(tmp, "index.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(generar_html(titulo_post, len(imgs), contenido_post))

            # Página de vista previa (título + flipbook)
            preview_path = os.path.join(tmp, "preview_post.html")
            with open(preview_path, "w", encoding="utf-8") as f:
                f.write(generar_preview_post_html(titulo_post, contenido_post, "index.html"))

            self.preview_temp_dir = tmp

            # Abrir en el navegador la vista del POST tal cual se publicará
            webbrowser.open(f"file://{preview_path}")

            # Visor interno página a página (si ImageTk está disponible)
            if HAS_IMAGETK:
                self.preview_images = imgs
                self.preview_index = 0
                self._render_preview()
                self.status_label.config(text=f"Vista previa lista: {len(imgs)} páginas. Revísala antes de publicar.", foreground="green")
            else:
                self.status_label.config(text=f"Vista previa abierta en el navegador ({len(imgs)} páginas).", foreground="green")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar la vista previa:\n{e}")
            self.status_label.config(text="❌ Error en vista previa", foreground="red")
        finally:
            self.progress.stop()
            self.btn_preview.config(state=tk.NORMAL)

    def _limpiar_preview_temp(self):
        """Borra la carpeta temporal de la última vista previa, si existe."""
        if self.preview_temp_dir and os.path.isdir(self.preview_temp_dir):
            shutil.rmtree(self.preview_temp_dir, ignore_errors=True)
        self.preview_temp_dir = None

    def _on_close(self):
        self._limpiar_preview_temp()
        self.root.destroy()

    def _render_preview(self):
        if not self.preview_images:
            return
        img = self.preview_images[self.preview_index]
        cw = max(self.preview_canvas.winfo_width(), 50)
        ch = max(self.preview_canvas.winfo_height(), 50)
        iw, ih = img.size
        escala = min(cw / iw, ch / ih)
        nw, nh = max(int(iw * escala), 1), max(int(ih * escala), 1)
        img_red = img.resize((nw, nh), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(img_red)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(cw // 2, ch // 2, image=self.preview_photo)
        self.preview_label.config(text=f"{self.preview_index + 1} / {len(self.preview_images)}")
        self.btn_pv_prev.config(state=(tk.NORMAL if self.preview_index > 0 else tk.DISABLED))
        self.btn_pv_next.config(state=(tk.NORMAL if self.preview_index < len(self.preview_images) - 1 else tk.DISABLED))

    def preview_prev(self):
        if self.preview_images and self.preview_index > 0:
            self.preview_index -= 1
            self._render_preview()

    def preview_next(self):
        if self.preview_images and self.preview_index < len(self.preview_images) - 1:
            self.preview_index += 1
            self._render_preview()

    def seleccionar_pdf(self):
        pdf = filedialog.askopenfilename(
            title="Selecciona el PDF",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]
        )
        if pdf:
            self.pdf_path.set(pdf)
            self.status_label.config(text=f"PDF: {os.path.basename(pdf)}", foreground="green")
    
    def generar_flipbook(self):
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Selecciona un PDF primero")
            return
        
        if not os.path.exists(self.pdf_path.get()):
            messagebox.showerror("Error", "El PDF no existe")
            return
        
        self.progress.start()
        self.status_label.config(text="Procesando...", foreground="orange")
        self.root.update()
        
        try:
            nombre = self.nombre_output.get().strip() or "periodico_digital"
            output_dir = os.path.expanduser(f"~/Descargas/{nombre}")
            output_dir = os.path.abspath(output_dir)
            
            if os.path.exists(output_dir):
                output_dir = f"{output_dir}_{datetime.now().strftime('%H%M%S')}"
            
            os.makedirs(output_dir, exist_ok=True)
            pages_dir = os.path.join(output_dir, "pages")
            os.makedirs(pages_dir, exist_ok=True)
            
            self.status_label.config(text="Extrayendo páginas...", foreground="orange")
            self.root.update()
            
            poppler_path = detectar_poppler()
            if poppler_path:
                images = convert_from_path(self.pdf_path.get(), dpi=150, poppler_path=poppler_path)
            else:
                images = convert_from_path(self.pdf_path.get(), dpi=150)

            page_paths = []
            for i, image in enumerate(images, 1):
                page_path = os.path.join(pages_dir, f"page_{i:03d}.png")
                image.thumbnail((1200, 1600), Image.Resampling.LANCZOS)
                image.save(page_path, "PNG", optimize=True)
                page_paths.append(page_path)
            
            self.status_label.config(text="Creando HTML...", foreground="orange")
            self.root.update()
            
            titulo_pag = self.post_titulo.get().strip() or nombre
            descripcion = self.post_contenido.get("1.0", tk.END).strip()
            html_content = generar_html(titulo_pag, len(images), descripcion)
            html_path = os.path.join(output_dir, "index.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            instr_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Instrucciones - {nombre}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Segoe UI', sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 30px 20px;
    display: flex;
    justify-content: center;
}}
.container {{
    background: white;
    border-radius: 20px;
    padding: 40px;
    max-width: 700px;
    width: 100%;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}}
h1 {{
    color: #667eea;
    text-align: center;
    margin-bottom: 10px;
    font-size: 1.8em;
}}
.subtitle {{
    text-align: center;
    color: #666;
    margin-bottom: 30px;
}}
.step {{
    display: flex;
    gap: 20px;
    margin-bottom: 25px;
    padding: 20px;
    background: #f7f8fc;
    border-radius: 15px;
    border-left: 5px solid #667eea;
}}
.step-number {{
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    width: 45px;
    height: 45px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5em;
    font-weight: bold;
    flex-shrink: 0;
}}
.step-content h3 {{
    color: #333;
    margin-bottom: 8px;
}}
.step-content p {{
    color: #555;
    line-height: 1.5;
}}
.highlight {{
    background: #fff3cd;
    border-left-color: #ffc107;
    margin-top: 30px;
}}
.highlight .step-number {{
    background: linear-gradient(135deg, #ffc107, #ff9800);
}}
code {{
    background: #e8eaf6;
    padding: 2px 8px;
    border-radius: 5px;
    font-family: monospace;
    color: #5c6bc0;
    font-size: 0.9em;
}}
.footer {{
    text-align: center;
    margin-top: 30px;
    color: #999;
    font-size: 0.85em;
}}
</style>
</head>
<body>
<div class="container">
    <h1>📰 ¡Tu periódico está listo y publicado!</h1>
    <p class="subtitle">Solo te quedan 2 pasos para que lo vean las familias</p>

    <div class="step">
        <div class="step-number">1</div>
        <div class="step-content">
            <h3>Copia el enlace</h3>
            <p>En la app, pulsa el botón <strong>"📋 Copiar enlace"</strong>. Tu periódico ya está publicado en internet en esta dirección:</p>
            <p><code>https://dtabuyodesigner.github.io/generador_flipbook/{nombre}/</code></p>
        </div>
    </div>

    <div class="step">
        <div class="step-number">2</div>
        <div class="step-content">
            <h3>Pégalo en la web del colegio</h3>
            <p>Entra en el portal del colegio → <strong>Agregar contenido → "Enlaces"</strong> (o dentro de un <strong>"Anuncio"</strong>) y <strong>pega el enlace</strong>. Guarda y listo: las familias ya pueden abrir el periódico.</p>
        </div>
    </div>

    <div class="step highlight">
        <div class="step-number">💡</div>
        <div class="step-content">
            <h3>Bueno saber</h3>
            <p>El enlace es <strong>permanente</strong> y se abre directamente en el navegador (no hace falta descargar nada). Si vuelves a generar el periódico con el <strong>mismo nombre</strong>, se actualiza en la misma dirección.</p>
        </div>
    </div>
    
    <div class="footer">
        Generado el {datetime.now().strftime('%d/%m/%Y')}
    </div>
</div>
</body>
</html>
"""
            instr_path = os.path.join(output_dir, "INSTRUCCIONES.html")
            with open(instr_path, "w", encoding="utf-8") as f:
                f.write(instr_html)
            self.instrucciones_html = instr_path

            # Crear ZIP de la carpeta completa
            self.status_label.config(text="Creando ZIP...", foreground="orange")
            self.root.update()
            zip_path = output_dir + ".zip"
            base_dir = os.path.dirname(output_dir)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root_dir, _, files in os.walk(output_dir):
                    for file in files:
                        fp = os.path.join(root_dir, file)
                        zf.write(fp, os.path.relpath(fp, base_dir))

            self.output_folder = output_dir
            self.flipbook_html = html_path
            self.zip_path = zip_path

            self.btn_abrir.config(state=tk.NORMAL)
            self.btn_carpeta.config(state=tk.NORMAL)
            self.btn_instrucciones.config(state=tk.NORMAL)

            # El flipbook local YA está creado. La subida a GitHub Pages va aparte
            # para que un fallo de red nunca rompa el resultado local.

            # Aviso de sobrescritura (antes de lanzar el hilo). Si la comprobación
            # de red falla, se omite el aviso y se sigue (el hilo de publicación
            # ya avisa amablemente si hay problemas de conexión).
            token = self._leer_token_github()
            try:
                ya_existe = bool(token) and github_pages.existe(token, nombre)
            except Exception:
                ya_existe = False
            if ya_existe:
                if not messagebox.askyesno(
                    "Ya existe",
                    f"Ya hay un periódico publicado con el nombre «{github_pages.slug(nombre)}».\n\n"
                    "¿Quieres actualizarlo? Se sobrescribirá el anterior y el enlace "
                    "seguirá siendo el mismo."):
                    self.progress.stop()
                    self.status_label.config(text="Publicación cancelada (flipbook local creado).",
                                             foreground="blue")
                    return

            webbrowser.open(f"file://{html_path}")

            self.status_label.config(text="Publicando en internet...", foreground="orange")
            self._set_controles(False)  # deshabilita el botón principal mientras sube

            def _trabajo():
                url = self._publicar_seguro(nombre, output_dir)
                self.root.after(0, lambda: self._fin_publicacion(url, len(images), output_dir))

            threading.Thread(target=_trabajo, daemon=True).start()

        except Exception as e:
            self.progress.stop()
            self.status_label.config(text="❌ Error", foreground="red")
            messagebox.showerror("Error", f"Error: {str(e)}")

    def _set_controles(self, activo):
        estado = tk.NORMAL if activo else tk.DISABLED
        self.btn_generar.config(state=estado)

    def _publicar_seguro(self, nombre, output_dir):
        """Publica devolviendo URL o None; nunca lanza (corre en hilo)."""
        token = self._leer_token_github()
        if not token:
            return None
        try:
            return github_pages.publicar(token, nombre, output_dir)
        except Exception:
            return None

    def _fin_publicacion(self, url, n_paginas, output_dir):
        self.progress.stop()
        self._set_controles(True)
        self.post_url = url
        if url:
            self.url_var.set(url)
            self.btn_copiar.config(state=tk.NORMAL)
            self.btn_post.config(state=tk.NORMAL)
            self.status_label.config(text=f"¡Publicado! ({n_paginas} páginas)", foreground="green")
            messagebox.showinfo("Publicado",
                "Tu periódico está publicado en internet.\n\n"
                f"Enlace:\n{url}\n\n"
                "Pulsa «Copiar enlace» y pégalo en la web del colegio.")
        else:
            self.status_label.config(text=f"Flipbook creado ({n_paginas} páginas). No publicado.", foreground="blue")
            messagebox.showwarning("No se pudo publicar",
                "No se ha podido publicar en internet.\n\n"
                "Revisa tu conexión a internet. Si el problema sigue, avisa a Dani.\n\n"
                f"El periódico está en tu equipo:\n{output_dir}")
        self._limpiar_preview_temp()

    def _copiar_enlace(self):
        """Copia la URL pública al portapapeles."""
        url = self.url_var.get()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.root.update()
            self.status_label.config(text="Enlace copiado ✅", foreground="green")

    def _copiar_url(self, url):
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.root.update()

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
                return
            self._recargar_periodicos()
        threading.Thread(target=_w, daemon=True).start()

    def _actualizar_slug_label(self, event=None):
        s = github_pages.slug(self.nombre_output.get())
        self.slug_label.config(text=f"Se publicará como:  {s}")

    def _leer_token_github(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        for path in (os.path.join(exe_dir, "tokengenerarflipbook.txt"),
                     os.path.join(script_dir, "tokengenerarflipbook.txt"),
                     os.path.join(os.path.dirname(script_dir), "tokengenerarflipbook.txt")):
            if os.path.exists(path):
                try:
                    tok = open(path, encoding="utf-8").read().strip()
                    if tok:
                        return tok
                except Exception:
                    pass
        cfg = cargar_config()
        if cfg.get("github_token"):
            return _desofuscar(cfg["github_token"])
        return None

    def subir_a_wordpress(self, nombre, zip_path, page_paths):
        """Sube el flipbook a WordPress y crea un post publicado con el flipbook
        embebido (iframe srcdoc con las páginas subidas a la mediateca) + botón
        de descarga del ZIP. Devuelve la URL del post, o None si no procede o si
        falla (en cuyo caso el flipbook local permanece intacto)."""
        url = self.wp_url.get().strip()
        usuario = self.wp_user.get().strip()
        password = self.wp_pass.get().strip()

        # Si no hay credenciales completas, no se publica (solo flipbook local)
        if not (url and usuario and password):
            return None

        # Guardar configuración (la password solo si "Recordar credenciales")
        config = {"url": url, "usuario": usuario}
        if self.recordar.get():
            config["password"] = _ofuscar(password)
        guardar_config(config)

        titulo = self.post_titulo.get().strip() or nombre
        contenido_usuario = self.post_contenido.get("1.0", tk.END).strip()

        try:
            # 1) Subir el ZIP (para el botón de descarga)
            self.status_label.config(text="WordPress: subiendo ZIP...", foreground="orange")
            self.root.update()
            media_zip = wp_subir_media(url, usuario, password, zip_path, "application/zip")
            zip_url = media_zip.get("source_url", "")

            # 2) Subir cada página PNG (para el flipbook embebido)
            image_urls = []
            total = len(page_paths)
            for idx, pp in enumerate(page_paths, 1):
                self.status_label.config(text=f"WordPress: subiendo página {idx}/{total}...", foreground="orange")
                self.root.update()
                media_img = wp_subir_media(url, usuario, password, pp, "image/png")
                image_urls.append(media_img.get("source_url", ""))

            # 3) Construir el contenido del post (texto + flipbook + descarga)
            self.status_label.config(text="WordPress: creando post...", foreground="orange")
            self.root.update()

            embed_html = generar_html_embed(titulo, image_urls)
            srcdoc = embed_html.replace("&", "&amp;").replace('"', "&quot;")

            partes = []
            if contenido_usuario:
                texto_html = contenido_usuario.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                texto_html = texto_html.replace("\n", "<br>\n")
                partes.append(f"<p>{texto_html}</p>")

            partes.append(
                f'<iframe srcdoc="{srcdoc}" style="width:100%;height:82vh;min-height:480px;max-height:920px;border:0;" '
                f'loading="lazy" allowfullscreen></iframe>')

            if zip_url:
                partes.append(
                    '<p style="text-align:center;margin-top:20px;">'
                    f'<a href="{zip_url}" download '
                    'style="display:inline-block;background:#667eea;color:#fff;padding:12px 28px;'
                    'border-radius:30px;text-decoration:none;font-weight:bold;">'
                    '⬇ Descargar flipbook (ZIP)</a></p>')

            contenido_post = "\n".join(partes)

            post = wp_crear_post(url, usuario, password, titulo, contenido_post, status="publish")
            return post.get("link")

        except urllib.error.HTTPError as e:
            messagebox.showwarning(
                "WordPress no disponible",
                "El flipbook se creó correctamente en local, pero falló la publicación en WordPress.\n\n"
                f"Error: {_wp_error_legible(e)}")
            return None
        except urllib.error.URLError as e:
            messagebox.showwarning(
                "WordPress no disponible",
                "El flipbook se creó correctamente en local, pero no se pudo conectar con WordPress.\n\n"
                f"Comprueba la URL y la conexión.\n\nError: {e.reason}")
            return None
        except Exception as e:
            messagebox.showwarning(
                "WordPress no disponible",
                "El flipbook se creó correctamente en local, pero falló la publicación en WordPress.\n\n"
                f"Error: {str(e)}")
            return None
    
    def abrir_flipbook(self):
        if self.flipbook_html and os.path.exists(self.flipbook_html):
            webbrowser.open(f"file://{self.flipbook_html}")
    
    def abrir_carpeta(self):
        if self.output_folder and os.path.exists(self.output_folder):
            if platform.system() == "Windows":
                os.startfile(self.output_folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", self.output_folder])
            else:
                subprocess.Popen(["xdg-open", self.output_folder])

    def abrir_post(self):
        if self.post_url:
            webbrowser.open(self.post_url)
    
    def abrir_instrucciones(self):
        if self.instrucciones_html and os.path.exists(self.instrucciones_html):
            webbrowser.open(f"file://{self.instrucciones_html}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CreadorFlipbook(root)
    root.mainloop()
