"""Homologación PROFECO (municipio) – ENSU (área urbana) con claves INEGI.

La composición municipal de cada área urbana ENSU se obtiene de los microdatos
oficiales (variables CD, CVE_ENT, CVE_MUN y factor FAC_SEL). No se une por parecido
de nombres de ciudad: el vínculo es municipio PROFECO -> clave municipal -> área ENSU.
"""
from pathlib import Path

import pandas as pd

from src.exploration import normalized_text

ROOT = Path(__file__).resolve().parents[1]
MICRODATOS = ROOT / "data/raw/ensu/microdatos/ENSU_CB_0626.csv"

# Nombre de entidad en PROFECO -> clave INEGI.
ENTIDAD_CLAVE = {
    "Aguascalientes": "01", "Baja California": "02", "Baja California Sur": "03",
    "Campeche": "04", "Coahuila": "05", "Colima": "06", "Chiapas": "07", "Chihuahua": "08",
    "Ciudad de México": "09", "Durango": "10", "Guanajuato": "11", "Guerrero": "12",
    "Hidalgo": "13", "Jalisco": "14", "Estado de México": "15", "Michoacán": "16",
    "Morelos": "17", "Nayarit": "18", "Nuevo León": "19", "Oaxaca": "20", "Puebla": "21",
    "Querétaro": "22", "Quintana Roo": "23", "San Luis Potosí": "24", "Sinaloa": "25",
    "Sonora": "26", "Tabasco": "27", "Tamaulipas": "28", "Tlaxcala": "29", "Veracruz": "30",
    "Yucatán": "31", "Zacatecas": "32",
}
# Escrituras PROFECO que difieren del nombre oficial INEGI. Revisadas una a una.
ALIAS_MUNICIPIO = {
    ("Ciudad de México", "Magdalena Contreras"): ("La Magdalena Contreras",
        "Nombre oficial de la alcaldía incluye «La»."),
    ("Estado de México", "Tlalnepantla"): ("Tlalnepantla de Baz", "Nombre oficial abreviado en PROFECO."),
    ("Jalisco", "Tlaquepaque"): ("San Pedro Tlaquepaque", "Nombre oficial abreviado en PROFECO."),
    ("Querétaro", "Santiago de Querétaro"): ("Querétaro",
        "PROFECO usa el nombre de la cabecera; el municipio oficial es Querétaro."),
    ("Estado de México", "Atizapán"): ("Atizapán de Zaragoza",
        "Existe un municipio Atizapán distinto; las coordenadas del único establecimiento "
        "(19.57, -99.25) se ubican en Atizapán de Zaragoza."),
}
UMBRAL_DIRECTA = 95.0
# 40 %: las coberturas observadas saltan de 49 % (Cuernavaca) a 27 % (Tlaxcala);
# además se exige que PROFECO tenga el municipio principal del área.
UMBRAL_APROXIMADA = 40.0


def ensu_composition(path=MICRODATOS):
    """Municipios de cada área ENSU y su peso en la población de 18+ (factor FAC_SEL)."""
    cols = ["CD", "NOM_CD", "CVE_ENT", "NOM_ENT", "CVE_MUN", "NOM_MUN", "FAC_SEL"]
    cb = pd.read_csv(path, encoding="latin-1", dtype=str, usecols=cols)
    cb["FAC_SEL"] = pd.to_numeric(cb.FAC_SEL)
    comp = cb.groupby(["CD", "NOM_CD", "CVE_ENT", "NOM_ENT", "CVE_MUN", "NOM_MUN"]).agg(
        personas_muestra=("FAC_SEL", "size"), poblacion_18_estimada=("FAC_SEL", "sum")).reset_index()
    comp["participacion_area_pct"] = (comp.poblacion_18_estimada
                                      / comp.groupby("CD").poblacion_18_estimada.transform("sum") * 100)
    comp["mun_norm"] = comp.NOM_MUN.map(normalized_text)
    assert not comp.duplicated(["CVE_ENT", "CVE_MUN"]).any(), "Municipio en más de un área ENSU"
    return comp


def attach_area_names(comp, ensu):
    """Asocia CD (microdatos) con el nombre del área en el tabulado (mismo levantamiento)."""
    tab = ensu.loc[ensu.estado_ensu.ne("Nacional"), ["area_urbana_ensu"]].drop_duplicates()
    tab["clave"] = tab.area_urbana_ensu.str.replace(r"\d+$", "", regex=True).map(normalized_text)
    cds = comp[["CD", "NOM_CD"]].drop_duplicates()
    cds["clave"] = cds.NOM_CD.map(normalized_text)
    merged = cds.merge(tab, on="clave", how="left", validate="one_to_one")
    assert merged.area_urbana_ensu.notna().all(), merged[merged.area_urbana_ensu.isna()]
    return comp.merge(merged[["CD", "area_urbana_ensu"]], on="CD")


def match(profeco_mun, comp):
    """Una fila por pareja estado–municipio PROFECO con su área ENSU, si existe."""
    rows = []
    for _, r in profeco_mun.iterrows():
        oficial, nota = ALIAS_MUNICIPIO.get((r.estado, r.municipio), (r.municipio, ""))
        cve_ent = ENTIDAD_CLAVE[r.estado]
        hit = comp[(comp.CVE_ENT == cve_ent) & (comp.mun_norm == normalized_text(oficial))]
        assert len(hit) <= 1
        base = {"estado": r.estado, "municipio_profeco": r.municipio, "cve_ent": cve_ent,
                "registros_profeco": r.registros, "establecimientos_profeco": r.establecimientos,
                "alias_aplicado": nota}
        if hit.empty:
            rows.append({**base, "cve_mun": pd.NA, "cd_ensu": pd.NA, "area_urbana_ensu": pd.NA,
                         "participacion_municipio_area_pct": pd.NA})
        else:
            h = hit.iloc[0]
            rows.append({**base, "cve_mun": h.CVE_MUN, "cd_ensu": h.CD,
                         "area_urbana_ensu": h.area_urbana_ensu,
                         "participacion_municipio_area_pct": h.participacion_area_pct})
    return pd.DataFrame(rows)


def classify(matched, comp):
    """Tipo de correspondencia según la parte del área ENSU cubierta por municipios PROFECO."""
    # Un municipio INEGI cuenta una sola vez aunque PROFECO lo escriba de dos formas.
    unique = matched.dropna(subset=["cd_ensu"]).drop_duplicates(["cd_ensu", "cve_mun"])
    cover = unique.groupby("cd_ensu").participacion_municipio_area_pct.sum().rename(
        "cobertura_profeco_area_pct")
    principal = comp.loc[comp.groupby("CD").participacion_area_pct.idxmax(), ["CD", "CVE_MUN"]]
    has_principal = unique.merge(principal, left_on=["cd_ensu", "cve_mun"],
                                 right_on=["CD", "CVE_MUN"]).cd_ensu
    n_mun = comp.groupby("CD").size().rename("municipios_area_ensu")
    out = matched.merge(cover, left_on="cd_ensu", right_index=True, how="left")
    out = out.merge(n_mun, left_on="cd_ensu", right_index=True, how="left")
    out["incluye_municipio_principal"] = out.cd_ensu.isin(has_principal)
    out["correspondencia"] = out.cd_ensu.notna()

    def kind(r):
        if not r.correspondencia:
            return "no comparable"
        if r.cobertura_profeco_area_pct >= UMBRAL_DIRECTA:
            return "directa"
        if r.cobertura_profeco_area_pct >= UMBRAL_APROXIMADA and r.incluye_municipio_principal:
            return "aproximada/documentada"
        return "no comparable"

    def note(r):
        parts = [r.alias_aplicado] if r.alias_aplicado else []
        if not r.correspondencia:
            parts.append("El municipio no forma parte de ningún área urbana de interés ENSU.")
        else:
            parts.append(
                f"Área ENSU de {int(r.municipios_area_ensu)} municipio(s); este municipio aporta "
                f"{r.participacion_municipio_area_pct:.1f}% de su población de 18+ y los municipios "
                f"PROFECO del área suman {r.cobertura_profeco_area_pct:.1f}%.")
            if r.cobertura_profeco_area_pct < UMBRAL_APROXIMADA:
                parts.append(f"Cobertura menor a {UMBRAL_APROXIMADA:.0f}%: los precios no "
                             "representarían al área urbana.")
            elif not r.incluye_municipio_principal:
                parts.append("PROFECO no cubre el municipio principal del área.")
        return " ".join(parts)

    out["tipo_correspondencia"] = out.apply(kind, axis=1)
    out["incluir"] = out.tipo_correspondencia.ne("no comparable")
    out["observaciones"] = out.apply(note, axis=1)
    cols = ["estado", "municipio_profeco", "cve_ent", "cve_mun", "cd_ensu", "area_urbana_ensu",
            "correspondencia", "tipo_correspondencia", "incluir",
            "participacion_municipio_area_pct", "cobertura_profeco_area_pct",
            "incluye_municipio_principal", "municipios_area_ensu", "registros_profeco", "establecimientos_profeco", "observaciones"]
    return out[cols].sort_values(["incluir", "area_urbana_ensu", "estado"],
                                 ascending=[False, True, True]).reset_index(drop=True)


def build_homologation(profeco_mun, ensu):
    comp = attach_area_names(ensu_composition(), ensu)
    return classify(match(profeco_mun, comp), comp), comp
