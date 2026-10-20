"""Verificación final: salidas presentes, notebooks ejecutados y consistencia entre tablas."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
PROC = ROOT / "data/processed"
required = [
    "homologacion_geografica.csv", "ensu_percepcion_areas.csv", "ensu_composicion_areas.csv",
    "canasta_definicion.csv", "precios_area_producto.csv", "cobertura_canasta_matriz.csv",
    "comparacion_metodos_canasta.csv", "observaciones_canasta.csv", "canasta_municipio.csv",
    "auditoria_cobertura.csv", "dataset_final.csv", "resultados_analisis.csv",
    "dispersion_productos.csv", "comparacion_cadenas.csv", "precios_relativos_area_producto.csv",
]
for name in required:
    assert (PROC / name).exists(), f"Falta {name}"
for name in ["outputs/social/grafica_principal_1080x1350.png", "outputs/social/grafica_principal_1600x900.png",
             "outputs/social/grafica_principal_1080x1350.svg", "outputs/social/grafica_principal_1600x900.svg",
             *[f"outputs/charts/{n}.png" for n in [
                 "02_ranking_costo_canasta", "03_ranking_seguridad", "04_dispersion_productos",
                 "05_distribucion_precios_tienda", "06_heatmap_precio_relativo", "07_comparacion_cadenas",
                 "08_tabla_ranking", "09_mapa_municipal_costo", "10_mapa_municipal_seguridad",
                 "00a_cobertura_geografica", "00b_distribucion_precios", "00c_metodos_marca",
                 "01_cobertura_temporal"]],
             "data/processed/geo/municipios_lcc.json",
             "docs/index.html", "data/metadata/ensu_manifest.json"]:
    assert (ROOT / name).exists(), f"Falta {name}"

for nb_path in sorted((ROOT / "notebooks").glob("0*.ipynb")):
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is not None, f"{nb_path.name} sin ejecutar"
            assert not any(o["output_type"] == "error" for o in cell["outputs"]), nb_path.name

final = pd.read_csv(PROC / "dataset_final.csv")
res = pd.read_csv(PROC / "resultados_analisis.csv")
aud = pd.read_csv(PROC / "auditoria_cobertura.csv")
homolog = pd.read_csv(PROC / "homologacion_geografica.csv")
canasta = pd.read_csv(PROC / "canasta_municipio.csv")
ensu = pd.read_csv(PROC / "ensu_percepcion_areas.csv")
params = json.loads((ROOT / "data/metadata/canasta_parametros.json").read_text(encoding="utf-8"))

assert len(aud) == len(homolog) == 72
assert set(final.area_urbana_ensu) == set(res.area_urbana_ensu)
assert set(final.area_urbana_ensu) == set(aud.loc[aud.pasa_validacion, "area_ensu"])
assert (aud.loc[~aud.pasa_validacion, "motivo_exclusion"].str.len() > 0).all()
assert final.productos_canasta.eq(len(params["productos"])).all()
# El costo se puede recomponer desde los precios por producto.
from src.basket import CANDIDATOS  # noqa: E402
prices = pd.read_csv(PROC / "precios_area_producto.csv")
qty = CANDIDATOS.set_index("producto_normalizado").cantidad_canasta
p = prices[prices.producto_normalizado.isin(params["productos"])]
recomputed = (p.precio_mediana * p.producto_normalizado.map(qty)).groupby(p.area_urbana_ensu).sum()
check = final.set_index("area_urbana_ensu").costo_canasta
assert (recomputed.reindex(check.index) - check).abs().max() < 1e-6
# La seguridad del dataset es exactamente la del tabulado ENSU.
merged = final.merge(ensu, on="area_urbana_ensu", suffixes=("", "_ensu"))
assert (merged.seguridad_pct - merged.seguridad_pct_ensu).abs().max() < 1e-9
assert res.cuadrante.between(1, 4).all()
assert canasta.costo_canasta.notna().sum() >= len(final)
print(f"Verificación correcta: {len(final)} áreas, {len(params['productos'])} productos, "
      f"{len(required)} tablas y notebooks 00–05 ejecutados sin errores.")
