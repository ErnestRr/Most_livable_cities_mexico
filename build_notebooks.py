"""Genera los notebooks 01–05. Ejecutarlos después en orden (ver README)."""
from pathlib import Path
import nbformat as nbf

from src.geographic_matching import UMBRAL_APROXIMADA, UMBRAL_DIRECTA

root = Path(__file__).resolve().parent
KERNEL = {"display_name": "Python (mexico-costo-canasta)", "language": "python", "name": "python3"}
SETUP = """from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown

ROOT = Path.cwd()
if ROOT.name == "notebooks":
    ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PROC = ROOT / "data/processed"
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 200)
"""


def write(name, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1])
                for c in cells]
    nb.metadata.kernelspec = KERNEL
    nbf.write(nb, root / "notebooks" / name)


# --------------------------------------------------------------------------- 01
write("01_auditoria_cobertura.ipynb", [
    ("md", """# 01 · Auditoría de cobertura PROFECO – ENSU

Antes de cualquier gráfica, se decide qué municipios PROFECO pueden compararse con
un área urbana de la ENSU. Se revisan ambas fuentes por separado y luego se construye
`homologacion_geografica.csv`.

**Regla:** no se une por parecido de nombres de ciudad. Cada municipio PROFECO se
lleva a su clave INEGI y se busca en la composición municipal oficial de cada área
ENSU, obtenida de los microdatos del mismo levantamiento."""),
    ("code", SETUP + """from src.ensu import load_ensu, manifest, download, PERIODO
from src.geographic_matching import (ensu_composition, attach_area_names, match, classify,
                                     UMBRAL_DIRECTA, UMBRAL_APROXIMADA)
download()  # solo descarga si faltan los paquetes oficiales
profeco_mun = pd.read_csv(PROC / "cobertura_municipios_profeco.csv")
print(f"PROFECO: {len(profeco_mun)} parejas estado–municipio")"""),
    ("md", """## 1. PROFECO (resumen de la fase 1)

Se reutiliza la tabla de cobertura exportada en `00_exploracion_profeco.ipynb`."""),
    ("code", """display(profeco_mun[["registros", "establecimientos", "productos", "dias_observados"]].describe().round(1))
display(profeco_mun[["estado", "municipio", "registros", "establecimientos", "fecha_inicio", "fecha_fin"]]
        .sort_values("registros").head(10))"""),
    ("md", f"""## 2. ENSU

- **Periodo:** junio 2026, la publicación más reciente en el sitio de INEGI al 19-oct-2026
  (levantamiento del 22 de mayo al 12 de junio de 2026, según el comunicado de INEGI).
  La de septiembre 2026 aún no está publicada.
- **Indicador:** cuadro 1.7 de los tabulados básicos, «Población de 18 años y más por área
  urbana y características de percepción de seguridad pública». Se usa el porcentaje
  **«seguro»** que publica INEGI. No se calcula `100 − inseguro` porque la diferencia es
  «no sabe / no responde».
- Se conservan coeficiente de variación e intervalo de confianza al 90 % de los tabulados oficiales."""),
    ("code", """ensu = load_ensu()
areas = ensu[ensu.estado_ensu.ne("Nacional")]
print(f"Áreas urbanas en el cuadro: {areas.area_urbana_ensu.nunique()} · entidades: {areas.estado_ensu.nunique()}")
print("Nacional (seguro / inseguro):", ensu.loc[ensu.estado_ensu.eq('Nacional'), ['seguridad_pct', 'inseguridad_pct']].round(1).values.tolist())
dup = areas[areas.duplicated("area_urbana_ensu", keep=False)]
display(Markdown("Áreas que aparecen en dos entidades (interestatales):"))
display(dup[["estado_ensu", "area_urbana_ensu", "seguridad_pct"]])
areas = areas.drop_duplicates("area_urbana_ensu")
areas["precision"] = pd.cut(areas.cv_pct_seguro, [0, 15, 30, np.inf], right=False,
                            labels=["alta", "moderada", "baja"])
display(areas.precision.value_counts())
display(areas.sort_values("seguridad_pct")[["estado_ensu", "area_urbana_ensu", "seguridad_pct",
        "inseguridad_pct", "no_responde_pct", "cv_pct_seguro", "ic90_inf_seguro", "ic90_sup_seguro"]].round(1))"""),
    ("code", """# Control: seguro + inseguro + no responde = 100 y los intervalos contienen la estimación.
assert np.allclose(areas.seguridad_pct + areas.inseguridad_pct + areas.no_responde_pct, 100)
assert (areas.ic90_inf_seguro <= areas.seguridad_pct).all() and (areas.seguridad_pct <= areas.ic90_sup_seguro).all()
assert areas.no_responde_pct.between(-0.01, 3).all()
print("Controles ENSU correctos.")"""),
    ("md", """## 3. Composición municipal de las áreas ENSU

Los microdatos (`ENSU_CB_0626.csv`) contienen para cada persona entrevistada el área
(`CD`) y su municipio (`CVE_ENT`, `CVE_MUN`). Sumando el factor de expansión `FAC_SEL`
se estima qué parte de la población de 18+ de cada área vive en cada municipio.
Las notas del tabulado lo confirman para La Laguna, Los Cabos y Zacatecas. El catálogo
oficial de ciudades ENSU 2025 (PDF en `data/raw/ensu/`) se contrastó con estas claves:
coinciden salvo seis municipios periféricos pequeños, por cambios de muestra entre periodos."""),
    ("code", """comp = attach_area_names(ensu_composition(), ensu)
multi = comp.groupby("area_urbana_ensu").filter(lambda g: len(g) > 1)
print(f"{comp.CD.nunique()} áreas en microdatos; {multi.area_urbana_ensu.nunique()} incluyen más de un municipio")
display(multi.sort_values(["area_urbana_ensu", "participacion_area_pct"], ascending=[True, False])
        [["area_urbana_ensu", "NOM_ENT", "NOM_MUN", "personas_muestra", "participacion_area_pct"]].round(1).head(40))"""),
    ("md", f"""## 4. Homologación

Para cada área se suma la participación de los municipios que PROFECO observa.

| Tipo | Regla |
|---|---|
| directa | Los municipios PROFECO cubren ≥ {UMBRAL_DIRECTA:.0f} % de la población 18+ del área |
| aproximada/documentada | Cubren ≥ {UMBRAL_APROXIMADA:.0f} % e incluyen el municipio principal del área |
| no comparable | Menos de {UMBRAL_APROXIMADA:.0f} %, sin municipio principal o municipio fuera de ENSU |

El umbral de {UMBRAL_APROXIMADA:.0f} % no se fijó a priori: la distribución de coberturas
(gráfica siguiente) salta de 49 % (Cuernavaca) a 27 % (Tlaxcala). Por debajo de ese salto,
los precios PROFECO describirían una fracción minoritaria del área.

Las escrituras PROFECO que no coinciden con el nombre oficial se resolvieron con una tabla
explícita de alias (`ALIAS_MUNICIPIO`), revisada caso por caso y documentada en la columna
`observaciones`."""),
    ("code", """matched = match(profeco_mun, comp)
homolog = classify(matched, comp)
cov = homolog.dropna(subset=["cd_ensu"]).drop_duplicates("cd_ensu").sort_values("cobertura_profeco_area_pct")
from src import charts
charts.coverage_strip(cov, UMBRAL_APROXIMADA, UMBRAL_DIRECTA, ROOT / "outputs/charts/00a_cobertura_geografica.png")
plt.show()
display(homolog.tipo_correspondencia.value_counts())
display(homolog.drop(columns=["observaciones"]).round(1))"""),
    ("code", """display(homolog.loc[~homolog.incluir, ["estado", "municipio_profeco", "area_urbana_ensu",
        "cobertura_profeco_area_pct", "registros_profeco", "observaciones"]])
display(Markdown("Alias aplicados (nombre PROFECO distinto del oficial INEGI):"))
display(homolog.loc[homolog.observaciones.str.contains("oficial|coordenadas|cabecera"),
        ["estado", "municipio_profeco", "area_urbana_ensu", "observaciones"]])"""),
    ("code", """# Controles de la homologación
assert len(homolog) == len(profeco_mun)
assert homolog.groupby("cd_ensu").area_urbana_ensu.nunique().le(1).all()
assert homolog.cobertura_profeco_area_pct.dropna().le(100.01).all()
assert not homolog.loc[homolog.incluir, "cd_ensu"].isna().any()
homolog.to_csv(PROC / "homologacion_geografica.csv", index=False, encoding="utf-8-sig")
areas.to_csv(PROC / "ensu_percepcion_areas.csv", index=False, encoding="utf-8-sig")
comp.drop(columns="mun_norm").to_csv(PROC / "ensu_composicion_areas.csv", index=False, encoding="utf-8-sig")
(ROOT / "data/metadata/ensu_manifest.json").write_text(json.dumps({
    "fuente": "INEGI, Encuesta Nacional de Seguridad Pública Urbana (ENSU)", "periodo": PERIODO,
    "levantamiento": "22 de mayo al 12 de junio de 2026 (comunicado INEGI)",
    "indicador": "Cuadro 1.7: % de población 18+ que se siente segura en su ciudad",
    "archivos_tabulados": manifest(),
    "microdatos": "https://www.inegi.org.mx/contenidos/programas/ensu/microdatos/ensu_bd_2026_csv.zip",
    "catalogo_ciudades": "https://www.inegi.org.mx/contenidos/programas/ensu/doc/ensu2025_catalogo_ciudades_interes.pdf",
}, ensure_ascii=False, indent=2), encoding="utf-8")
n_areas = homolog.loc[homolog.incluir, "cd_ensu"].nunique()
display(Markdown(
    f"**Resultado:** {homolog.incluir.sum()} de {len(homolog)} municipios PROFECO corresponden a "
    f"**{n_areas} áreas urbanas ENSU** ({(homolog.tipo_correspondencia == 'directa').sum()} directas, "
    f"{(homolog.tipo_correspondencia == 'aproximada/documentada').sum()} aproximadas). "
    f"{(~homolog.incluir).sum()} municipios quedan fuera: seis del Estado de México fuera de las áreas ENSU "
    "y Solidaridad (Q. Roo) no pertenecen a un área ENSU; Tlaxcala y Apizaco cubren solo 27 % de la suya. "
    "La correspondencia geográfica es necesaria, no suficiente: falta verificar la cobertura de la canasta."))"""),
])

# --------------------------------------------------------------------------- 02
write("02_canasta_comparable.ipynb", [
    ("md", """# 02 · Canasta comparable

No se promedian todos los precios de cada ciudad: municipios distintos tienen productos,
marcas, presentaciones y cadenas distintos. Aquí se define una canasta fija y se
comprueba su cobertura.

Decisiones explícitas:

1. **Canal:** solo «Supermercado / Tienda de Autoservicio» (79 % de los registros de
   alimentos). Mercados y centrales de abasto tienen otra lógica de precio y cobertura muy desigual.
2. **Producto normalizado:** un producto + una lista cerrada de presentaciones literalmente
   equivalentes (por ejemplo, arroz súper extra de 900 g, 907 g o 1 kg). Las variantes
   (negro vs. pinto, entero vs. con vísceras) se tratan como productos distintos.
3. **Unidad:** la cantidad se extrae de la presentación y se calcula precio por kg, litro o pieza.
   Las presentaciones ambiguas («800 Ó 880 Gr.») no se usan.
4. **Ventana temporal:** todo el archivo disponible, del 16 al 31 de agosto de 2026
   (12 días con observaciones). Es la ventana completa disponible y no hay datos más
   cercanos a la ENSU de junio."""),
    ("code", SETUP + """from src.exploration import load_data
from src.cleaning import prepare, quality_flags, parse_quantity, CANAL
from src.basket import (CANDIDATOS, select_observations, area_item_prices, coverage_matrix,
                        select_items, brand_option, basket_cost)
prepared = prepare(load_data())
homolog = pd.read_csv(PROC / "homologacion_geografica.csv", dtype={"cd_ensu": str, "cve_mun": str, "cve_ent": str})
display(quality_flags(prepared).to_frame("valor"))
names = CANDIDATOS.set_index("producto_normalizado").nombre"""),
    ("md", "## 1. Candidatos y normalización de unidades"),
    ("code", """rules = CANDIDATOS.explode("presentaciones").rename(columns={"presentaciones": "presentacion"})
q = rules.presentacion.map(parse_quantity)
rules["cantidad"], rules["unidad_detectada"] = q.str[0], q.str[1]
display(rules[["producto_normalizado", "producto", "presentacion", "cantidad", "unidad_detectada",
               "unidad", "cantidad_canasta"]])
assert (rules.unidad == rules.unidad_detectada).all()
# Ejemplos de presentaciones que NO se normalizan por ambigüedad
for p in ["Paquete 800 Ó 880 Gr.", "Paquete 1 Kg. Ó 1.1 Kg.", "Manojo. Cambray"]:
    print(p, "->", parse_quantity(p))"""),
    ("code", """obs = select_observations(prepared, homolog)
print(f"Observaciones seleccionadas: {len(obs):,} · áreas con datos: {obs.area_urbana_ensu.nunique()} "
      f"· establecimientos: {obs.establecimiento_id.nunique()}")
display(obs.groupby("producto_normalizado").agg(observaciones=("precio_num", "size"),
        presentaciones=("presentacion", "nunique"), marcas=("marca", "nunique"),
        cadenas=("cadena_comercial", "nunique"), extremos_iqr=("extremo_iqr", "sum")))"""),
    ("md", """## 2. Precio representativo y valores extremos

Primero se toma la mediana de cada establecimiento (un supermercado visitado varios días
no pesa más) y después la mediana entre establecimientos del área.

Los extremos se marcan con IQR (1.5×) dentro de cada producto normalizado, **sin eliminarlos**.
La mediana es poco sensible a ellos; se comprueba comparando con la media."""),
    ("code", """area_prices = area_item_prices(obs)
area_prices_sin_ext = area_item_prices(obs[~obs.extremo_iqr])
cmp = area_prices.merge(area_prices_sin_ext, on=["cd_ensu", "area_urbana_ensu", "producto_normalizado"],
                        suffixes=("", "_sin_extremos"))
cmp["dif_mediana_pct"] = (cmp.precio_mediana_sin_extremos / cmp.precio_mediana - 1) * 100
cmp["dif_media_vs_mediana_pct"] = (cmp.precio_media / cmp.precio_mediana - 1) * 100
display(cmp[["dif_mediana_pct", "dif_media_vs_mediana_pct"]].describe().round(2))
ext = obs[obs.extremo_iqr].groupby("producto_normalizado").agg(
    extremos=("precio_unitario", "size"), minimo=("precio_unitario", "min"), maximo=("precio_unitario", "max"))
display(ext.round(2))
from src import charts
charts.price_boxplot(obs, names, ROOT / "outputs/charts/00b_distribucion_precios.png")
plt.show()"""),
    ("md", """## 3. Cobertura producto × área y mínimo de establecimientos

Una mediana de uno o dos supermercados es frágil. Se observa la distribución de
establecimientos de autoservicio por área antes de fijar un mínimo."""),
    ("code", """stores = obs.groupby("area_urbana_ensu").agg(establecimientos=("establecimiento_id", "nunique"),
                                              observaciones=("precio_unitario", "size"))
display(stores.establecimientos.value_counts().sort_index().to_frame("áreas"))
n_areas = homolog.loc[homolog.incluir, "cd_ensu"].nunique()
sin_autoservicio = sorted(set(homolog.loc[homolog.incluir, "area_urbana_ensu"]) - set(stores.index))
print("Áreas comparables sin supermercados PROFECO:", sin_autoservicio)
MIN_ESTABLECIMIENTOS = 3
eligible = sorted(stores[stores.establecimientos >= MIN_ESTABLECIMIENTOS].index)
print(f"Con ≥{MIN_ESTABLECIMIENTOS} establecimientos: {len(eligible)} de {len(stores)} áreas con autoservicio")
matrix, cov = coverage_matrix(area_prices, n_areas)
display(cov.assign(nombre=names).round(1))"""),
    ("md", """## 4. Selección de productos

Se parte de los 22 candidatos de consumo común y se exige **composición completa**: un área
sin un producto no recibe costo. Comparar sumas con productos faltantes abarataría
artificialmente a esas ciudades.

Regla iterativa: si un producto es el único faltante en una o más áreas elegibles, se
retira el que excluye más áreas. Se repite hasta que ningún producto, por sí solo, deje
fuera un área."""),
    ("code", """items, log, complete = select_items(area_prices, eligible)
display(log)
print(f"Canasta final: {len(items)} productos; áreas elegibles con composición completa: {complete.sum()} de {len(eligible)}")
display(complete[~complete])"""),
    ("md", """## 5. Marcas: opción A vs. opción B

- **A:** producto + presentación equivalente con cualquier marca y precio mediano.
- **B:** misma marca en todas las áreas (para cada producto, la marca presente en más áreas).

B controla la composición de marcas, pero pierde las áreas donde esa marca no se observó.
Se comparan cobertura y ordenamiento."""),
    ("code", """picked, chosen = brand_option(obs, items)
display(chosen)
A = basket_cost(area_prices, items).set_index("area_urbana_ensu").costo_canasta
Amedia = basket_cost(area_prices, items, "precio_media").set_index("area_urbana_ensu").costo_canasta
B = basket_cost(picked, items).set_index("area_urbana_ensu").costo_canasta
metodos = pd.DataFrame({"A_mediana": A, "A_media": Amedia, "B_misma_marca": B}).loc[eligible]
display(metodos.notna().sum().to_frame("áreas con costo"))
display(metodos.corr(method="spearman").round(3))
charts.methods_scatter(metodos, ROOT / "outputs/charts/00c_metodos_marca.png")
plt.show()"""),
    ("md", """**Decisión:** opción A con mediana. Ordena las áreas de forma parecida a B
(correlación de Spearman mostrada arriba), conserva más áreas y la mediana entre
establecimientos limita el efecto de marcas premium aisladas. B y la media se conservan
como pruebas de sensibilidad en el notebook 04."""),
    ("code", """definicion = CANDIDATOS.copy()
definicion["presentaciones"] = definicion.presentaciones.str.join(" | ")
definicion["incluido"] = definicion.producto_normalizado.isin(items)
definicion["motivo"] = np.where(definicion.incluido, "Cobertura completa en áreas elegibles",
    "Retirado: único faltante en " + definicion.producto_normalizado.map(log.set_index("producto_retirado").areas).fillna(""))
definicion = definicion.merge(cov, left_on="producto_normalizado", right_index=True)
definicion.to_csv(PROC / "canasta_definicion.csv", index=False, encoding="utf-8-sig")
area_prices.to_csv(PROC / "precios_area_producto.csv", index=False, encoding="utf-8-sig")
matrix.T.to_csv(PROC / "cobertura_canasta_matriz.csv", encoding="utf-8-sig")
metodos.reset_index().to_csv(PROC / "comparacion_metodos_canasta.csv", index=False, encoding="utf-8-sig")
log.to_csv(PROC / "seleccion_productos_bitacora.csv", index=False, encoding="utf-8-sig")
keep = ["cd_ensu", "area_urbana_ensu", "estado", "municipio", "establecimiento_id", "cadena_comercial",
        "producto_normalizado", "producto", "presentacion", "marca", "precio_num", "cantidad_presentacion",
        "unidad", "precio_unitario", "fecha", "lat", "lon", "extremo_iqr"]
obs[keep].to_csv(PROC / "observaciones_canasta.csv", index=False, encoding="utf-8-sig")
(ROOT / "data/metadata/canasta_parametros.json").write_text(json.dumps({
    "canal": CANAL, "min_establecimientos": MIN_ESTABLECIMIENTOS, "productos": items,
    "fecha_inicio": str(obs.fecha.min().date()), "fecha_fin": str(obs.fecha.max().date()),
    "metodo": "Opción A: mediana por establecimiento y mediana entre establecimientos",
}, ensure_ascii=False, indent=2), encoding="utf-8")
display(Markdown(f"**Canasta:** {len(items)} productos: " + ", ".join(names[i] for i in items) + "."))"""),
])

# --------------------------------------------------------------------------- 03
write("03_limpieza_transformacion.ipynb", [
    ("md", """# 03 · Criterios de inclusión y dataset analítico

Se aplican los criterios en orden y se registra para cada municipio PROFECO **por qué**
aparece o no en la gráfica.

| # | Criterio | Umbral y justificación |
|---|---|---|
| 1 | Correspondencia geográfica | directa o aproximada/documentada (notebook 01) |
| 2 | Establecimientos de autoservicio en el área | ≥ 3 (con 1–2 la mediana depende de una tienda) |
| 3 | Productos de la canasta | 100 % (no se imputan faltantes) |
| 4 | Productos con un solo establecimiento | ≤ 2 de 21 (≈10 %); la distribución se muestra abajo |
| 5 | Precisión ENSU del % «seguro» | CV < 30 % (precisión alta o moderada según INEGI) |

La ventana temporal (precios de agosto vs. ENSU de junio) es la misma para todas las
áreas, por eso se documenta como limitación y no como criterio por área."""),
    ("code", SETUP + """params = json.loads((ROOT / "data/metadata/canasta_parametros.json").read_text(encoding="utf-8"))
items = params["productos"]
homolog = pd.read_csv(PROC / "homologacion_geografica.csv", dtype={"cd_ensu": str, "cve_mun": str, "cve_ent": str})
prices = pd.read_csv(PROC / "precios_area_producto.csv", dtype={"cd_ensu": str})
obs = pd.read_csv(PROC / "observaciones_canasta.csv", dtype={"cd_ensu": str}, parse_dates=["fecha"])
ensu = pd.read_csv(PROC / "ensu_percepcion_areas.csv")
from src.basket import basket_cost
print(len(items), "productos;", obs.area_urbana_ensu.nunique(), "áreas con observaciones de autoservicio")"""),
    ("code", """basket = basket_cost(prices, items)
p = prices[prices.producto_normalizado.isin(items)]
single = p[p.establecimientos == 1].groupby("area_urbana_ensu").size().rename("productos_un_establecimiento")
area = (obs.groupby("area_urbana_ensu").agg(establecimientos=("establecimiento_id", "nunique"),
            observaciones_precio=("precio_unitario", "size"))
        .join(obs[obs.producto_normalizado.isin(items)].groupby("area_urbana_ensu").precio_unitario.size()
              .rename("observaciones_canasta"))
        .join(obs.drop_duplicates("establecimiento_id").groupby("area_urbana_ensu")[["lat", "lon"]].median())
        .join(single).fillna({"productos_un_establecimiento": 0}).reset_index())
area = area.merge(basket.drop(columns="cd_ensu"), on="area_urbana_ensu", how="left")
display(area.productos_un_establecimiento.value_counts().sort_index().to_frame("áreas"))"""),
    ("code", """MIN_EST, MAX_SINGLE, MAX_CV = params["min_establecimientos"], 2, 30
geo = homolog[homolog.incluir].groupby("area_urbana_ensu").agg(
    cd_ensu=("cd_ensu", "first"), estado=("estado", lambda s: " / ".join(sorted(set(s)))),
    municipios_profeco=("municipio_profeco", lambda s: ", ".join(s)),
    tipo_correspondencia=("tipo_correspondencia", "first"),
    cobertura_geografica_pct=("cobertura_profeco_area_pct", "first")).reset_index()
cand = geo.merge(area, on="area_urbana_ensu", how="left").merge(
    ensu.drop(columns=["estado_ensu", "region_ensu"]), on="area_urbana_ensu", how="left")

def motivo(r):
    if pd.isna(r.establecimientos):
        return "Sin establecimientos de autoservicio en PROFECO"
    if r.establecimientos < MIN_EST:
        return f"Menos de {MIN_EST} establecimientos de autoservicio ({int(r.establecimientos)})"
    if r.productos_disponibles < len(items):
        return f"Canasta incompleta ({int(r.productos_disponibles)} de {len(items)} productos)"
    if r.productos_un_establecimiento > MAX_SINGLE:
        return f"{int(r.productos_un_establecimiento)} productos con precio de un solo establecimiento"
    if pd.isna(r.seguridad_pct) or r.cv_pct_seguro >= MAX_CV:
        return "Estimación ENSU con precisión baja"
    return ""
cand["motivo_exclusion"] = cand.apply(motivo, axis=1)
cand["pasa_validacion"] = cand.motivo_exclusion.eq("")
display(cand.motivo_exclusion.replace("", "INCLUIDA").value_counts())
display(cand.loc[~cand.pasa_validacion, ["area_urbana_ensu", "municipios_profeco", "establecimientos",
        "productos_disponibles", "productos_un_establecimiento", "motivo_exclusion"]])"""),
    ("md", "## Tablas exigidas por la metodología"),
    ("code", """fi, ff = params["fecha_inicio"], params["fecha_fin"]
canasta = cand[["estado", "municipios_profeco", "area_urbana_ensu", "productos_disponibles", "productos_canasta",
                "cobertura_pct", "establecimientos", "costo_canasta"]].rename(columns={"municipios_profeco": "municipio"})
canasta = canasta.assign(fecha_inicio=fi, fecha_fin=ff).sort_values("costo_canasta")
canasta.to_csv(PROC / "canasta_municipio.csv", index=False, encoding="utf-8-sig")

aud = homolog.merge(cand[["area_urbana_ensu", "establecimientos", "cobertura_pct", "seguridad_pct",
                          "pasa_validacion", "motivo_exclusion"]], on="area_urbana_ensu", how="left")
aud["motivo_exclusion"] = np.where(~aud.incluir, "Sin correspondencia geográfica válida: " + aud.observaciones,
                                   aud.motivo_exclusion)
aud["pasa_validacion"] = aud.incluir & aud.pasa_validacion.fillna(False).astype(bool)
auditoria = aud.rename(columns={"municipio_profeco": "municipio", "establecimientos": "establecimientos_autoservicio_area",
    "cobertura_pct": "cobertura_canasta_pct", "area_urbana_ensu": "area_ensu", "seguridad_pct": "dato_ensu"})[
    ["municipio", "estado", "registros_profeco", "establecimientos_profeco", "establecimientos_autoservicio_area",
     "cobertura_canasta_pct", "area_ensu", "tipo_correspondencia", "dato_ensu", "pasa_validacion", "motivo_exclusion"]]
auditoria.to_csv(PROC / "auditoria_cobertura.csv", index=False, encoding="utf-8-sig")
display(auditoria.pasa_validacion.value_counts())

final = cand[cand.pasa_validacion].assign(
    fecha_inicio_precios=fi, fecha_fin_precios=ff, periodo_ensu="junio 2026",
    precision_ensu=lambda d: np.where(d.cv_pct_seguro < 15, "alta", "moderada"))
final = final.rename(columns={"municipios_profeco": "municipio", "lat": "latitud", "lon": "longitud"})[
    ["estado", "municipio", "area_urbana_ensu", "cd_ensu", "tipo_correspondencia", "cobertura_geografica_pct",
     "costo_canasta", "seguridad_pct", "inseguridad_pct", "no_responde_pct", "cv_pct_seguro", "ic90_inf_seguro",
     "ic90_sup_seguro", "precision_ensu", "productos_canasta", "cobertura_pct", "establecimientos",
     "observaciones_precio", "observaciones_canasta", "productos_un_establecimiento", "fecha_inicio_precios",
     "fecha_fin_precios", "periodo_ensu", "latitud", "longitud"]].sort_values("costo_canasta")
final.to_csv(PROC / "dataset_final.csv", index=False, encoding="utf-8-sig")
display(final.round(1))"""),
    ("code", """# Controles del dataset final
assert final.area_urbana_ensu.is_unique and final.cd_ensu.is_unique
assert final.cobertura_pct.eq(100).all() and final.costo_canasta.notna().all()
assert final.establecimientos.ge(MIN_EST).all() and final.cv_pct_seguro.lt(MAX_CV).all()
assert final.seguridad_pct.between(0, 100).all() and final.latitud.between(14, 33).all()
assert auditoria.pasa_validacion.sum() == homolog.merge(final[["area_urbana_ensu"]]).shape[0]
display(Markdown(f"**Dataset final:** {len(final)} áreas urbanas comparables, de "
    f"{homolog.loc[homolog.incluir, 'cd_ensu'].nunique()} con correspondencia geográfica. "
    f"Precios del {fi} al {ff}; ENSU junio 2026. "
    f"{(final.precision_ensu == 'moderada').sum()} áreas tienen precisión ENSU moderada (CV 15–30 %)."))"""),
])

# --------------------------------------------------------------------------- 04
write("04_analisis.ipynb", [
    ("md", """# 04 · Análisis

Cuadrantes con las **medianas** del grupo como cortes, intervalos de incertidumbre para
ambos ejes, dispersión de precios por producto y comparación de cadenas. Ninguna
relación se interpreta como causal."""),
    ("code", SETUP + """from src.basket import bootstrap_basket, dispersion, relative_prices, CANDIDATOS
import warnings
params = json.loads((ROOT / "data/metadata/canasta_parametros.json").read_text(encoding="utf-8"))
items = params["productos"]
names = CANDIDATOS.set_index("producto_normalizado").nombre
final = pd.read_csv(PROC / "dataset_final.csv", dtype={"cd_ensu": str})
prices = pd.read_csv(PROC / "precios_area_producto.csv", dtype={"cd_ensu": str})
obs = pd.read_csv(PROC / "observaciones_canasta.csv", dtype={"cd_ensu": str})
metodos = pd.read_csv(PROC / "comparacion_metodos_canasta.csv")
areas = final.area_urbana_ensu.tolist()
print(len(final), "áreas")"""),
    ("md", """## 1. Incertidumbre del costo

Bootstrap con 1,000 réplicas, remuestreando establecimientos dentro de cada área, que es
la fuente principal de variación (≈5 supermercados por área)."""),
    ("code", """with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    boot = bootstrap_basket(obs, items, areas, reps=1000)
res = final.merge(boot, on="area_urbana_ensu")
res["ancho_ic_pct"] = (res.costo_ic90_sup - res.costo_ic90_inf) / res.costo_canasta * 100
rango = res.costo_canasta.max() / res.costo_canasta.min() - 1
print(f"Rango del costo: ${res.costo_canasta.min():,.0f} – ${res.costo_canasta.max():,.0f} ({rango:.1%})")
print(f"Ancho mediano del IC90 por área: {res.ancho_ic_pct.median():.1f}% del costo")
display(res[["costo_canasta", "ancho_ic_pct", "seguridad_pct"]].describe().round(1))"""),
    ("md", "## 2. Cuadrantes"),
    ("code", """x_med, y_med = res.costo_canasta.median(), res.seguridad_pct.median()
barato, seguro = res.costo_canasta <= x_med, res.seguridad_pct >= y_med
res["cuadrante"] = np.select([barato & seguro, ~barato & seguro, barato & ~seguro], [1, 2, 3], 4)
res["cuadrante_nombre"] = res.cuadrante.map({1: "Menor costo + mayor seguridad", 2: "Mayor costo + mayor seguridad",
                                             3: "Menor costo + menor seguridad", 4: "Mayor costo + menor seguridad"})
# Robusto: los IC90 de ambos ejes quedan del mismo lado de su mediana.
x_ok = np.where(barato, res.costo_ic90_sup <= x_med, res.costo_ic90_inf > x_med)
y_ok = np.where(seguro, res.ic90_inf_seguro >= y_med, res.ic90_sup_seguro < y_med)
res["cuadrante_robusto"] = x_ok & y_ok
res["eje_costo_robusto"], res["eje_seguridad_robusto"] = x_ok, y_ok
print(f"Mediana costo ${x_med:,.2f} · mediana seguridad {y_med:.1f}%")
display(pd.crosstab(res.cuadrante_nombre, res.cuadrante_robusto, margins=True))
print("Ejes robustos — costo:", res.eje_costo_robusto.sum(), "· seguridad:", res.eje_seguridad_robusto.sum())
for q in [1, 2, 3, 4]:
    d = res[res.cuadrante == q].sort_values("costo_canasta")
    display(Markdown(f"**{d.cuadrante_nombre.iloc[0]}** ({len(d)}): " +
        ", ".join(f"{a.rstrip('0123456789')}{'*' if r else ''}" for a, r in zip(d.area_urbana_ensu, d.cuadrante_robusto))))
display(Markdown("\\\\* cuadrante robusto en ambos ejes."))"""),
    ("code", """rho = res[["costo_canasta", "seguridad_pct"]].corr(method="spearman").iloc[0, 1]
pear = res[["costo_canasta", "seguridad_pct"]].corr().iloc[0, 1]
# Permutación: ¿qué tan frecuente es un |rho| así si no hubiera relación?
rng = np.random.default_rng(1)
xr, yr = res.costo_canasta.rank().to_numpy(), res.seguridad_pct.rank().to_numpy()
perm = np.array([np.corrcoef(xr, rng.permutation(yr))[0, 1] for _ in range(5000)])
p_perm = np.mean(np.abs(perm) >= abs(rho))
print(f"Spearman {rho:+.3f} · Pearson {pear:+.3f} · p (permutación) {p_perm:.2f}")"""),
    ("md", """## 3. Sensibilidad

¿Cambia el cuadrante de costo si se usa la media o una sola marca por producto?"""),
    ("code", """sens = res[["area_urbana_ensu", "costo_canasta"]].merge(metodos, on="area_urbana_ensu", how="left")
for col in ["A_media", "B_misma_marca"]:
    ok = sens[col].notna()
    same = ((sens.loc[ok, col] <= sens.loc[ok, col].median()) == (sens.loc[ok, "costo_canasta"] <= x_med)).mean()
    print(f"{col}: {ok.sum()} áreas; misma mitad de costo que A-mediana en {same:.0%}; "
          f"Spearman {sens.loc[ok, ['costo_canasta', col]].corr(method='spearman').iloc[0, 1]:.2f}")
sin_moderada = res[res.precision_ensu == "alta"]
print(f"Solo precisión ENSU alta ({len(sin_moderada)} áreas): Spearman "
      f"{sin_moderada[['costo_canasta', 'seguridad_pct']].corr(method='spearman').iloc[0, 1]:+.3f}")"""),
    ("md", "## 4. ¿Qué productos explican las diferencias?"),
    ("code", """p = prices[prices.area_urbana_ensu.isin(areas) & prices.producto_normalizado.isin(items)]
disp = dispersion(p, items)
qty = CANDIDATOS.set_index("producto_normalizado").cantidad_canasta
p = p.assign(costo_item=p.precio_mediana * p.producto_normalizado.map(qty))
share = p.groupby("producto_normalizado").costo_item.median() / p.groupby("area_urbana_ensu").costo_item.sum().median() * 100
contrib = p.groupby("producto_normalizado").costo_item.std() ** 2
disp["peso_en_canasta_pct"] = share
disp["contribucion_varianza_pct"] = contrib / contrib.sum() * 100  # aproximada: ignora covarianzas
disp.insert(0, "nombre", names.reindex(disp.index))
display(disp.round(2))
rel = relative_prices(p, items)"""),
    ("md", """## 5. Comparación de cadenas

Para comparar cadenas con justicia se compara **el mismo producto en la misma área**:
índice = precio del establecimiento / mediana del producto en el área × 100. Solo
cadenas presentes en al menos 5 áreas del dataset final."""),
    ("code", """st = (obs[obs.area_urbana_ensu.isin(areas) & obs.producto_normalizado.isin(items)]
      .groupby(["area_urbana_ensu", "cadena_comercial", "establecimiento_id", "producto_normalizado"])
      .precio_unitario.median().reset_index())
st["indice"] = st.precio_unitario / st.groupby(["area_urbana_ensu", "producto_normalizado"]).precio_unitario.transform("median") * 100
chains = st.groupby("cadena_comercial").agg(indice_medio=("indice", "mean"), indice_mediano=("indice", "median"), areas=("area_urbana_ensu", "nunique"),
                                            establecimientos=("establecimiento_id", "nunique"), precios=("indice", "size"))
chains = chains[chains.areas >= 5].sort_values("indice_medio").reset_index()
# La mediana del índice suele ser 100 porque muchas tiendas comparten precio exacto;
# la media sí refleja diferencias sistemáticas.
chains["pct_precios_menores_a_mediana"] = chains.cadena_comercial.map(
    st.assign(menor=st.indice < 100).groupby("cadena_comercial").menor.mean() * 100)
display(chains.round(1))"""),
    ("code", """res.to_csv(PROC / "resultados_analisis.csv", index=False, encoding="utf-8-sig")
disp.reset_index().to_csv(PROC / "dispersion_productos.csv", index=False, encoding="utf-8-sig")
rel.to_csv(PROC / "precios_relativos_area_producto.csv", encoding="utf-8-sig")
chains.to_csv(PROC / "comparacion_cadenas.csv", index=False, encoding="utf-8-sig")
meta = {"areas": len(res), "productos": len(items), "mediana_costo": round(float(x_med), 2),
        "mediana_seguridad": round(float(y_med), 2), "rango_costo_pct": round(rango * 100, 1),
        "spearman": round(float(rho), 3), "p_permutacion": round(float(p_perm), 3),
        "periodo_precios": "16–31 ago 2026", "periodo_ensu": "junio 2026",
        "fecha_inicio": params["fecha_inicio"], "fecha_fin": params["fecha_fin"]}
(ROOT / "data/metadata/resultados_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
top = disp.index[0]
q1 = res[(res.cuadrante == 1) & res.cuadrante_robusto].area_urbana_ensu.str.rstrip("0123456789").tolist()
q4 = res[(res.cuadrante == 4) & res.cuadrante_robusto].area_urbana_ensu.str.rstrip("0123456789").tolist()
display(Markdown(f\"\"\"**Hallazgos**

- La canasta de {len(items)} productos cuesta entre **${res.costo_canasta.min():,.0f}** y **${res.costo_canasta.max():,.0f}**:
  una diferencia de {rango:.0%}. El intervalo de 90 % de cada área mide en mediana {res.ancho_ic_pct.median():.0f}% del costo,
  así que buena parte del ordenamiento por costo no es concluyente.
- La seguridad percibida varía mucho más: de {res.seguridad_pct.min():.0f}% a {res.seguridad_pct.max():.0f}%.
- No se observa relación entre ambas dimensiones (Spearman {rho:+.2f}; p por permutación {p_perm:.2f}).
- Cuadrante robusto «menor costo + mayor seguridad»: {', '.join(q1) or 'ninguna'}.
  Cuadrante robusto «mayor costo + menor seguridad»: {', '.join(q4) or 'ninguna'}.
- El producto con mayor dispersión geográfica es **{names[top]}** (CV {disp.cv_pct.iloc[0]:.0f}%).
\"\"\"))"""),
])

# --------------------------------------------------------------------------- 05
write("05_visualizaciones.ipynb", [
    ("md", """# 05 · Visualizaciones

Todas las figuras siguen la misma plantilla editorial propia (`src/charts.py`):

- fondo azul pizarra; título **alineado a la izquierda** con barra de acento y subtítulo con periodo y universo;
- ejes abiertos (izquierdo e inferior), **líneas finas** y cuadrícula tenue;
- **leyenda** y recuadros **«¿Cómo leer?»** o **«Datos clave»** que explican cada indicador en lenguaje llano;
- **pie** con fuente y un dato agregado (mediana, total o rango).

Los mapas añaden océano, países vecinos (Natural Earth), contornos estatales y **barra de
color** con su unidad. Paleta validada para daltonismo y contraste sobre el fondo oscuro:
verde azulado `#1fa596` y coral `#e5683f`; gris para lo no concluyente."""),
    ("code", SETUP + """from datetime import date
from src import charts, geo
from src import visualization as viz
from src.basket import CANDIDATOS
from src.charts import b, n
names = CANDIDATOS.set_index("producto_normalizado").nombre.to_dict()
res = pd.read_csv(PROC / "resultados_analisis.csv", dtype={"cd_ensu": str})
meta = json.loads((ROOT / "data/metadata/resultados_meta.json").read_text(encoding="utf-8"))
meta["archivo_profeco"] = json.loads((ROOT / "data/metadata/profeco_manifest.json").read_text(encoding="utf-8"))["archivo"]
meta["generado"] = date.today().isoformat()
items = json.loads((ROOT / "data/metadata/canasta_parametros.json").read_text(encoding="utf-8"))["productos"]
SOCIAL, CHARTS = ROOT / "outputs/social", ROOT / "outputs/charts"
SOCIAL.mkdir(parents=True, exist_ok=True); CHARTS.mkdir(parents=True, exist_ok=True)"""),
    ("md", "## 1. Gráfica principal: costo vs. seguridad (LinkedIn 1080×1350 y X 1600×900, PNG 200 DPI + SVG)"),
    ("code", """charts.scatter_quadrants(res, meta, SOCIAL / "grafica_principal_1600x900.png", (1600, 900)); plt.show()"""),
    ("code", """charts.scatter_quadrants(res, meta, SOCIAL / "grafica_principal_1080x1350.png", (1080, 1350)); plt.show()
from PIL import Image
for f in ["grafica_principal_1080x1350.png", "grafica_principal_1600x900.png"]:
    print(f, Image.open(SOCIAL / f).size)"""),
    ("md", "## 2. Rankings con intervalos de confianza al 90 %"),
    ("code", """charts.ranking_cost(res, CHARTS / "02_ranking_costo_canasta.png"); plt.show()"""),
    ("code", """charts.ranking_security(res, CHARTS / "03_ranking_seguridad.png"); plt.show()"""),
    ("md", "## 3. Productos: dispersión entre ciudades y distribución por tienda"),
    ("code", """disp = pd.read_csv(PROC / "dispersion_productos.csv", index_col=0)
charts.dispersion_lollipop(disp, names, CHARTS / "04_dispersion_productos.png"); plt.show()"""),
    ("code", """obs = pd.read_csv(PROC / "observaciones_canasta.csv")
prices = pd.read_csv(PROC / "precios_area_producto.csv", dtype={"cd_ensu": str})
obs = obs[obs.area_urbana_ensu.isin(res.area_urbana_ensu) & obs.producto_normalizado.isin(items)]
store = obs.groupby(["area_urbana_ensu", "establecimiento_id", "producto_normalizado"]).precio_unitario.median().reset_index()
ref = prices[prices.area_urbana_ensu.isin(res.area_urbana_ensu)].groupby("producto_normalizado").precio_mediana.median()
store["indice"] = store.precio_unitario / store.producto_normalizado.map(ref) * 100
charts.store_spread(store, names, disp.sort_values("cv_pct").index.tolist(), CHARTS / "05_distribucion_precios_tienda.png"); plt.show()"""),
    ("code", """rel = pd.read_csv(PROC / "precios_relativos_area_producto.csv", index_col=0)
charts.relative_heatmap(rel, names, res.sort_values("costo_canasta").area_urbana_ensu, CHARTS / "06_heatmap_precio_relativo.png"); plt.show()"""),
    ("md", "## 4. Cadenas y tabla de resultados"),
    ("code", """charts.chains_lollipop(pd.read_csv(PROC / "comparacion_cadenas.csv"), CHARTS / "07_comparacion_cadenas.png"); plt.show()"""),
    ("code", """charts.ranking_table(res, CHARTS / "08_tabla_ranking.png"); plt.show()"""),
    ("md", """## 5. Mapas de calor municipales

Límites: INEGI, Marco Geoestadístico 2024 (`00mun`, `00ent`), simplificados con `src/geo.py`.
Países vecinos: Natural Earth 1:50m. **Cada municipio toma el valor de su área urbana ENSU**
(costo y seguridad se estiman por área, no por municipio); en negro, municipios sin dato.
Recuadros: Valle de México, Guadalajara y Monterrey."""),
    ("code", """if not (ROOT / "data/processed/geo/municipios_lcc.json").exists():
    geo.build()
mun, ent = geo.load_projected("municipios"), geo.load_projected("entidades")
neighbors = charts.load_neighbors()
comp = pd.read_csv(PROC / "ensu_composicion_areas.csv", dtype={"CVE_ENT": str, "CVE_MUN": str, "CD": str})
comp["CVEGEO"] = comp.CVE_ENT + comp.CVE_MUN
ensu = pd.read_csv(PROC / "ensu_percepcion_areas.csv")
seg = comp.merge(ensu[["area_urbana_ensu", "seguridad_pct"]], on="area_urbana_ensu")
cost = comp.merge(res[["area_urbana_ensu", "costo_canasta"]], on="area_urbana_ensu")
assert seg.CVEGEO.isin({f["props"]["CVEGEO"] for f in mun}).all()
print(f"Seguridad: {len(seg)} municipios en {seg.area_urbana_ensu.nunique()} áreas; "
      f"canasta: {len(cost)} municipios en {cost.area_urbana_ensu.nunique()} áreas")
mun_by_id = {f["props"]["CVEGEO"]: f for f in mun}

def centroid(cvegeo):
    return max(mun_by_id[cvegeo]["rings"], key=len).mean(axis=0)

def principal(table):
    return table.sort_values("participacion_area_pct").drop_duplicates("area_urbana_ensu", keep="last")

def label_points(table, col, k=3):
    p = principal(table)
    pick = pd.concat([p.nsmallest(k, col), p.nlargest(k, col)])
    return [(tuple(centroid(r.CVEGEO) + [12000, 0]), viz.short_name(r.area_urbana_ensu)) for r in pick.itertuples()]

ZONAS = {"Valle de México": lambda t: t.CVE_ENT.isin(["09", "15"]) & ~t.area_urbana_ensu.eq("Toluca de Lerdo"),
         "Guadalajara": lambda t: t.CVE_ENT.eq("14") & ~t.area_urbana_ensu.eq("Puerto Vallarta"),
         "Monterrey": lambda t: t.CVE_ENT.eq("19")}

def insets(table):
    return {name: (comp[rule(comp)].CVEGEO.tolist(),
                   [(*centroid(r.CVEGEO), viz.short_name(r.area_urbana_ensu)) for r in principal(table[rule(table)]).itertuples()])
            for name, rule in ZONAS.items()}"""),
    ("code", """med = res.costo_canasta.median()
charts.municipal_map(
    mun, ent, neighbors, dict(zip(cost.CVEGEO, cost.costo_canasta)), res.costo_canasta,
    [n("Costo de la "), b("canasta comparable"), n(" en México por municipio (agosto de 2026)")],
    "pesos por canasta", "Pesos por canasta de 21 productos", lambda v: f"${v:,.0f}",
    [n("Fuente: PROFECO (16–31 ago 2026); INEGI, Marco Geoestadístico 2024 y ENSU. Mediana: "), b(f"${med:,.0f}"),
     n(" por canasta en "), b(f"{len(res)}"), n(" áreas urbanas ("), b(f"{len(cost)}"), n(" municipios).")],
    CHARTS / "09_mapa_municipal_costo.png", insets(cost), labels=label_points(cost, "costo_canasta"),
    n_mun=len(cost), note_lines=["Negro: municipio sin dato.", "Cada municipio toma el valor", "de su área urbana ENSU."]); plt.show()"""),
    ("code", """areas_seg = principal(seg)
charts.municipal_map(
    mun, ent, neighbors, dict(zip(seg.CVEGEO, seg.seguridad_pct)), areas_seg.seguridad_pct,
    [n("Población que se siente "), b("segura"), n(" en su ciudad, por municipio (junio de 2026)")],
    "% de población de 18+", "% de la población de 18+ que se siente segura", lambda v: f"{v:.1f}%",
    [n("Fuente: INEGI, ENSU (jun 2026) y Marco Geoestadístico 2024. Nacional (áreas urbanas): "), b("40.0%"),
     n(" se siente seguro; "), b(f"{areas_seg.area_urbana_ensu.nunique()}"), n(" áreas, "), b(f"{len(seg)}"), n(" municipios.")],
    CHARTS / "10_mapa_municipal_seguridad.png", insets(seg), labels=label_points(seg, "seguridad_pct"),
    n_mun=len(seg), note_lines=["Negro: municipio fuera de las", "áreas urbanas ENSU.", "Valor del área urbana ENSU."]); plt.show()"""),
    ("md", """## 6. Página HTML (opcional)

Reporte web en formato de tablero (`docs/index.html`): indicadores, tarjetas y gráficas Plotly interactivas."""),
    ("code", """ent_coarse = [{"props": f["props"], "rings": [r for r in (geo._snap(x, 2500) for x in f["rings"]) if len(r) >= 4]} for f in ent]
geo_html = {"entidades": geo.to_geojson(ent_coarse)}
for key, table, col in [("mapa_costo", cost, "costo_canasta"), ("mapa_seguridad", seg, "seguridad_pct")]:
    feats = [{"props": mun_by_id[c]["props"], "rings": [geo._snap(r, 600) for r in mun_by_id[c]["rings"]]} for c in table.CVEGEO]
    geo_html[key] = {"geojson": geo.to_geojson(feats), "ids": table.CVEGEO.tolist(), "z": table[col].round(2).tolist(),
                     "text": [[mun_by_id[c]["props"]["NOMGEO"], a.rstrip("0123456789")] for c, a in zip(table.CVEGEO, table.area_urbana_ensu)]}
qty = CANDIDATOS.set_index("producto_normalizado").cantidad_canasta
pp = prices[prices.area_urbana_ensu.isin(res.area_urbana_ensu) & prices.producto_normalizado.isin(items)].copy()
pp["precio_mediana"] = pp.precio_mediana * pp.producto_normalizado.map(qty)
out = viz.interactive_html(res, pp, names, meta, geo_html, ROOT / "docs/index.html", disp=disp,
                           chains=pd.read_csv(PROC / "comparacion_cadenas.csv"), store=store)
print(out, f"{out.stat().st_size / 1e6:.1f} MB")"""),
])
print("Notebooks 01–05 generados.")
