"""Genera el notebook legible de fase 1. Ejecutarlo después con Jupyter."""
from pathlib import Path
import nbformat as nbf

root = Path(__file__).resolve().parent
for folder in ["notebooks", "data/metadata", "data/processed", "outputs/social",
               "outputs/charts", "docs", ".vscode"]:
    (root / folder).mkdir(parents=True, exist_ok=True)

cells = []
def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))
def code(text):
    cells.append(nbf.v4.new_code_cell(text))

md("""# 00 · Exploración de PROFECO

**Pregunta del proyecto:** ¿en qué localidades una canasta comparable cuesta menos
y se percibe mayor seguridad?

Esta primera fase describe el archivo completo. No construye una canasta ni compara
el costo de vida. No incorpora ENSU todavía. Se conserva el CSV original.
La fuente fue declarada por el usuario; falta verificar su procedencia oficial.
""")
code("""from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
assert (ROOT / "src/exploration.py").exists(), "Abrir desde la raíz del proyecto."
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.exploration import load_data, source_path, audit, export_results
pd.set_option("display.max_columns", 20)
path = source_path()
df = load_data(path)
print(f"Archivo: {path.name}; filas: {len(df):,}; columnas: {len(df.columns)}")
display(df.head(5))""")
md("""## 1. Definiciones y estructura

- Municipio: pareja exacta `estado` + `municipio`; todavía sin claves INEGI.
- Establecimiento: estado + municipio + cadena + nombre comercial + dirección.
  Es una aproximación operativa, no un identificador oficial.
- Producto: nombre distinto. Variante: producto + presentación + marca.
- Los campos se leen como texto para conservar el original, incluido `S/M`.
  Las conversiones numéricas y de fechas se realizan en variables auxiliares.
- No se eliminan duplicados ni anomalías. Los conteos incluyen registros originales.
""")
code("""display(pd.DataFrame({
    "tipo_lectura": df.dtypes.astype(str),
    "valores_distintos": df.nunique(),
}))
summary, tables = audit(df)
display(pd.Series(summary, name="valor").to_frame())""")
md("""## 2. Cobertura geográfica y temporal

La tabla completa de municipios se exporta a CSV. El porcentaje de días compara
días observados con días calendario entre el mínimo y el máximo globales:
**no mide incumplimiento de un calendario de levantamiento**. Un municipio
presente en PROFECO todavía no es un área urbana comparable con ENSU.
""")
code("""municipios = tables["cobertura_municipios_profeco"]
display(tables["estados_profeco"])
with pd.option_context("display.max_rows", None):
    display(municipios[["estado", "municipio", "registros", "establecimientos",
                        "productos", "fecha_inicio", "fecha_fin", "dias_observados"]])
display(municipios[["registros", "establecimientos", "productos",
                   "variantes_producto_presentacion_marca", "dias_observados"]].describe())
display(tables["cobertura_diaria_profeco"])""")
code("""from src import charts
daily = tables["cobertura_diaria_profeco"]
(ROOT / "outputs/charts").mkdir(parents=True, exist_ok=True)
charts.daily_bars(daily, ROOT / "outputs/charts/01_cobertura_temporal.png")
plt.show()""")
md("""## 3. Cobertura de productos

El denominador es el número de parejas estado–municipio con geografía completa.
Se exige producto, presentación y marca no vacíos para esta tabla.
La coincidencia literal de presentación no demuestra equivalencia de unidades.
Esta cobertura es descriptiva: no se han seleccionado alimentos ni una canasta.
""")
code("""display(tables["catalogos_categorias_profeco"])
productos = tables["cobertura_productos_profeco"]
display(productos.head(25))
display(productos["cobertura_municipios_pct"].describe())
print("Variantes presentes en todos los municipios:",
      int(productos.municipios.eq(summary["municipios_estado_municipio"]).sum()))""")
md("""## 4. Controles de calidad

Duplicados excedentes: repeticiones después de la primera fila idéntica en las
15 columnas. La comparación de precios extremos se pospone hasta definir
productos homogéneos; un IQR global mezclaría bienes diferentes.

La revisión textual de geografía elimina acentos, espacios redundantes y
diferencias de mayúsculas **solo para detectar posibles variantes**.
No fusiona municipios. Las coordenadas se revisan por rango mundial, sin
certificar que correspondan al municipio declarado.
""")
code("""display(tables["controles_calidad_profeco"])
display(tables["nulos_profeco"])
display(tables["variantes_geograficas_revision"])
display(tables["muestra_anomalias_profeco"].head(10))
assert municipios.registros.sum() + int(
    tables["controles_calidad_profeco"].set_index("control").loc[
        "geografia_incompleta", "registros"]) == len(df)
assert municipios[["estado", "municipio"]].duplicated().sum() == 0
assert productos.cobertura_municipios_pct.between(0, 100).all()
print("Reconciliaciones y controles estructurales: correctos.")""")
md("""## 5. Exportación y conclusiones

Se guardan tablas de cobertura, controles y metadatos con SHA-256.
La ruta local se registra por separado (`data/metadata/ruta_local.txt`).
No se crea todavía `auditoria_cobertura.csv`: esa validación requiere ENSU
y la cobertura de la canasta.
""")
code("""export_results(summary, tables, path)
controls = tables["controles_calidad_profeco"].set_index("control").registros
display(Markdown(
    f"Se observaron **{summary['registros']:,} registros**, "
    f"**{summary['municipios_estado_municipio']} municipios** en "
    f"**{summary['estados']} entidades**, entre "
    f"**{summary['fecha_inicio']}** y **{summary['fecha_fin']}**.\\n\\n"
    f"Hay **{summary['establecimientos_clave_observada']:,} claves de establecimiento** "
    f"y **{summary['productos_nombre']:,} nombres de producto**. "
    f"Los duplicados excedentes exactos son **{controls['duplicados_excedentes_exactos']:,}**.\\n\\n"
    "Estos resultados describen la muestra del archivo, no la oferta total de cada ciudad. "
    "La siguiente fase debe verificar el periodo y la geografía ENSU antes de unir fuentes."
))""")
nb = nbf.v4.new_notebook(cells=cells)
nb.metadata.kernelspec = {"display_name": "Python (mexico-costo-canasta)",
                         "language": "python", "name": "python3"}
nbf.write(nb, root / "notebooks/00_exploracion_profeco.ipynb")
