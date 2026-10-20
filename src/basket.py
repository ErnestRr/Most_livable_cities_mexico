"""Canasta comparable: reglas explícitas de producto, unidad y precio representativo."""
import numpy as np
import pandas as pd

from src.cleaning import CANAL, parse_quantity

# Cada producto normalizado admite solo presentaciones literalmente equivalentes.
# «cantidad» es la porción de la canasta en la unidad base (kg, l o pieza).
CANDIDATOS = [
    ("tortilla_maiz", "Tortilla de maíz", "Tortilla de Maíz", ["1 Kg. Granel"], "kg", 1),
    ("huevo_blanco", "Huevo blanco", "Huevo", ["Paquete C/12 Blanco", "Paquete C/18 Blanco"], "pieza", 12),
    ("leche_entera", "Leche UHT entera", "Leche Ultrapasteurizada",
     ["Caja 1 Lt. Entera", "Envase o Caja 1 Lt. Entera"], "l", 1),
    ("frijol_negro", "Frijol negro", "Frijol",
     ["Bolsa 900 Gr. Negro", "Bolsa 908 Gr. Negro", "Bolsa 1 Kg. Negro"], "kg", 1),
    ("frijol_pinto", "Frijol pinto", "Frijol",
     ["Bolsa 900 Gr. Pinto", "Bolsa 907 Gr. Pinto", "Bolsa 908 Gr. Pinto", "Bolsa 1 Kg. Pinto"], "kg", 1),
    ("arroz", "Arroz súper extra", "Arroz",
     ["Bolsa 900 Gr. Super Extra", "Bolsa 907 Gr. Super Extra", "Bolsa 1 Kg. Super Extra"], "kg", 1),
    ("azucar", "Azúcar estándar", "Azúcar", ["Bolsa Plástico 900 Gr. Estándar"], "kg", 1),
    ("aceite", "Aceite vegetal", "Aceite",
     ["Botella 1 Lt. Vegetal", "Botella 850 Ml. Vegetal", "Botella 800 Ml. Vegetal"], "l", 1),
    ("harina_maiz", "Harina de maíz", "Harina de Maíz", ["Paquete 1 Kg."], "kg", 1),
    ("lenteja", "Lenteja", "Lenteja", ["Bolsa 500 Gr."], "kg", 1),
    ("jitomate", "Jitomate saladet", "Jitomate",
     ["1 Kg. Granel. Saladette/huaje o Tomate Saladette/huaje"], "kg", 1),
    ("cebolla", "Cebolla blanca", "Cebolla", ["1 Kg. Granel. Blanca Sin Rabo"], "kg", 1),
    ("papa", "Papa blanca", "Papa", ["1 Kg. Granel. Alfa/blanca"], "kg", 1),
    ("chile_serrano", "Chile serrano", "Chile Fresco", ["1 Kg. Granel. Serrano"], "kg", 1),
    ("platano", "Plátano tabasco", "Plátano",
     ["1 Kg. Granel. Tabasco/chiapas/roatán/portalimón"], "kg", 1),
    ("manzana", "Manzana roja", "Manzana",
     ["1 Kg. Granel. Red Delicious/roja/roja Mediana/roja Americana"], "kg", 1),
    ("limon", "Limón con semilla", "Limón", ["1 Kg. Granel. Agrio con Semilla o Colima"], "kg", 1),
    ("pollo_entero", "Pollo entero", "Carne Pollo", ["1 Kg. Granel. Entero"], "kg", 1),
    ("res_milanesa", "Milanesa de res (bola)", "Carne Res",
     ["1 Kg. Granel. Milanesa de Bola o Auténtica de Bola o de Bola Corte Delgado o de Pulpa Bola"],
     "kg", 1),
    ("cerdo_chuleta", "Chuleta de cerdo", "Carne Cerdo",
     ["1 Kg. Granel. Chuleta o Chuleta Natural o Fresca/chuleta de Puerco Entrecortada o Lomo "
      "Deshuesado de Puerco o Chuleta Natural Lomo de Puerco"], "kg", 1),
    ("pan_caja", "Pan de caja blanco", "Pan de Caja", ["Paquete Grande 620 Gr. Rebanado Blanco"], "kg", 0.62),
    ("bolillo", "Bolillo", "Pan Blanco Bolillo", ["Pieza"], "pieza", 1),
]
CANDIDATOS = pd.DataFrame(CANDIDATOS, columns=["producto_normalizado", "nombre", "producto",
                                               "presentaciones", "unidad", "cantidad_canasta"])


def _rule_table():
    rows = [(r.producto_normalizado, r.producto, p, r.unidad)
            for r in CANDIDATOS.itertuples() for p in r.presentaciones]
    return pd.DataFrame(rows, columns=["producto_normalizado", "producto", "presentacion", "unidad"])


def select_observations(prepared, homologation):
    """Observaciones del canal autoservicio en áreas comparables y presentaciones admitidas."""
    areas = homologation.loc[homologation.incluir, ["estado", "municipio_profeco", "cd_ensu",
                                                    "area_urbana_ensu"]]
    base = prepared[prepared.giro.eq(CANAL) & prepared.precio_num.gt(0)]
    base = base.merge(areas, left_on=["estado", "municipio"],
                      right_on=["estado", "municipio_profeco"], validate="many_to_one")
    obs = base.merge(_rule_table(), on=["producto", "presentacion"], validate="many_to_one")
    qty = obs.presentacion.map(parse_quantity)
    obs["cantidad_presentacion"] = qty.str[0]
    obs["unidad_presentacion"] = qty.str[1]
    bad = obs.unidad_presentacion.ne(obs.unidad) | obs.cantidad_presentacion.isna()
    assert not bad.any(), obs.loc[bad, ["producto", "presentacion"]].drop_duplicates()
    obs["presentacion_normalizada"] = (obs.cantidad_presentacion.round(3).astype(str)
                                       + " " + obs.unidad)
    obs["precio_unitario"] = obs.precio_num / obs.cantidad_presentacion
    return flag_outliers(obs)


def flag_outliers(obs, k=1.5):
    """Marca extremos por IQR dentro de cada producto normalizado. No elimina filas."""
    g = obs.groupby("producto_normalizado").precio_unitario
    q1, q3 = g.transform(lambda s: s.quantile(.25)), g.transform(lambda s: s.quantile(.75))
    iqr = q3 - q1
    obs = obs.copy()
    obs["extremo_iqr"] = (obs.precio_unitario < q1 - k * iqr) | (obs.precio_unitario > q3 + k * iqr)
    return obs


def area_item_prices(obs, by_brand=False):
    """Mediana por establecimiento y luego mediana entre establecimientos del área.

    El paso intermedio evita que un establecimiento visitado muchas veces domine.
    """
    item = ["producto_normalizado"] + (["marca"] if by_brand else [])
    store = (obs.groupby(["cd_ensu", "area_urbana_ensu", *item, "establecimiento_id"])
             .agg(precio_est=("precio_unitario", "median"), obs=("precio_unitario", "size"))
             .reset_index())
    area = store.groupby(["cd_ensu", "area_urbana_ensu", *item]).agg(
        precio_mediana=("precio_est", "median"), precio_media=("precio_est", "mean"),
        establecimientos=("establecimiento_id", "nunique"), observaciones=("obs", "sum"),
    ).reset_index()
    return area


def coverage_matrix(area_prices, n_areas):
    m = area_prices.pivot_table(index="producto_normalizado", columns="area_urbana_ensu",
                                values="precio_mediana")
    cov = m.notna().sum(axis=1).rename("areas_con_precio").to_frame()
    cov["cobertura_pct"] = cov.areas_con_precio / n_areas * 100
    return m, cov.sort_values("cobertura_pct", ascending=False)


def basket_cost(area_prices, items, price_col="precio_mediana"):
    """Suma de precio unitario × cantidad para las áreas con TODOS los productos."""
    qty = CANDIDATOS.set_index("producto_normalizado").cantidad_canasta
    p = area_prices[area_prices.producto_normalizado.isin(items)].copy()
    p["costo_item"] = p[price_col] * p.producto_normalizado.map(qty)
    out = p.groupby(["cd_ensu", "area_urbana_ensu"]).agg(
        productos_disponibles=("producto_normalizado", "nunique"),
        costo_suma=("costo_item", "sum")).reset_index()
    out["productos_canasta"] = len(items)
    out["cobertura_pct"] = out.productos_disponibles / len(items) * 100
    # No se imputan faltantes: sin composición completa no hay costo comparable.
    out["costo_canasta"] = out.costo_suma.where(out.productos_disponibles.eq(len(items)))
    return out.drop(columns="costo_suma")


def dispersion(area_prices, items):
    """Coeficiente de variación y razón máx/mín del precio mediano entre áreas."""
    p = area_prices[area_prices.producto_normalizado.isin(items)]
    g = p.groupby("producto_normalizado").precio_mediana
    out = pd.DataFrame({"areas": g.size(), "mediana": g.median(), "minimo": g.min(),
                        "maximo": g.max(), "cv_pct": g.std() / g.mean() * 100})
    out["razon_max_min"] = out.maximo / out.minimo
    return out.sort_values("cv_pct", ascending=False)


def relative_prices(area_prices, items):
    """Precio de cada área relativo a la mediana nacional del producto (100 = mediana)."""
    p = area_prices[area_prices.producto_normalizado.isin(items)].copy()
    p["indice"] = p.precio_mediana / p.groupby("producto_normalizado").precio_mediana.transform(
        "median") * 100
    return p.pivot_table(index="area_urbana_ensu", columns="producto_normalizado", values="indice")


def select_items(area_prices, eligible_areas, candidates=None):
    """Retira, de forma iterativa, el producto cuya ausencia excluye más áreas elegibles.

    Se detiene cuando ningún producto, por sí solo, deja fuera un área que tendría
    completos los demás productos. Devuelve productos retenidos y bitácora.
    """
    items = list(CANDIDATOS.producto_normalizado if candidates is None else candidates)
    m = (area_prices[area_prices.area_urbana_ensu.isin(eligible_areas)]
         .pivot_table(index="area_urbana_ensu", columns="producto_normalizado",
                      values="precio_mediana").reindex(index=eligible_areas))
    log = []
    while True:
        present = m[items].notna()
        missing_one = present.sum(axis=1).eq(len(items) - 1)
        blockers = (~present[missing_one]).sum()
        blockers = blockers[blockers > 0]
        if blockers.empty:
            break
        worst = blockers.sort_values(ascending=False).index[0]
        log.append({"producto_retirado": worst, "areas_recuperadas": int(blockers[worst]),
                    "areas": ", ".join(present.index[missing_one & ~present[worst]])})
        items.remove(worst)
    complete = m[items].notna().all(axis=1)
    return items, pd.DataFrame(log), complete


def brand_option(obs, items):
    """Opción B: misma marca. Para cada producto se toma la marca con más áreas."""
    by_brand = area_item_prices(obs[obs.producto_normalizado.isin(items)], by_brand=True)
    reach = by_brand.groupby(["producto_normalizado", "marca"]).cd_ensu.nunique().rename("areas")
    chosen = reach.reset_index().sort_values("areas", ascending=False).drop_duplicates(
        "producto_normalizado")
    picked = by_brand.merge(chosen[["producto_normalizado", "marca"]])
    return picked, chosen.sort_values("producto_normalizado").reset_index(drop=True)


def bootstrap_basket(obs, items, areas, reps=500, seed=2026):
    """Intervalo bootstrap (percentiles 5–95) remuestreando establecimientos por área."""
    rng = np.random.default_rng(seed)
    data = obs[obs.producto_normalizado.isin(items) & obs.area_urbana_ensu.isin(areas)]
    store = (data.groupby(["area_urbana_ensu", "establecimiento_id", "producto_normalizado"])
             .precio_unitario.median().unstack())
    qty = CANDIDATOS.set_index("producto_normalizado").cantidad_canasta.reindex(items)
    rows = []
    for area, block in store.groupby(level=0):
        values = block[items].to_numpy(dtype=float, na_value=np.nan)
        n = len(values)
        draws = []
        for _ in range(reps):
            sample = values[rng.integers(0, n, n)]
            med = np.nanmedian(sample, axis=0)  # producto sin precio en la muestra -> nan
            draws.append(np.nan if np.isnan(med).any() else float(med @ qty.to_numpy()))
        draws = np.array(draws)
        ok = draws[~np.isnan(draws)]
        rows.append({"area_urbana_ensu": area, "costo_ic90_inf": np.percentile(ok, 5),
                     "costo_ic90_sup": np.percentile(ok, 95),
                     "bootstrap_validas_pct": len(ok) / reps * 100})
    return pd.DataFrame(rows)
