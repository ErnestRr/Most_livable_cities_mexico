"""Exploración descriptiva del archivo completo, sin modificar ni eliminar filas."""
from pathlib import Path
import hashlib
import json
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    "producto", "presentacion", "marca", "categoria", "catalogo", "precio",
    "fecha_registro", "cadena_comercial", "giro", "nombre_comercial",
    "direccion", "estado", "municipio", "latitud", "longitud",
]
STORE = ["estado", "municipio", "cadena_comercial", "nombre_comercial", "direccion"]
ITEM = ["producto", "presentacion", "marca"]


def source_path():
    for path in [ROOT / "data/raw/08-2026_Q2.csv", ROOT.parent / "08-2026_Q2.csv"]:
        if path.exists():
            return path
    raise FileNotFoundError("Colocar 08-2026_Q2.csv en data/raw/.")


def load_data(path=None):
    path = Path(path) if path else source_path()
    # No interpretar S/M, NA u otros textos originales como nulos.
    df = pd.read_csv(path, dtype="string", encoding="utf-8-sig", keep_default_na=False)
    if list(df.columns) != EXPECTED:
        raise ValueError(f"Esquema inesperado: {df.columns.tolist()}")
    if df.empty:
        raise ValueError("El CSV está vacío.")
    return df


def normalized_text(value):
    text = " ".join(str(value).strip().casefold().split())
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))


def audit(df):
    """Las claves usan textos originales. Vacíos se detectan, no se imputan."""
    data = df.copy()
    blank = df.apply(lambda s: s.str.strip().eq(""))
    price = pd.to_numeric(df.precio, errors="coerce")
    date = pd.to_datetime(df.fecha_registro, format="%Y/%m/%d", errors="coerce")
    lat = pd.to_numeric(df.latitud, errors="coerce")
    lon = pd.to_numeric(df.longitud, errors="coerce")
    # Identificadores internos por tuplas exactas, sin concatenaciones ambiguas.
    data["_establecimiento"] = pd.factorize(pd.MultiIndex.from_frame(df[STORE]))[0]
    data["_variante"] = pd.factorize(pd.MultiIndex.from_frame(df[ITEM]))[0]
    data["_presentacion"] = pd.factorize(
        pd.MultiIndex.from_frame(df[["producto", "presentacion"]]))[0]
    data["_fecha"] = date
    data["_precio_valido"] = price.notna() & np.isfinite(price) & price.gt(0)
    data["_duplicado"] = df.duplicated()
    data["_identidad_incompleta"] = blank[STORE].any(axis=1)
    data["_producto_incompleto"] = blank[ITEM].any(axis=1)
    valid_geo = ~blank[["estado", "municipio"]].any(axis=1)
    municipalities = data.loc[valid_geo].groupby(["estado", "municipio"]).agg(
        registros=("producto", "size"),
        establecimientos=("_establecimiento", "nunique"),
        cadenas=("cadena_comercial", lambda s: s[s.str.strip().ne("")].nunique()),
        productos=("producto", lambda s: s[s.str.strip().ne("")].nunique()),
        producto_presentaciones=("_presentacion", "nunique"),
        variantes_producto_presentacion_marca=("_variante", "nunique"),
        fecha_inicio=("_fecha", "min"), fecha_fin=("_fecha", "max"),
        dias_observados=("_fecha", "nunique"),
        precios_validos=("_precio_valido", "sum"),
        duplicados_excedentes=("_duplicado", "sum"),
        registros_identidad_incompleta=("_identidad_incompleta", "sum"),
        registros_producto_incompleto=("_producto_incompleto", "sum"),
    ).reset_index()
    span = (date.max() - date.min()).days + 1 if date.notna().any() else 0
    municipalities["dias_ventana_global"] = span
    municipalities["cobertura_dias_calendario_pct"] = (
        municipalities.dias_observados / span * 100 if span else np.nan)
    n_geo = len(municipalities)
    products = data.loc[valid_geo & ~blank[ITEM].any(axis=1)].groupby(ITEM).agg(
        registros=("precio", "size"), establecimientos=("_establecimiento", "nunique"),
    ).reset_index()
    counts = data.loc[valid_geo & ~blank[ITEM].any(axis=1),
                      ITEM + ["estado", "municipio"]].drop_duplicates().groupby(ITEM).size()
    products = products.merge(counts.rename("municipios"), on=ITEM, validate="one_to_one")
    products["cobertura_municipios_pct"] = products.municipios / n_geo * 100 if n_geo else np.nan
    daily = data.groupby("_fecha").agg(registros=("producto", "size"),
                                       establecimientos=("_establecimiento", "nunique"))
    if span:
        daily = daily.reindex(pd.date_range(date.min(), date.max()), fill_value=0)
    daily.index.name = "fecha"
    daily = daily.reset_index()
    municipality_dates = data.groupby(["estado", "municipio", "_fecha"]).size().rename(
        "registros").reset_index().rename(columns={"_fecha": "fecha"})
    categories = data.groupby(["catalogo", "categoria"]).size().rename("registros").reset_index()
    states = data.groupby("estado").size().rename("registros").reset_index()
    nulls = pd.DataFrame({"columna": df.columns, "vacios": blank.sum().values})
    nulls["vacios_pct"] = nulls.vacios / len(df) * 100
    geo = df[["estado", "municipio"]].drop_duplicates().copy()
    geo["estado_revision"] = geo.estado.map(normalized_text)
    geo["municipio_revision"] = geo.municipio.map(normalized_text)
    variants = geo[geo.duplicated(["estado_revision", "municipio_revision"], keep=False)]
    issues = {
        "duplicados_excedentes_exactos": int(df.duplicated().sum()),
        "filas_en_grupos_duplicados": int(df.duplicated(keep=False).sum()),
        "precio_vacio": int(blank.precio.sum()),
        "precio_no_numerico_no_vacio": int((price.isna() & ~blank.precio).sum()),
        "precio_no_finito_no_nulo": int((price.notna() & ~np.isfinite(price)).sum()),
        "precio_cero_o_negativo": int(price.le(0).sum()),
        "fecha_vacia": int(blank.fecha_registro.sum()),
        "fecha_invalida_no_vacia": int((date.isna() & ~blank.fecha_registro).sum()),
        "geografia_incompleta": int((~valid_geo).sum()),
        "identidad_establecimiento_incompleta": int(data._identidad_incompleta.sum()),
        "producto_presentacion_marca_incompleto": int(data._producto_incompleto.sum()),
        "coordenadas_faltantes_o_no_numericas": int((lat.isna() | lon.isna()).sum()),
        "coordenadas_fuera_rango_mundial": int(
            ((lat.notna() & ~lat.between(-90, 90)) | (lon.notna() & ~lon.between(-180, 180))).sum()),
        "coordenadas_cero": int((lat.eq(0) | lon.eq(0)).sum()),
        "variantes_textuales_geograficas_para_revision": len(variants),
    }
    summary = {
        "registros": len(df), "columnas": len(df.columns),
        "estados": int(df.loc[~blank.estado, "estado"].nunique()),
        "municipios_estado_municipio": n_geo,
        "nombres_municipio_distintos": int(df.loc[~blank.municipio, "municipio"].nunique()),
        "establecimientos_clave_observada": int(data._establecimiento.nunique()),
        "establecimientos_identidad_completa": int(
            data.loc[~data._identidad_incompleta, "_establecimiento"].nunique()),
        "cadenas": int(df.loc[~blank.cadena_comercial, "cadena_comercial"].nunique()),
        "productos_nombre": int(df.loc[~blank.producto, "producto"].nunique()),
        "producto_presentaciones": int(data._presentacion.nunique()),
        "variantes_producto_presentacion_marca": int(data._variante.nunique()),
        "fecha_inicio": str(date.min().date()) if date.notna().any() else None,
        "fecha_fin": str(date.max().date()) if date.notna().any() else None,
        "dias_observados": int(date.nunique()), "dias_calendario_ventana": span,
    }
    anomaly = (~data._precio_valido | date.isna() | ~valid_geo
               | data._identidad_incompleta | data._producto_incompleto
               | lat.isna() | lon.isna() | ~lat.between(-90, 90)
               | ~lon.between(-180, 180) | lat.eq(0) | lon.eq(0))
    samples = df.loc[anomaly].head(100).copy()
    samples.insert(0, "fila_datos_1_based", samples.index + 1)
    tables = {
        "cobertura_municipios_profeco": municipalities.sort_values("registros", ascending=False),
        "cobertura_productos_profeco": products.sort_values("cobertura_municipios_pct", ascending=False),
        "cobertura_diaria_profeco": daily, "cobertura_municipio_fecha_profeco": municipality_dates,
        "catalogos_categorias_profeco": categories.sort_values("registros", ascending=False),
        "estados_profeco": states, "nulos_profeco": nulls,
        "variantes_geograficas_revision": variants,
        "muestra_anomalias_profeco": samples,
        "controles_calidad_profeco": pd.DataFrame(issues.items(), columns=["control", "registros"]),
    }
    assert municipalities.registros.sum() + (~valid_geo).sum() == len(df)
    assert daily.registros.sum() + date.isna().sum() == len(df)
    assert categories.registros.sum() == len(df)
    assert products.municipios.le(n_geo).all()
    return summary, tables


def export_results(summary, tables, path):
    processed = ROOT / "data/processed"
    metadata = ROOT / "data/metadata"
    processed.mkdir(parents=True, exist_ok=True)
    metadata.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(processed / f"{name}.csv", index=False, encoding="utf-8-sig")
    with Path(path).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = {
        "archivo": Path(path).name, "sha256": digest, "bytes": Path(path).stat().st_size,
        "fuente_declarada": "PROFECO; archivo aportado por el usuario",
        "url_descarga": None, "verificacion_origen_oficial": "pendiente",
        "codificacion_lectura": "utf-8-sig", "separador": ",",
        "resumen": summary,
    }
    (metadata / "profeco_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (metadata / "ruta_local.txt").write_text(str(Path(path).resolve()), encoding="utf-8")


if __name__ == "__main__":
    source = source_path()
    frame = load_data(source)
    summary, tables = audit(frame)
    export_results(summary, tables, source)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(tables["controles_calidad_profeco"].to_string(index=False))
