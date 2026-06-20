"""Capa de red para publicar flipbooks en GitHub Pages. Sin tkinter."""
import os
import re
import json
import base64
import unicodedata
import urllib.request
import urllib.error

OWNER = "dtabuyodesigner"
REPO = "generador_flipbook"
BRANCH = "gh-pages"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
PAGES_URL = f"https://{OWNER}.github.io/{REPO}"


class GitHubError(Exception):
    """Error legible de la capa GitHub (para mostrar al usuario)."""


def slug(nombre):
    """Convierte un nombre en una cadena URL-segura."""
    s = unicodedata.normalize("NFKD", nombre or "")
    s = s.encode("ascii", "ignore").decode("ascii").lower().strip()
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-_")
    return s or "periodico"


def _headers(token):
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "flipbook-generator",
        "Content-Type": "application/json",
    }


def _request(token, method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in _headers(token).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _error_legible(err):
    """Mensaje legible (interno) a partir de un HTTPError."""
    try:
        data = json.loads(err.read().decode("utf-8"))
        return data.get("message", str(err))
    except Exception:
        return str(err)


def _get_ref_sha(token):
    """SHA del último commit de BRANCH; None si la rama no existe."""
    try:
        data = _request(token, "GET", f"{API}/git/ref/heads/{BRANCH}")
        return data["object"]["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _asegurar_rama(token):
    """Crea BRANCH como rama huérfana (con .gitkeep) si no existe. Devuelve SHA."""
    sha = _get_ref_sha(token)
    if sha:
        return sha
    blob = _request(token, "POST", f"{API}/git/blobs",
                    {"content": "", "encoding": "utf-8"})
    tree = _request(token, "POST", f"{API}/git/trees", {
        "tree": [{"path": ".gitkeep", "mode": "100644",
                  "type": "blob", "sha": blob["sha"]}]})
    commit = _request(token, "POST", f"{API}/git/commits", {
        "message": "Inicializar gh-pages", "tree": tree["sha"], "parents": []})
    _request(token, "POST", f"{API}/git/refs",
             {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    return commit["sha"]


def _asegurar_pages(token):
    """Best-effort: activa GitHub Pages si no está ya activo. Nunca bloquea la
    publicación: si Pages ya está activo, o el token no tiene permiso para
    crearlo, se ignora (el contenido se publica igual con permiso de Contents).

    Activar Pages vía API solo hace falta UNA vez por repo; un token
    fine-grained de Contents/Pages puede no poder crearlo (403), pero como en
    este repo Pages ya está activo, esa llamada se omite."""
    try:
        _request(token, "GET", f"{API}/pages")
        return  # ya está activo
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return  # 403/otros: no bloquear; Pages probablemente ya configurado
    # Solo si NO existía (404) intentamos crearlo, en best-effort
    try:
        _request(token, "POST", f"{API}/pages",
                 {"source": {"branch": BRANCH, "path": "/"}})
    except urllib.error.HTTPError:
        return


def _arbol_actual(token):
    """Devuelve (parent_sha, blobs) del último commit de BRANCH.
    blobs: lista de dicts {path, mode, type, sha} solo de type=='blob'.
    Si la rama no existe: (None, [])."""
    sha = _get_ref_sha(token)
    if not sha:
        return None, []
    commit = _request(token, "GET", f"{API}/git/commits/{sha}")
    tree = _request(token, "GET",
                    f"{API}/git/trees/{commit['tree']['sha']}?recursive=1")
    blobs = [{"path": e["path"], "mode": e["mode"],
              "type": "blob", "sha": e["sha"]}
             for e in tree.get("tree", []) if e["type"] == "blob"]
    return sha, blobs


def _archivos_flipbook(output_dir, s):
    """Pares (ruta_en_repo, ruta_local) de index.html + pages/*.png."""
    out = []
    idx = os.path.join(output_dir, "index.html")
    if os.path.exists(idx):
        out.append((f"{s}/index.html", idx))
    pages = os.path.join(output_dir, "pages")
    if os.path.isdir(pages):
        for f in sorted(os.listdir(pages)):
            if f.lower().endswith(".png"):
                out.append((f"{s}/pages/{f}", os.path.join(pages, f)))
    return out


def _commit_arbol(token, parent_sha, tree_entries, mensaje):
    """Crea un tree COMPLETO (sin base_tree), un commit y mueve la ref."""
    tree = _request(token, "POST", f"{API}/git/trees", {"tree": tree_entries})
    commit = _request(token, "POST", f"{API}/git/commits", {
        "message": mensaje, "tree": tree["sha"], "parents": [parent_sha]})
    _request(token, "PATCH", f"{API}/git/refs/heads/{BRANCH}",
             {"sha": commit["sha"]})


def existe(token, nombre):
    s = slug(nombre)
    _, blobs = _arbol_actual(token)
    return any(b["path"].startswith(f"{s}/") for b in blobs)


def listar(token):
    _, blobs = _arbol_actual(token)
    nombres = set()
    for b in blobs:
        parte = b["path"].split("/", 1)
        if len(parte) == 2:  # está dentro de una carpeta
            nombres.add(parte[0])
    return [{"nombre": n, "url": f"{PAGES_URL}/{n}/"} for n in sorted(nombres)]


def publicar(token, nombre, output_dir):
    s = slug(nombre)
    _asegurar_pages(token)
    rama_sha = _asegurar_rama(token)
    parent_sha, blobs = _arbol_actual(token)
    if parent_sha is None:  # rama recién creada y aún no propagada
        parent_sha = rama_sha
    # conservar todo lo que NO sea de esta carpeta (reemplazo limpio)
    keep = [b for b in blobs if not b["path"].startswith(f"{s}/")]
    nuevos = []
    for repo_path, local in _archivos_flipbook(output_dir, s):
        with open(local, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")
        blob = _request(token, "POST", f"{API}/git/blobs",
                        {"content": content, "encoding": "base64"})
        nuevos.append({"path": repo_path, "mode": "100644",
                       "type": "blob", "sha": blob["sha"]})
    _commit_arbol(token, parent_sha, keep + nuevos, f"Publicar: {s}")
    return f"{PAGES_URL}/{s}/"


def borrar(token, nombre):
    s = slug(nombre)
    parent_sha, blobs = _arbol_actual(token)
    if parent_sha is None:
        return
    keep = [b for b in blobs if not b["path"].startswith(f"{s}/")]
    if len(keep) == len(blobs):
        return  # no había nada que borrar
    _commit_arbol(token, parent_sha, keep, f"Borrar: {s}")
