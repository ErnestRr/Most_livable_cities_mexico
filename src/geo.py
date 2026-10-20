"""Límites municipales y estatales del Marco Geoestadístico 2024 (INEGI).

Se simplifican por ajuste a una rejilla métrica (los vecinos comparten vértices, así
que no se abren huecos entre municipios) y se guardan en dos versiones:
coordenadas Lambert de INEGI (para matplotlib) y lon/lat GeoJSON (para Plotly).
"""
from pathlib import Path
import json
import warnings

import numpy as np
import shapefile
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/inegi_mg"
OUT = ROOT / "data/processed/geo"
URL = ("https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/"
       "productos/geografia/marcogeo/794551132173/mg_2024_integrado.zip")
# EPSG:6372 = Mexico ITRF2008 / LCC, la proyección declarada en 00mun.prj
TO_LONLAT = Transformer.from_crs("EPSG:6372", "EPSG:4326", always_xy=True)


def _snap(points, grid):
    """Ajusta a la rejilla y quita vértices repetidos consecutivos."""
    p = np.round(np.asarray(points) / grid) * grid
    keep = np.r_[True, np.any(np.diff(p, axis=0) != 0, axis=1)]
    return p[keep]


def _rings(shape, grid, min_points=4):
    bounds = list(shape.parts) + [len(shape.points)]
    rings = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        ring = _snap(shape.points[a:b], grid)
        if len(ring) >= min_points:
            rings.append(ring)
    return rings


def read_layer(name, key_fields, grid):
    with warnings.catch_warnings():  # el .cpg dice "88591" (ISO-8859-1 = latin-1)
        warnings.simplefilter("ignore")
        reader = shapefile.Reader(str(RAW / name), encoding="latin-1")
    features = []
    for rec, shp in zip(reader.iterRecords(), reader.iterShapes()):
        rings = _rings(shp, grid)
        if rings:
            features.append({"props": {k: rec[k] for k in key_fields}, "rings": rings})
    return features


def build(grid_mun=250, grid_ent=600):
    """Crea data/processed/geo/*.json (proyectado y lon/lat). Tarda ~1 min."""
    OUT.mkdir(parents=True, exist_ok=True)
    layers = {"municipios": read_layer("00mun", ["CVEGEO", "CVE_ENT", "CVE_MUN", "NOMGEO"], grid_mun),
              "entidades": read_layer("00ent", ["CVEGEO", "NOMGEO"], grid_ent)}
    for name, feats in layers.items():
        proj = [{"props": f["props"], "rings": [r.round(0).astype(int).tolist() for r in f["rings"]]}
                for f in feats]
        (OUT / f"{name}_lcc.json").write_text(json.dumps(proj, ensure_ascii=False), encoding="utf-8")
    return {k: len(v) for k, v in layers.items()}


def load_projected(name):
    feats = json.loads((OUT / f"{name}_lcc.json").read_text(encoding="utf-8"))
    for f in feats:
        f["rings"] = [np.asarray(r, dtype=float) for r in f["rings"]]
    return feats


def to_geojson(features, id_field="CVEGEO"):
    """FeatureCollection lon/lat (anillos como polígonos simples; suficiente para Plotly)."""
    out = []
    for f in features:
        polys = []
        for r in f["rings"]:
            lon, lat = TO_LONLAT.transform(r[:, 0], r[:, 1])
            coords = np.round(np.c_[lon, lat], 4).tolist()
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            polys.append([coords])
        out.append({"type": "Feature", "id": f["props"][id_field], "properties": f["props"],
                    "geometry": {"type": "MultiPolygon", "coordinates": polys}})
    return {"type": "FeatureCollection", "features": out}


if __name__ == "__main__":
    print(build())
