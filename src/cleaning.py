"""Variables auxiliares de PROFECO. Las columnas originales no se modifican."""
import re

import numpy as np
import pandas as pd

from src.exploration import STORE, load_data

CANAL = "Supermercado / Tienda de Autoservicio"
_QTY = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|gr|g|lt|l|ml)\.?(?![a-z])", re.IGNORECASE)
_PIEZAS = re.compile(r"C/(\d+)", re.IGNORECASE)
_A_BASE = {"kg": ("kg", 1.0), "gr": ("kg", 0.001), "g": ("kg", 0.001),
           "lt": ("l", 1.0), "l": ("l", 1.0), "ml": ("l", 0.001)}


def parse_quantity(presentacion):
    """Cantidad y unidad base (kg, l, pieza) de una presentación PROFECO.

    Devuelve (nan, None) cuando la presentación es ambigua: dos cantidades,
    rangos («800 Ó 880 Gr.») o sin cantidad. Esos casos no se normalizan.
    """
    text = str(presentacion)
    if re.search(r"\d\s*[óo]\s*\d", text, re.IGNORECASE):
        return np.nan, None
    pieces = _PIEZAS.findall(text)
    if len(pieces) == 1:
        return float(pieces[0]), "pieza"
    found = _QTY.findall(text)
    if len(found) == 1:
        value, unit = found[0]
        base, factor = _A_BASE[unit.lower()]
        return float(value) * factor, base
    if text.strip().lower() == "pieza":
        return 1.0, "pieza"
    return np.nan, None


def prepare(df=None):
    """Agrega tipos numéricos, fecha y claves; no elimina filas."""
    df = load_data() if df is None else df
    out = df.copy()
    out["precio_num"] = pd.to_numeric(out.precio, errors="coerce").astype(float)
    out["fecha"] = pd.to_datetime(out.fecha_registro, format="%Y/%m/%d", errors="coerce")
    out["lat"] = pd.to_numeric(out.latitud, errors="coerce").astype(float)
    out["lon"] = pd.to_numeric(out.longitud, errors="coerce").astype(float)
    out["establecimiento_id"] = pd.factorize(pd.MultiIndex.from_frame(out[STORE]))[0]
    return out


def quality_flags(df):
    """Conteos de control sobre la tabla preparada."""
    return pd.Series({
        "registros": len(df),
        "duplicados_exactos": int(df.duplicated(subset=list(df.columns[:15])).sum()),
        "precio_no_valido": int((~(df.precio_num > 0)).sum()),
        "fecha_invalida": int(df.fecha.isna().sum()),
        "coordenadas_faltantes": int((df.lat.isna() | df.lon.isna()).sum()),
        "registros_canal_autoservicio": int(df.giro.eq(CANAL).sum()),
    })
