"""Contraste independiente de conteos exportados con csv de la biblioteca estándar."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = ROOT / "data/raw/08-2026_Q2.csv"
if not source.exists():
    source = ROOT.parent / source.name
states, municipalities, stores, chains, products = set(), set(), set(), set(), set()
dates = Counter()
rows = 0
with source.open(encoding="utf-8-sig", newline="") as stream:
    for row in csv.DictReader(stream):
        rows += 1
        states.add(row["estado"])
        municipalities.add((row["estado"], row["municipio"]))
        stores.add(tuple(row[k] for k in
                         ["estado", "municipio", "cadena_comercial", "nombre_comercial", "direccion"]))
        chains.add(row["cadena_comercial"])
        products.add(row["producto"])
        dates[row["fecha_registro"]] += 1
manifest = json.loads((ROOT / "data/metadata/profeco_manifest.json").read_text(encoding="utf-8"))
s = manifest["resumen"]
assert s["registros"] == rows
assert s["estados"] == len({x for x in states if x.strip()})
assert s["municipios_estado_municipio"] == len(
    {x for x in municipalities if all(v.strip() for v in x)})
assert s["establecimientos_clave_observada"] == len(stores)
assert s["cadenas"] == len({x for x in chains if x.strip()})
assert s["productos_nombre"] == len({x for x in products if x.strip()})
with (ROOT / "data/processed/cobertura_diaria_profeco.csv").open(
        encoding="utf-8-sig", newline="") as stream:
    for row in csv.DictReader(stream):
        assert int(row["registros"]) == dates[row["fecha"].replace("-", "/")]
nb = json.loads((ROOT / "notebooks/00_exploracion_profeco.ipynb").read_text(encoding="utf-8"))
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        assert cell["execution_count"] is not None, "Notebook sin ejecutar"
        assert not any(o["output_type"] == "error" for o in cell["outputs"])
print("Verificación independiente correcta: conteos, fechas y notebook ejecutado sin errores.")
