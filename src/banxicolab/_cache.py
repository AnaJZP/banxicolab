"""Caché en disco de las respuestas del SIE (solo datos públicos, nunca el token)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path


def carpeta_cache() -> Path:
    """Carpeta por omisión de la caché en disco."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "banxicolab" / "cache"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "banxicolab"


class CacheDisco:
    def __init__(self, carpeta: str | Path | None = None, vigencia_horas: float = 12):
        self.carpeta = Path(carpeta) if carpeta else carpeta_cache()
        self.vigencia = vigencia_horas * 3600

    def _archivo(self, llave: tuple) -> Path:
        huella = hashlib.sha256(json.dumps(llave, sort_keys=True, default=str).encode()).hexdigest()
        return self.carpeta / f"{huella}.json"

    def obtener(self, llave: tuple):
        archivo = self._archivo(llave)
        try:
            if time.time() - archivo.stat().st_mtime > self.vigencia:
                return None
            return json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def guardar(self, llave: tuple, cuerpo) -> None:
        try:
            self.carpeta.mkdir(parents=True, exist_ok=True)
            archivo = self._archivo(llave)
            temporal = archivo.with_suffix(".tmp")
            temporal.write_text(json.dumps(cuerpo, ensure_ascii=False), encoding="utf-8")
            temporal.replace(archivo)  # escritura atómica
        except OSError:
            pass  # sin permiso de escritura: la caché en disco simplemente no se usa

    def limpiar(self) -> int:
        borrados = 0
        for archivo in self.carpeta.glob("*.json"):
            archivo.unlink(missing_ok=True)
            borrados += 1
        return borrados
