"""Acorta URLs con is.gd (gratis, sin API key). Solo stdlib."""
import urllib.parse
import urllib.request


def acortar(url, timeout=10):
    """Devuelve una URL corta (is.gd) o None si falla. Nunca lanza."""
    try:
        api = ("https://is.gd/create.php?format=simple&url="
               + urllib.parse.quote(url, safe=""))
        req = urllib.request.Request(api, headers={"User-Agent": "flipbook-generator"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            corta = resp.read().decode("utf-8").strip()
        return corta if corta.startswith("http") else None
    except Exception:
        return None
