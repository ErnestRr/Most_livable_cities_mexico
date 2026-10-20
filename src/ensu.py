"""Lectura del cuadro 1.7 de los tabulados básicos ENSU (percepción por área urbana)."""
from pathlib import Path
import hashlib

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/ensu"
PERIODO = "junio 2026"
URL_BASE = "https://www.inegi.org.mx/contenidos/programas/ensu/tabulados/2026/"
ARCHIVOS = {
    "estimacion": ("junio_2026_estimacion/1.Bas_percepcion_seguridad_jun_2026_est.xlsx",
                   "ensu_tabulados_basicos_junio_2026_estimacion_xlsx.zip"),
    "cv": ("junio_2026_coeficiente/1.Bas_percepcion_seguridad_jun_2026_cv.xlsx",
           "ensu_tabulados_basicos_junio_2026_coeficiente_xlsx.zip"),
    "intervalos": ("junio_2026_intervalos/1.Bas_percepcion_seguridad_jun_2026_interv.xlsx",
                   "ensu_tabulados_basicos_junio_2026_intervalos_xlsx.zip"),
}
ENTIDADES = {
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Coahuila de Zaragoza",
    "Colima", "Chiapas", "Chihuahua", "Ciudad de México", "Durango", "Guanajuato", "Guerrero",
    "Hidalgo", "Jalisco", "México", "Michoacán de Ocampo", "Morelos", "Nayarit", "Nuevo León",
    "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora",
    "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz de Ignacio de la Llave", "Yucatán", "Zacatecas",
}


def _rows(relative):
    wb = openpyxl.load_workbook(RAW / relative, read_only=True, data_only=True)
    rows = [tuple(r) for r in wb["1.7"].iter_rows(values_only=True)]
    wb.close()
    return rows


def _parse(rows, first_value_col, width):
    """Recorre la jerarquía entidad > [región CDMX] > área urbana > Seguro/Inseguro.

    Las filas sin población son encabezados (entidad o región); las filas con
    población son áreas urbanas. No se infiere nada a partir del parecido de nombres.
    """
    out, estado, region, area = [], None, None, None
    start = next(i for i, r in enumerate(rows) if r[0] == "Estados Unidos Mexicanos")
    for r in rows[start:]:
        label = r[0].strip() if isinstance(r[0], str) else None
        if label is None or label.startswith(("Nota", "Fuente", "INEGI")):
            continue
        values = r[first_value_col:first_value_col + width]
        if label in ("Seguro", "Inseguro"):
            out.append({"estado_ensu": estado, "region_ensu": region, "area_urbana_ensu": area,
                        "respuesta": label.lower(), "valores": values})
        elif r[1] is None:  # encabezado
            if label in ENTIDADES:
                estado, region = label, None
            else:
                region = label
        else:
            area = label
            if label == "Estados Unidos Mexicanos":
                estado = "Nacional"
    return out


def load_ensu():
    est = _parse(_rows(ARCHIVOS["estimacion"][0]), 2, 2)
    cv = _parse(_rows(ARCHIVOS["cv"][0]), 2, 2)
    ic = _parse(_rows(ARCHIVOS["intervalos"][0]), 5, 2)
    assert len(est) == len(cv) == len(ic)
    records = []
    for e, c, i in zip(est, cv, ic):
        keys = ("estado_ensu", "region_ensu", "area_urbana_ensu", "respuesta")
        assert all(e[k] == c[k] == i[k] for k in keys), (e, c, i)
        records.append({**{k: e[k] for k in keys}, "pct": e["valores"][1],
                        "cv_pct": c["valores"][1], "ic90_inf": i["valores"][0],
                        "ic90_sup": i["valores"][1]})
    long = pd.DataFrame(records)
    wide = long.pivot_table(index=["estado_ensu", "region_ensu", "area_urbana_ensu"],
                            columns="respuesta", values=["pct", "cv_pct", "ic90_inf", "ic90_sup"],
                            dropna=False, aggfunc="first")
    wide.columns = [f"{v}_{k}" for v, k in wide.columns]
    wide = wide.dropna(how="all").reset_index()
    wide = wide.rename(columns={"pct_seguro": "seguridad_pct", "pct_inseguro": "inseguridad_pct"})
    # ENSU publica directamente «seguro»; no se calcula 100 - inseguro porque
    # la diferencia restante corresponde a «no sabe/no responde».
    wide["no_responde_pct"] = 100 - wide.seguridad_pct - wide.inseguridad_pct
    wide["region_ensu"] = wide.region_ensu.replace("", pd.NA)
    wide["periodo_ensu"] = PERIODO
    order = ["estado_ensu", "region_ensu", "area_urbana_ensu", "periodo_ensu", "seguridad_pct",
             "inseguridad_pct", "no_responde_pct", "cv_pct_seguro", "ic90_inf_seguro",
             "ic90_sup_seguro", "cv_pct_inseguro", "ic90_inf_inseguro", "ic90_sup_inseguro"]
    return wide[order]


def manifest():
    rows = []
    for kind, (xlsx, zip_name) in ARCHIVOS.items():
        local_zip = RAW / f"{xlsx.split('/')[0]}.zip"
        digest = hashlib.sha256(local_zip.read_bytes()).hexdigest()
        rows.append({"tipo": kind, "url": URL_BASE + zip_name, "zip_local": local_zip.name,
                     "sha256_zip": digest, "libro": xlsx.split("/")[1], "cuadro": "1.7"})
    return rows


def download(force=False):
    """Descarga los tres paquetes oficiales si no existen y extrae el libro 1."""
    import io
    import zipfile
    import requests
    RAW.mkdir(parents=True, exist_ok=True)
    for xlsx, zip_name in ARCHIVOS.values():
        folder = xlsx.split("/")[0]
        target = RAW / f"{folder}.zip"
        if force or not target.exists():
            response = requests.get(URL_BASE + zip_name, timeout=180)
            response.raise_for_status()
            target.write_bytes(response.content)
        with zipfile.ZipFile(io.BytesIO(target.read_bytes())) as z:
            z.extract(xlsx.split("/")[1], RAW / folder)
