"""Página interactiva autocontenida (Plotly) y utilidades compartidas con src/charts.py.

Estilo: fondo oscuro, rejilla visible y tenue, títulos con palabras clave en negrita,
valores rotulados sobre las marcas, recuadros de notas/estadísticas y pie con fuente.
Paleta validada con dataviz/validate_palette.js sobre el fondo #161b24 (modo oscuro,
todos los pares): cian #1fa596 y naranja #e5683f.
"""
from pathlib import Path
import json
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
FIRMA = ""  # p. ej. "@tu_usuario"; vacío = sin firma en el pie

BG, PANEL, GRID, AXIS = "#161b24", "#161b24", "#283041", "#5b6578"
TEXT, TEXT2, MUTED = "#f3f5f4", "#c8d0cc", "#8d9993"
CYAN, ORANGE, NEUTRAL, GOLD = "#1fa596", "#e5683f", "#7d8697", "#c9a24a"
NODATA, BORDER = "#1f2633", "#161b24"
Q_COLOR = {1: CYAN, 2: "#8592ad", 3: "#a8946c", 4: ORANGE}
Q_LABEL = {1: "Menor costo + mayor seguridad", 2: "Mayor costo + mayor seguridad",
           3: "Menor costo + menor seguridad", 4: "Mayor costo + menor seguridad"}
# Secuencial de una familia (azul noche -> verde azulado -> menta), luminosidad creciente.
SEQ = LinearSegmentedColormap.from_list(
    "noche", ["#1b2a3a", "#1d4a5a", "#1f6f75", "#2a968a", "#5dbd9c", "#a9dfbf", "#eaf7e4"])
DIVERGING = LinearSegmentedColormap.from_list("cian_naranja", [CYAN, "#2a313d", ORANGE])

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 10,
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "axes.edgecolor": AXIS, "axes.labelcolor": TEXT2, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "text.color": TEXT, "axes.titlecolor": TEXT, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.grid": True, "axes.axisbelow": True, "legend.facecolor": BG, "legend.edgecolor": TEXT2,
    "legend.labelcolor": TEXT, "legend.framealpha": 1,
})


# --------------------------------------------------------------------------- utilidades
def short_name(area):
    """Nombre corto para etiquetas: sin notas al pie ni nombres oficiales largos."""
    name = str(area).rstrip("0123456789")
    return {"Heroica Puebla de Zaragoza": "Puebla", "San Francisco de Campeche": "Campeche",
            "León de los Aldama": "León", "Ciudad Nezahualcóyotl": "Nezahualcóyotl",
            "Culiacán Rosales": "Culiacán", "Acapulco de Juárez": "Acapulco",
            "Tlalnepantla de Baz": "Tlalnepantla", "Naucalpan de Juárez": "Naucalpan",
            "Ecatepec de Morelos": "Ecatepec", "Toluca de Lerdo": "Toluca",
            "Atizapán de Zaragoza": "Atizapán", "Oaxaca de Juárez": "Oaxaca",
            "Chilpancingo de los Bravo": "Chilpancingo", "Tlaxcala de Xicohténcatl": "Tlaxcala",
            "San Pedro Garza García": "San Pedro G. G.", "San Nicolás de los Garza": "San Nicolás",
            "Tlajomulco de Zúñiga": "Tlajomulco", "Cuajimalpa de Morelos": "Cuajimalpa",
            "La Magdalena Contreras": "Magdalena Contreras"}.get(name, name)



def labels_to_show(df, n_extremes=3):
    """Etiquetas selectivas: extremos de cada eje y mejores/peores combinaciones."""
    pick = set()
    for col in ["costo_canasta", "seguridad_pct"]:
        pick |= set(df.nsmallest(n_extremes, col).area_urbana_ensu)
        pick |= set(df.nlargest(n_extremes, col).area_urbana_ensu)
    z = ((df.seguridad_pct - df.seguridad_pct.mean()) / df.seguridad_pct.std()
         - (df.costo_canasta - df.costo_canasta.mean()) / df.costo_canasta.std())
    pick |= set(df.loc[z.nlargest(3).index, "area_urbana_ensu"])
    pick |= set(df.loc[z.nsmallest(3).index, "area_urbana_ensu"])
    return pick



# --------------------------------------------------------------------------- HTML
# Reporte en formato de tablero: barra de título, indicadores y tarjetas en cuadrícula de dos
# columnas con gráficas Plotly. Paleta y tipografía propias del reporte web.
H = dict(fondo="#171A16", tarjeta="#1C1F1A", texto="#F2F4EF", sec="#A9B0A4", verde="#11A3B5",
         rojo="#E5574A", neutro="#7C8478", arena="#B8A56A", grid="#3A4037", linea="#4A5146",
         pista="#2A2F27", hover="#111311")
H_Q = {1: H["verde"], 2: H["neutro"], 3: H["arena"], 4: H["rojo"]}
H_Q_TEXT = {1: "Más barata · más segura", 2: "Más cara · más segura",
            3: "Más barata · menos segura", 4: "Más cara · menos segura"}
H_FONT = "Plus Jakarta Sans, Segoe UI, Arial, sans-serif"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _layout(height, **kw):
    base = dict(height=height, autosize=True, barcornerradius=4,
                font=dict(family=H_FONT, color=H["texto"], size=14),
                plot_bgcolor=H["tarjeta"], paper_bgcolor=H["tarjeta"], margin=dict(t=40, r=30, b=50),
                legend=dict(itemsizing="constant", bgcolor="rgba(0,0,0,0)", font=dict(size=13)),
                hoverlabel=dict(font=dict(family=H_FONT, color=H["texto"]), bgcolor=H["hover"],
                                bordercolor=H["linea"]))
    base.update(kw)
    return base


def _ax(**kw):
    base = dict(linecolor=H["linea"], tickcolor=H["grid"], linewidth=1.5, showline=True, mirror=False,
                ticks="outside", ticklen=5, gridcolor=H["grid"], gridwidth=1, zeroline=False, griddash="dot")
    base.update(kw)
    return base


def _respaldo(df):
    """Ejes en los que el intervalo al 90 % queda completamente de un lado de la mediana."""
    c, s = df.eje_costo_robusto.astype(bool), df.eje_seguridad_robusto.astype(bool)
    return pd.Series(np.select([c & s, s, c], ["Ambos ejes", "Solo seguridad", "Solo costo"], "Ninguno"), index=df.index)


def _fig_scatter(df, meta):
    import plotly.graph_objects as go
    fig = go.Figure()
    df = df.assign(respaldo=_respaldo(df), posicion=df.cuadrante.map(H_Q_TEXT))
    cols = ["area_urbana_ensu", "estado", "costo_ic90_inf", "costo_ic90_sup", "ic90_inf_seguro",
            "ic90_sup_seguro", "establecimientos", "posicion", "respaldo"]
    hover = ("<b>%{customdata[0]}</b> · %{customdata[1]}<br>Canasta: <b>$%{x:,.0f}</b> "
             "(IC 90% $%{customdata[2]:,.0f}–$%{customdata[3]:,.0f})<br>Se siente segura: <b>%{y:.1f}%</b> "
             "(IC 90% %{customdata[4]:.1f}–%{customdata[5]:.1f}%)<br>Posición vs. medianas: <b>%{customdata[7]}</b>"
             "<br>Respaldo de los intervalos: <b>%{customdata[8]}</b><br>Tiendas observadas: %{customdata[6]}"
             "<extra></extra>")
    for q in [1, 2, 3, 4]:
        d = df[df.cuadrante == q]
        fig.add_trace(go.Scatter(
            x=d.costo_canasta, y=d.seguridad_pct, mode="markers", name=H_Q_TEXT[q],
            marker=dict(size=np.where(d.cuadrante_robusto, 17, 13), color=H_Q[q],
                        line=dict(width=np.where(d.cuadrante_robusto, 2.5, 1),
                                  color=np.where(d.cuadrante_robusto, H["texto"], H["tarjeta"]))),
            customdata=d[cols].to_numpy(), hovertemplate=hover))
    fig.add_vline(meta["mediana_costo"], line=dict(color=H["sec"], width=1.5, dash="dot"))
    fig.add_hline(meta["mediana_seguridad"], line=dict(color=H["sec"], width=1.5, dash="dot"))
    for r in df[df.area_urbana_ensu.isin(labels_to_show(df))].itertuples():
        fig.add_annotation(x=r.costo_canasta, y=r.seguridad_pct, text=short_name(r.area_urbana_ensu),
                           showarrow=False, yshift=15, font=dict(size=12, color=H["sec"]))
    for q, (x, y, xa, ya) in {1: (0, 1, "left", "top"), 2: (1, 1, "right", "top"),
                              3: (0, 0, "left", "bottom"), 4: (1, 0, "right", "bottom")}.items():
        fig.add_annotation(x=x, y=y, xref="x domain", yref="y domain", xanchor=xa, yanchor=ya,
                           text=f"<b>{H_Q_TEXT[q].upper()}</b>", showarrow=False,
                           font=dict(size=12, color=H_Q[q]))
    fig.update_layout(**_layout(560, legend=dict(orientation="h", y=-0.2, x=0, bgcolor="rgba(0,0,0,0)",
                                                 font=dict(size=12), itemsizing="constant")),
                      xaxis=_ax(title="Costo de la canasta (pesos)", tickprefix="$", tickformat=",.0f"),
                      yaxis=_ax(title="% que se siente segura", range=[0, 100], ticksuffix="%"))
    return fig


def _fig_ranking(d, value, lo, hi, med, fmt, axis_title, tickprefix="", ticksuffix=""):
    import plotly.graph_objects as go
    fig = go.Figure()
    names_ = [short_name(a) for a in d.area_urbana_ensu]
    groups = [("Diferencia clara: por debajo", d[hi] < med, H["verde"] if value == "costo_canasta" else H["rojo"]),
              ("Diferencia clara: por encima", d[lo] > med, H["rojo"] if value == "costo_canasta" else H["verde"]),
              ("No concluyente", ~((d[hi] < med) | (d[lo] > med)), H["neutro"])]
    for label, mask, color in groups:
        s = d[mask]
        if s.empty:
            continue
        rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        fig.add_trace(go.Scatter(
            x=s[value], y=[names_[i] for i in np.flatnonzero(mask)], mode="markers+text", name=label,
            marker=dict(size=30, color=color, line=dict(width=1.5, color=H["tarjeta"])),
            text=[fmt(v) for v in s[value]], textfont=dict(size=10, color="#111311", weight="bold"),
            error_x=dict(type="data", symmetric=False, array=s[hi] - s[value], arrayminus=s[value] - s[lo],
                         color=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.45)", thickness=7, width=0),
            customdata=s[["area_urbana_ensu", lo, hi]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>Valor: <b>" + tickprefix + "%{x:,.1f}" + ticksuffix +
                          "</b><br>Margen de error (90%): " + tickprefix + "%{customdata[1]:,.1f}–" +
                          tickprefix + "%{customdata[2]:,.1f}" + ticksuffix + "<extra></extra>"))
    fig.add_vline(med, line=dict(color=H["sec"], width=1.5, dash="dot"),
                  annotation=dict(text=f"<b>Mediana {tickprefix}{med:,.0f}{ticksuffix}</b>" if tickprefix else
                                  f"<b>Mediana {med:.1f}{ticksuffix}</b>", font=dict(size=12, color=H["sec"]),
                                  yanchor="bottom"), annotation_position="top")
    fig.update_layout(**_layout(1180, margin=dict(t=40, r=30, b=50, l=10), showlegend=False),
                      xaxis=_ax(title=axis_title, tickprefix=tickprefix, ticksuffix=ticksuffix, tickformat=",.0f"),
                      yaxis=_ax(categoryorder="array", categoryarray=names_[::-1], showgrid=False, ticksuffix="  ",
                                range=[-0.7, len(names_) - 0.3],
                                tickfont=dict(size=12)))
    return fig


def _fig_dispersion(disp, names):
    import plotly.graph_objects as go
    d = disp.sort_values("cv_pct")
    colors = [H["rojo"] if i >= len(d) - 5 else H["verde"] for i in range(len(d))]
    fig = go.Figure(go.Bar(
        x=d.cv_pct, y=[names[i] for i in d.index], orientation="h", marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.1f}%  ·  {r:.1f}×" for v, r in zip(d.cv_pct, d.razon_max_min)], textposition="outside",
        textfont=dict(size=12, weight="bold"), cliponaxis=False,
        customdata=d[["razon_max_min", "minimo", "maximo"]].to_numpy(),
        hovertemplate="<b>%{y}</b><br>Variación entre ciudades: <b>%{x:.1f}%</b><br>Ciudad más cara ÷ más barata: "
                      "%{customdata[0]:.1f}×<br>Precio por unidad: $%{customdata[1]:,.1f}–$%{customdata[2]:,.1f}<extra></extra>"))
    fig.update_layout(**_layout(620, margin=dict(t=20, r=110, b=50, l=10), bargap=0.22, showlegend=False),
                      xaxis=_ax(title="Variación del precio entre ciudades (coeficiente de variación)", ticksuffix="%",
                                range=[0, d.cv_pct.max() * 1.12]),
                      yaxis=_ax(showgrid=False, ticksuffix="  "))
    return fig


def _fig_stores(store, names):
    import plotly.graph_objects as go
    g = store.groupby("producto_normalizado").indice
    st = pd.DataFrame({"barata": g.apply(lambda v: (v < 90).mean() * 100),
                       "cara": g.apply(lambda v: (v > 110).mean() * 100),
                       "iqr": g.quantile(.75) - g.quantile(.25), "n": g.size()})
    st["similar"] = 100 - st.barata - st.cara
    st = st.sort_values("iqr")
    y = [names[i] for i in st.index]
    fig = go.Figure()
    for col, label, color in [("barata", "Más de 10% abajo del precio típico", H["verde"]),
                              ("similar", "Similar al típico (±10%)", H["neutro"]),
                              ("cara", "Más de 10% arriba del precio típico", H["rojo"])]:
        fig.add_trace(go.Bar(
            x=st[col], y=y, orientation="h", name=label, marker=dict(color=color, line=dict(width=1.5, color=H["tarjeta"])),
            text=[f"{v:.0f}" if v >= 10 else "" for v in st[col]], textposition="inside", insidetextanchor="middle",
            textangle=0,
            textfont=dict(size=12, color="#111311", weight="bold"), customdata=st[["n"]].to_numpy(),
            hovertemplate="<b>%{y}</b><br>" + label + ": <b>%{x:.0f} de cada 100</b> tiendas<br>"
                          "Tiendas observadas: %{customdata[0]}<extra></extra>"))
    fig.update_layout(**_layout(620, margin=dict(t=60, r=30, b=50, l=10), barmode="stack", bargap=0.22,
                                legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, bgcolor="rgba(0,0,0,0)",
                                            font=dict(size=12), traceorder="normal")),
                      xaxis=_ax(title="Tiendas de cada 100", range=[0, 100], dtick=25),
                      yaxis=_ax(showgrid=False, ticksuffix="  "))
    return fig, st


def _fig_chains(chains):
    import plotly.graph_objects as go
    d = chains.sort_values("indice_medio")
    diff = d.indice_medio - 100
    colors = [H["neutro"] if abs(v) < 0.5 else H["verde"] if v < 0 else H["rojo"] for v in diff]
    fig = go.Figure(go.Bar(
        x=diff, y=d.cadena_comercial, orientation="h", marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:+.1f}%" for v in diff], textposition="outside", textfont=dict(size=12, weight="bold"), cliponaxis=False,
        customdata=d[["areas", "establecimientos", "precios", "pct_precios_menores_a_mediana"]].to_numpy(),
        hovertemplate="<b>%{y}</b><br>Precios observados: <b>%{x:+.1f}%</b> en promedio vs. la mediana local del mismo producto<br>"
                      "%{customdata[3]:.0f}% de sus precios quedaron por debajo de esa mediana<br>"
                      "%{customdata[0]} áreas · %{customdata[1]} tiendas · %{customdata[2]} precios<extra></extra>"))
    lim = abs(diff).max() * 1.3
    fig.add_vline(0, line=dict(color=H["linea"], width=2))
    fig.update_layout(**_layout(560, margin=dict(t=20, r=40, b=50, l=10), bargap=0.25, showlegend=False),
                      xaxis=_ax(title="Precio observado vs. mediana local del mismo producto (%)", ticksuffix="%", range=[-lim, lim]),
                      yaxis=_ax(showgrid=False, ticksuffix="  "))
    return fig


def _fig_products(prices, names):
    import plotly.graph_objects as go
    items = sorted(prices.producto_normalizado.unique(), key=lambda k: names[k])
    fig = go.Figure()
    for i, item in enumerate(items):
        p = prices[prices.producto_normalizado == item].sort_values("precio_mediana")
        med = p.precio_mediana.median()
        fig.add_trace(go.Bar(
            x=[short_name(a) for a in p.area_urbana_ensu], y=p.precio_mediana, visible=i == 0, name=names[item],
            marker=dict(color=np.where(p.precio_mediana < med, H["verde"], H["rojo"]), line=dict(width=0)),
            customdata=p[["area_urbana_ensu", "establecimientos", "observaciones"]].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br><b>$%{y:,.2f}</b> por porción<br>"
                          "Tiendas: %{customdata[1]} · Precios: %{customdata[2]}<extra></extra>"))
    buttons = [dict(label=names[it], method="update", args=[{"visible": [j == i for j in range(len(items))]}])
               for i, it in enumerate(items)]
    fig.update_layout(**_layout(560, margin=dict(t=70, r=30, b=50), bargap=0.18, showlegend=False),
                      updatemenus=[dict(buttons=buttons, x=0, y=1.13, xanchor="left", yanchor="bottom",
                                        bgcolor=H["hover"], bordercolor=H["linea"], font=dict(color=H["texto"], size=13))],
                      yaxis=_ax(title="Precio de la porción de la canasta", tickprefix="$"),
                      xaxis=_ax(tickangle=-55, tickfont=dict(size=11), showgrid=False))
    return fig


def _fig_map(geo, key, label, fmt):
    import plotly.graph_objects as go
    g = geo[key]
    shared = pd.Series([a for _, a in g["text"]]).value_counts()
    custom = [[m, a, int(shared[a])] for m, a in g["text"]]
    fig = go.Figure(go.Choropleth(
        geojson=geo["entidades"], locations=[f["id"] for f in geo["entidades"]["features"]], z=[0] * len(geo["entidades"]["features"]),
        colorscale=[[0, H["pista"]], [1, H["pista"]]], showscale=False, marker_line_color=H["linea"],
        marker_line_width=0.7, hoverinfo="skip"))
    fig.add_trace(go.Choropleth(
        geojson=g["geojson"], locations=g["ids"], z=g["z"], featureidkey="id",
        colorscale=[[0, "#1E3A3D"], [0.35, "#167A86"], [0.65, H["verde"]], [1, "#CDEFF3"]],
        marker_line_color=H["tarjeta"], marker_line_width=0.3, customdata=custom,
        hovertemplate="<b>%{customdata[0]}</b><br>Área urbana ENSU: %{customdata[1]}<br>" + label + ": <b>" + fmt +
                      "</b><br><i>Valor del área urbana, compartido por %{customdata[2]} municipio(s)</i><extra></extra>",
        colorbar=dict(title=dict(text=label, font=dict(size=12)), tickfont=dict(size=11), outlinewidth=0,
                      thickness=12, len=0.7)))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor=H["tarjeta"], projection_type="mercator")
    fig.update_layout(**_layout(560, margin=dict(l=0, r=0, t=10, b=0)))
    return fig


def _fecha(iso):
    y, m, d = str(iso)[:10].split("-")
    return f"{int(d)} {MESES[int(m) - 1]} {y}"


def _card(title, sub, body, chart_height=None, note=None):
    head = f'<div class="card-head"><h2>{title}</h2>' + (f"<p>{sub}</p>" if sub else "") + "</div>"
    if chart_height:
        body = f'<div class=""><div class="chart-scroll"><div style="height:{chart_height}px; width:100%;">{body}</div></div></div>'
    else:
        body = f'<div class="card-body">{body}</div>'
    if note:
        body += f'<p class="nota">{note}</p>'
    return f'<div class="card">{head}{body}</div>'


def _meter(lo, hi, band, marks, legend, aria):
    pos = lambda v: f"{(v - lo) / (hi - lo) * 100:.1f}%"
    ticks = np.linspace(lo, hi, 5)
    html = [f'<div class="meter" role="img" aria-label="{aria}"><div class="meter-track">',
            f'<div class="meter-band" style="left:{pos(band[0])};width:{(band[1] - band[0]) / (hi - lo) * 100:.1f}%"></div>']
    for cls, v, text in marks:
        html.append(f'<div class="meter-mark {cls}" style="left:{pos(v)}"><span>{text}</span></div>')
    html.append("</div><div class=\"meter-scale\">" + "".join(f"<span>{legend[0](t)}</span>" for t in ticks) + "</div>")
    html.append(f'<p class="meter-legend"><i class="sw band"></i>{legend[1]}</p></div>')
    return "".join(html)


def _hl(text):
    """Marcado breve para insights: [+favorable+] verde, [-desfavorable-] rojo, [=matiz=] ámbar, todo en negritas."""
    text = re.sub(r"\[\+(.+?)\+\]", r'<b class="pos">\1</b>', text)
    text = re.sub(r"\[-(.+?)-\]", r'<b class="neg">\1</b>', text)
    return re.sub(r"\[=(.+?)=\]", r'<b class="neu">\1</b>', text)


HALLAZGOS = {  # (veredicto, tono, insight, interpretación, hipótesis). Hechos con datos; hipótesis aparte; sin causalidad.
    "Saltillo": ("Seguridad más alta", "pos",
                 "[+Seguridad más alta del grupo ({s:.1f}%)+], {ds:+.1f} pp frente a la mediana y respaldada por el intervalo.",
                 "Su costo ({c}) queda [=arriba de la mediana, pero no es concluyente=]: el intervalo ({clo}–{chi}) la cruza.",
                 "El intervalo amplio del costo podría deberse a las pocas tiendas observadas ({est})."),
    "Culiacán": ("Seguridad más baja", "neg",
                 "[-Seguridad más baja del grupo ({s:.1f}%)-], {ds:+.1f} pp frente a la mediana, diferencia respaldada.",
                 "Su costo ({c}) [=no se distingue de la mediana=]: la baja seguridad percibida no se acompaña de una canasta distinta.",
                 "Contrastar con otras fuentes (p. ej., incidencia delictiva del SESNSP); este análisis no identifica causas."),
    "Nezahualcóyotl": ("Más barata · más segura", "pos",
                       "[+Canasta más barata del grupo ({c})+] y [+seguridad {ds:+.1f} pp arriba de la mediana+].",
                       "Es la [+única área+] cuyas dos posiciones se sostienen con los intervalos al 90%.",
                       "Se estima con {est} tiendas y el límite superior ({chi}) queda cerca de la mediana: conviene confirmarlo."),
    "Monterrey": ("Canasta más cara", "neg",
                  "[-Canasta más cara del grupo ({c}, {dc:+.1f}%)-]; seguridad [+{ds:+.1f} pp arriba de la mediana+]. Ambas respaldadas.",
                  "[=No implica el mayor costo de vida=]: la canasta no incluye vivienda, transporte, servicios ni el resto de los alimentos.",
                  "La mezcla de cadenas observadas podría influir en el costo; verificar con más tiendas por área."),
    "Ecatepec": ("Barata, pero menos segura", "neu",
                 "[+Canasta entre las más baratas ({dc:+.1f}%)+], pero [-seguridad {ds:+.1f} pp abajo de la mediana-]. Ambas respaldadas.",
                 "Un costo bajo [=no coincide necesariamente=] con mayor seguridad percibida.",
                 "Sin hipótesis adicional: es compatible con no haber hallado una asociación significativa en el conjunto."),
}


def _mini(lo, hi, v, ci, med, color, label_lo, label_hi):
    pos = lambda x: f"{min(max((x - lo) / (hi - lo), 0), 1) * 100:.1f}%"
    w = (min(ci[1], hi) - max(ci[0], lo)) / (hi - lo) * 100
    return (f'<div class="mini"><div class="mini-track">'
            f'<div class="mini-ci" style="left:{pos(ci[0])};width:{w:.1f}%;background:{color}55"></div>'
            f'<div class="mini-med" style="left:{pos(med)}"></div>'
            f'<div class="mini-dot" style="left:{pos(v)};background:{color}"></div></div>'
            f'<div class="mini-scale"><span>{label_lo}</span><span>{label_hi}</span></div></div>')


def _hallazgos(res, med_c, med_s):
    d = res.assign(corto=res.area_urbana_ensu.map(short_name), rank_c=res.costo_canasta.rank().astype(int),
                   rank_s=res.seguridad_pct.rank(ascending=False).astype(int))
    lo_c, hi_c = d.costo_ic90_inf.min(), d.costo_ic90_sup.max()
    cards = []
    for name, (verdict, tone, insight, interp, hyp) in HALLAZGOS.items():
        m = d[d.corto == name]
        if m.empty:
            continue
        r = m.iloc[0]
        dc, ds = (r.costo_canasta / med_c - 1) * 100, r.seguridad_pct - med_s
        f = dict(c=f"${r.costo_canasta:,.0f}", clo=f"${r.costo_ic90_inf:,.0f}", chi=f"${r.costo_ic90_sup:,.0f}",
                 s=r.seguridad_pct, dc=dc, ds=ds, est=int(r.establecimientos))
        # Color del delta: favorable/desfavorable solo si el intervalo lo respalda; si no, gris.
        tc = ("pos" if dc < 0 else "neg") if r.eje_costo_robusto else "gris"
        ts = ("pos" if ds > 0 else "neg") if r.eje_seguridad_robusto else "gris"
        col = {"pos": H["verde"], "neg": H["rojo"], "gris": H["neutro"]}
        delta = lambda lbl, val, chg, t, rank, ok, bar: (
            f'<div class="delta"><span class="lbl">{lbl}</span><div class="delta-row"><span class="val">{val}</span>'
            f'<span class="chg {t}">{chg}</span><span class="sig">#{rank} de {len(d)} · '
            f'{"respaldado (IC 90%)" if ok else "no concluyente"}</span></div>{bar}</div>')
        cards.append(
            f'<div class="hall t-{tone}"><div class="hall-top"><h3>{name}<span class="muted"> · {r.estado.split(" / ")[0]}</span></h3>'
            f'<span class="verdict {tone}">{verdict}</span></div>'
            '<div class="deltas">'
            + delta("Canasta", f["c"], f"{'▼' if dc < 0 else '▲'} {dc:+.1f}%", tc, r.rank_c, r.eje_costo_robusto,
                    _mini(lo_c, hi_c, r.costo_canasta, (r.costo_ic90_inf, r.costo_ic90_sup), med_c, col[tc],
                          f"${lo_c:,.0f}", f"${hi_c:,.0f}"))
            + delta("Seguridad", f"{r.seguridad_pct:.1f}%", f"{'▲' if ds > 0 else '▼'} {ds:+.1f} pp", ts, r.rank_s,
                    r.eje_seguridad_robusto,
                    _mini(0, 100, r.seguridad_pct, (r.ic90_inf_seguro, r.ic90_sup_seguro), med_s, col[ts], "0%", "100%"))
            + "</div>"
            + f'<p class="insight">{_hl(insight.format(**f))}</p><p class="interp">{_hl(interp.format(**f))}</p>'
            f'<p class="hyp"><span>Hipótesis por verificar</span>{hyp.format(**f)}</p></div>')
    leyenda = ('<p class="hall-key"><b class="pos">▲▼ Verde</b> = favorable · <b class="neg">Rojo</b> = desfavorable · '
               '<b class="gris">Gris</b> = no concluyente (el intervalo al 90% cruza la mediana) · ▲▼ = diferencia vs. la mediana del grupo · '
               'Barra = intervalo al 90%, punto = valor, línea blanca = mediana · Canasta más baja y seguridad más alta son favorables.</p>')
    return leyenda + '<div class="hall-grid">' + "".join(cards) + "</div>"


def interactive_html(df, prices, names, meta, geo, path, disp=None, chains=None, store=None, nacional_seguridad=40.0):
    """Reporte HTML en formato de tablero (tarjetas + gráficas Plotly cargadas desde CDN)."""
    config = {"displayModeBar": False, "responsive": True}

    def div(fig, id_):
        return fig.to_html(full_html=False, include_plotlyjs=False, config=config, div_id=id_, default_height="100%")

    res = df.sort_values("costo_canasta").reset_index(drop=True)
    med_c, med_s = meta["mediana_costo"], meta["mediana_seguridad"]
    cheap, dear = res.iloc[0], res.iloc[-1]
    safe, unsafe = res.loc[res.seguridad_pct.idxmax()], res.loc[res.seguridad_pct.idxmin()]
    robust = {q: [short_name(a) for a in res[(res.cuadrante == q) & res.cuadrante_robusto].area_urbana_ensu] for q in (1, 2, 3, 4)}
    pval = meta.get("p_permutacion", float("nan"))
    res["respaldo"] = _respaldo(res)
    n_robust = int(res.cuadrante_robusto.sum())
    shared = pd.Series([a for _, a in geo["mapa_costo"]["text"]]).value_counts()
    multi = shared[shared > 1]

    kpis = "".join(_card(t, None, f'<p class="kpi-value {c}">{v}</p><p class="kpi-note">{n}</p>') for t, v, c, n in [
        ("Áreas urbanas comparables", f"{meta['areas']}", "verde", f"Canasta fija de {meta['productos']} productos"),
        ("Costo típico de la canasta", f"${med_c:,.0f}", "verde", f"Mediana · rango ${cheap.costo_canasta:,.0f}–${dear.costo_canasta:,.0f}"),
        ("Más cara vs. más barata", f"+{meta['rango_costo_pct']:.1f}%", "rojo",
         f"{short_name(dear.area_urbana_ensu)} vs. {short_name(cheap.area_urbana_ensu)} · solo esta canasta"),
        ("Asociación costo–seguridad", f"{meta['spearman']:+.2f}", "", f"Spearman · p = {pval:.2f} · no significativa")])

    q = res.costo_canasta.quantile([.25, .75])
    qs = res.seguridad_pct.quantile([.25, .75])
    lo_c, hi_c = np.floor(res.costo_canasta.min() / 20) * 20 - 20, np.ceil(res.costo_canasta.max() / 20) * 20 + 20
    meters = (_meter(lo_c, hi_c, (q[.25], q[.75]),
                     [("consenso", cheap.costo_canasta, f"Más barata ${cheap.costo_canasta:,.0f}"),
                      ("actual", med_c, f"Mediana ${med_c:,.0f}")],
                     (lambda v: f"${v:,.0f}", f"Mitad central de las áreas: ${q[.25]:,.0f}–${q[.75]:,.0f}"),
                     f"Costo mediano {med_c:,.0f} pesos")
              + '<div style="height:18px"></div>'
              + _meter(0, 100, (qs[.25], qs[.75]),
                       [("consenso", nacional_seguridad, f"Nacional {nacional_seguridad:.1f}%"),
                        ("actual", med_s, f"Mediana {med_s:.1f}%")],
                       (lambda v: f"{v:.0f}%", f"Mitad central de las áreas: {qs[.25]:.1f}%–{qs[.75]:.1f}% se siente segura"),
                       f"Seguridad mediana {med_s:.1f} por ciento"))
    bullets = [
        f"<b class='pos'>{short_name(cheap.area_urbana_ensu)} ${cheap.costo_canasta:,.0f}</b> y "
        f"<b class='neg'>{short_name(dear.area_urbana_ensu)} ${dear.costo_canasta:,.0f}</b> son los extremos observados de esta "
        f"canasta de {meta['productos']} productos (<b class='neg'>▲ {meta['rango_costo_pct']:.1f}%</b> de diferencia). "
        "<b class='neu'>No representan el gasto total en alimentos ni el costo de vida.</b>",
        f"La seguridad varía mucho más: de <b class='neg'>▼ {unsafe.seguridad_pct:.1f}%</b> ({short_name(unsafe.area_urbana_ensu)}) a "
        f"<b class='pos'>▲ {safe.seguridad_pct:.1f}%</b> ({short_name(safe.area_urbana_ensu)}).",
        f"<b class='neu'>No se encontró evidencia estadísticamente significativa</b> de una asociación entre el costo de la canasta y la "
        f"percepción de seguridad en las áreas analizadas (Spearman {meta['spearman']:+.2f}; p = {pval:.2f}).",
        f"Por posición frente a las medianas, cada área cae en un cuadrante; con respaldo de los intervalos al 90% en ambos "
        f"ejes solo quedan <b>{n_robust}</b>: "
        + "; ".join(f"<b class='{ {1: 'pos', 4: 'neg'}.get(k, 'neu') }'>{', '.join(v)}</b> ({H_Q_TEXT[k].lower()})"
                    for k, v in robust.items() if v)
        + (f". Ninguna en «{H_Q_TEXT[4].lower()}»." if not robust[4] else ".")]
    if disp is not None:
        top = disp.sort_values("cv_pct", ascending=False)
        bullets.append(f"Los precios que más cambian entre ciudades: <b class='neg'>{', '.join(names[i] for i in top.index[:3])}</b> "
                       f"(hasta <b class='neg'>{top.razon_max_min.max():.1f}×</b> entre la ciudad más cara y la más barata).")
    if chains is not None:
        c = chains.sort_values("indice_medio")
        bullets.append(f"En los precios observados, {c.cadena_comercial.iloc[0]} quedó en promedio "
                       f"<b class='pos'>▼ {c.indice_medio.iloc[0] - 100:+.1f}%</b> y {c.cadena_comercial.iloc[-1]} "
                       f"<b class='neg'>▲ {c.indice_medio.iloc[-1] - 100:+.1f}%</b> frente a la mediana local del mismo producto; "
                       "<b class='neu'>no equivale a un ahorro garantizado</b>.")
    lectura = '<ul class="lista">' + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>"

    n_q = res.cuadrante.value_counts()
    filas = [f'<div class="fila kpis">{kpis}</div>',
             '<div class="fila">' + _card("Dónde está el costo y la seguridad típicos",
                                          f"Mediana costo → ${med_c:,.0f} | Mediana seguridad → {med_s:.1f}%", meters)
             + _card("Lectura rápida", "Cifras clave del periodo", lectura) + "</div>"]

    maps = (f'<div class="tabs" role="tablist"><button role="tab" aria-selected="true" data-target="m-costo">Costo de la canasta</button>'
            f'<button role="tab" aria-selected="false" data-target="m-seg">Seguridad percibida</button></div>'
            f'<div id="m-costo" style="height:560px">{div(_fig_map(geo, "mapa_costo", "Costo", "$%{z:,.0f}"), "mapa-costo")}</div>'
            f'<div id="m-seg" class="hidden" style="height:560px">{div(_fig_map(geo, "mapa_seguridad", "% segura", "%{z:.1f}%"), "mapa-seguridad")}</div>')
    filas.append('<div class="fila">'
                 + _card("Costo de la canasta vs. seguridad percibida",
                         "Color → posición frente a las medianas ("
                         + (f"{n_q.min()} áreas en cada cuadrante" if n_q.min() == n_q.max() else f"{n_q.min()}–{n_q.max()} áreas por cuadrante")
                         + ") | "
                         f"Contorno blanco → respaldada por IC 90% en ambos ejes ({n_robust} áreas)",
                         div(_fig_scatter(res, meta), "graf-cuadrantes"), 560,
                         note="<b class='neu'>Posición no es lo mismo que diferencia significativa.</b> El cuadrante solo indica de qué lado de "
                              "cada mediana está el área. Solo las áreas con contorno blanco tienen ambos intervalos al 90% del mismo "
                              "lado; en las demás, al menos un eje no permite afirmar una diferencia. El detalle aparece al pasar el cursor.")
                 + _card("Mapa municipal", "Precios → tiendas PROFECO en los municipios observados | Seguridad → estimación ENSU del área urbana",
                         f'<div class="map-wrap">{maps}</div>', 610,
                         note=f"<b>{len(multi)} de {len(shared)} áreas agrupan varios municipios</b> (hasta {multi.max()} en "
                              f"{short_name(multi.idxmax())}): todos muestran la misma estimación urbana, no un dato propio. "
                              "Gris: municipio fuera de las áreas analizadas.") + "</div>")

    rc = res.sort_values("costo_canasta").reset_index(drop=True)
    rs = res.sort_values("seguridad_pct", ascending=False).reset_index(drop=True)
    clear_c = ((rc.costo_ic90_sup < med_c) | (rc.costo_ic90_inf > med_c)).sum()
    clear_s = ((rs.ic90_sup_seguro < med_s) | (rs.ic90_inf_seguro > med_s)).sum()
    filas.append('<div class="fila">'
                 + _card("Ranking del costo de la canasta", f"Diferencia clara → <b>{clear_c} de {len(rc)}</b> áreas | <b class='pos'>Verde → más barata</b> | "
                         "<b class='neg'>Rojo → más cara</b> | <b class='gris'>Gris → no concluyente</b>",
                         div(_fig_ranking(rc, "costo_canasta", "costo_ic90_inf", "costo_ic90_sup", med_c, lambda v: f"{v:,.0f}",
                                          "Pesos por canasta · barra = margen de error (90%)", tickprefix="$"), "graf-rank-costo"), 1180)
                 + _card("Ranking de seguridad percibida", f"Diferencia clara → <b>{clear_s} de {len(rs)}</b> áreas | <b class='pos'>Verde → más segura</b> | "
                         "<b class='neg'>Rojo → menos segura</b> | <b class='gris'>Gris → no concluyente</b>",
                         div(_fig_ranking(rs, "seguridad_pct", "ic90_inf_seguro", "ic90_sup_seguro", med_s, lambda v: f"{v:.1f}",
                                          "% que se siente segura · barra = margen de error (90%)", ticksuffix="%"), "graf-rank-seg"), 1180)
                 + "</div>")

    if disp is not None and store is not None:
        fs, st = _fig_stores(store, names)
        d = disp.sort_values("cv_pct", ascending=False)
        filas.append('<div class="fila">'
                     + _card("Qué productos cambian más de precio entre ciudades",
                             f"Mayor → {names[d.index[0]]} <b class='neg'>▲ {d.cv_pct.iloc[0]:.1f}%</b> | "
                             f"Menor → {names[d.index[-1]]} <b class='pos'>▼ {d.cv_pct.iloc[-1]:.1f}%</b>",
                             div(_fig_dispersion(disp, names), "graf-dispersion"), 620)
                     + _card("De cada 100 tiendas, ¿cuántas cobran más o menos?",
                             f"Más diferencia entre tiendas → <b class='neg'>{names[st.index[-1]]}</b> | "
                             f"Menos → <b class='pos'>{names[st.index[0]]}</b>",
                             div(fs, "graf-tiendas"), 620) + "</div>")
    second = _card("Explorador de precios por producto", "Elige un producto | <b class='pos'>Verde → abajo de la mediana</b> | <b class='neg'>Rojo → arriba</b>",
                   div(_fig_products(prices, names), "graf-productos"), 560)
    if chains is not None:
        c = chains.sort_values("indice_medio")
        filas.append('<div class="fila">'
                     + _card("Precios observados por cadena vs. mediana local",
                             f"Más bajos → {c.cadena_comercial.iloc[0]} <b class='pos'>▼ {c.indice_medio.iloc[0] - 100:+.1f}%</b> | "
                             f"Más altos → {c.cadena_comercial.iloc[-1]} <b class='neg'>▲ {c.indice_medio.iloc[-1] - 100:+.1f}%</b>",
                             div(_fig_chains(chains), "graf-cadenas"), 560,
                             note="Promedio de la diferencia de cada precio observado frente a la mediana del mismo producto en la "
                                  "misma área. <b class='neu'>No es un ahorro garantizado</b> ni indica que una cadena sea siempre más económica: "
                                  f"en {c.cadena_comercial.iloc[0]}, {c.pct_precios_menores_a_mediana.iloc[0]:.0f}% de los precios "
                                  "quedaron por debajo de la mediana local.") + second + "</div>")
    else:
        filas.append(f'<div class="fila">{second}</div>')

    tag = {1: "verde", 4: "rojo"}
    rows = "".join(
        f"<tr><td>{i + 1}</td><td><b>{short_name(r.area_urbana_ensu)}</b><br><span class='muted'>{r.estado.split(' / ')[0]}</span></td>"
        f"<td>${r.costo_canasta:,.0f}</td><td>{r.seguridad_pct:.1f}%</td>"
        f"<td class='tag {tag.get(r.cuadrante, 'gris')}'><span>{H_Q_TEXT[r.cuadrante]}</span></td>"
        f"<td>{'<b>' + r.respaldo + '</b>' if r.respaldo == 'Ambos ejes' else r.respaldo}</td></tr>"
        for i, r in enumerate(res.itertuples()))
    tabla = ('<div class="table-scroll"><table><thead><tr><th>#</th><th>Área urbana</th><th>Canasta</th><th>Segura</th>'
             f'<th>Posición (medianas)</th><th>Respaldo IC 90%</th></tr></thead><tbody>{rows}</tbody></table></div>'
             '<p class="kpi-note" style="padding-top:10px">Posición = lado de cada mediana. Respaldo = ejes en los que el '
             'intervalo al 90% no cruza la mediana; solo con «Ambos ejes» el cuadrante está respaldado estadísticamente.</p>')
    guia = [("Mediana", "El valor de en medio: la mitad de las áreas (o tiendas) está por debajo y la mitad por encima.", "verde", "Valor típico"),
            ("Media (promedio)", "Suma entre número de casos; sube si hay unos pocos valores muy altos.", "gris", "Referencia"),
            ("Margen de error (90%)", "Rango donde casi seguro está el valor real. Si cruza la mediana, la diferencia no es concluyente.", "rojo", "Revisar antes de concluir"),
            ("Variación entre ciudades (CV)", "Cuánto se aleja, en promedio, el precio de cada ciudad del promedio nacional.", "gris", "Más alto = más diferencia"),
            ("Índice 100", "Precio típico del producto; 110 = 10% más caro, 90 = 10% más barato.", "gris", "Comparar tiendas"),
            ("Cuadrante", "Posición respecto a las medianas de costo y seguridad; por sí sola no implica una diferencia significativa.", "gris", "Ver respaldo IC"),
            ("Spearman", "Mide si dos variables tienden a moverse juntas, de −1 a 1; el valor p indica si el resultado podría deberse al azar.",
             "gris", f"Aquí {meta['spearman']:+.2f} · p = {pval:.2f}")]
    guia_html = ('<table><thead><tr><th>Indicador</th><th>Qué significa</th><th>Uso</th></tr></thead><tbody>'
                 + "".join(f"<tr><td><b>{a}</b></td><td>{b_}</td><td class='tag {c}'><span>{d_}</span></td></tr>" for a, b_, c, d_ in guia)
                 + "</tbody></table><p style=\"padding-top:12px;font-weight:600\">¿En tu ciudad la canasta cuesta más que la mediana? "
                   "Compara la misma lista de productos entre cadenas antes de comprar: la diferencia puede ser mayor que entre ciudades.</p>")
    filas.append('<div class="fila una">' + _card("Hallazgos e interpretación económica",
                 "Cinco áreas destacadas | Hechos con respaldo estadístico vs. <b class='neu'>hipótesis por verificar</b> | Sin inferencia causal", _hallazgos(res, med_c, med_s)) + "</div>")
    filas.append('<div class="fila">' + _card("Tabla de resultados", f"{len(res)} áreas, de la canasta más barata a la más cara", tabla)
                 + _card("Cómo leer este reporte", "Indicadores en lenguaje llano", guia_html) + "</div>")
    limites = [f"Los precios corresponden a <b>{meta['periodo_precios']}</b>; la seguridad percibida, a <b>{meta['periodo_ensu']}</b>.",
               "La comparación es <b>transversal</b>: un solo momento, sin cambios en el tiempo.",
               "Los resultados describen <b>asociaciones, no causalidad</b>.",
               f"La canasta incluye <b>únicamente los {meta['productos']} productos</b> definidos; no es el gasto total en alimentos ni el costo de vida.",
               "Los precios de PROFECO <b>no representan necesariamente todos los establecimientos</b> de una ciudad."]
    territorio = ["<b>Precios:</b> supermercados y tiendas de autoservicio de PROFECO ubicados en los municipios observados de cada área.",
                  "<b>Seguridad:</b> estimación de INEGI (ENSU) para el área urbana completa, que puede abarcar varios municipios.",
                  f"Los municipios con tiendas observadas cubren entre <b>{res.cobertura_geografica_pct.min():.0f}% y "
                  f"{res.cobertura_geografica_pct.max():.0f}%</b> de la población de 18+ de su área "
                  f"({(res.tipo_correspondencia == 'directa').sum()} áreas con correspondencia directa).",
                  f"<b>{len(multi)} de {len(shared)} áreas</b> agrupan varios municipios: comparten una sola estimación de costo y de seguridad."]
    filas.append('<div class="fila">' + _card("Limitaciones del análisis", "Nota metodológica",
                                              '<ul class="lista">' + "".join(f"<li>{x}</li>" for x in limites) + "</ul>")
                 + _card("Comparabilidad territorial", "Qué unidad geográfica mide cada fuente",
                         '<ul class="lista">' + "".join(f"<li>{x}</li>" for x in territorio) + "</ul>") + "</div>")

    header = (f'<header class="topbar"><div><h1>¿Dónde cuesta menos la canasta y se percibe mayor seguridad?</h1>'
              f'<p class="sub">México · Canasta comparable de {meta["productos"]} productos (PROFECO) y seguridad percibida (INEGI, ENSU)</p></div>'
              f'<div class="meta"><p>Precios: <b>{meta["periodo_precios"]}</b> · ENSU: <b>{meta["periodo_ensu"]}</b></p>'
              f'<p>Datos al <b>{_fecha(meta.get("generado", ""))}</b> · Fuentes: PROFECO e INEGI</p><p>Elaboración propia</p></div></header>')
    footer = ('<footer><p>Datos procesados con Python (pandas y Plotly). Canasta fija con las mismas presentaciones en todas las áreas, '
              'solo supermercados y tiendas de autoservicio; precio representativo = mediana por tienda y después entre tiendas. '
              'Margen de error del costo por bootstrap (1,000 réplicas); el de seguridad es el oficial de INEGI.</p><ul>'
              f'<li><a href="https://datos.profeco.gob.mx/datos_abiertos/qqp.php" target="_blank" rel="noopener">PROFECO, Quién es Quién en los Precios (archivo {meta.get("archivo_profeco", "")})</a></li>'
              f'<li><a href="https://www.inegi.org.mx/programas/ensu/" target="_blank" rel="noopener">INEGI, Encuesta Nacional de Seguridad Pública Urbana ({meta["periodo_ensu"]})</a></li>'
              '<li><a href="https://www.inegi.org.mx/temas/mg/" target="_blank" rel="noopener">INEGI, Marco Geoestadístico 2024</a></li></ul></footer>')
    html = (HEAD.replace("{TITLE}", "Canasta y seguridad urbana")
            + f'<div class="page">{header}{"".join(filas)}{footer}</div>' + TAIL)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(html, encoding="utf-8")
    return path


HEAD = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="Costo de una canasta comparable (PROFECO) vs. percepción de seguridad (INEGI ENSU) en áreas urbanas de México.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap">
<style>
:root {
  color-scheme: dark;
  --titulo: #2F352B; --fondo: #171A16; --tarjeta: #1C1F1A; --borde: #30362D;
  --franja: #2B2819; --franja-borde: #3D3823; --texto: #F2F4EF; --secundario: #A9B0A4;
  --texto-barra: #FFFFFF; --pista: #2A2F27; --banda: rgba(17, 163, 181, 0.45); --linea-tabla: #2A2F27;
  --pill-rojo: rgba(229, 87, 74, 0.16); --pill-verde: rgba(17, 163, 181, 0.16); --pill-gris: rgba(169, 176, 164, 0.14);
  --sombra: 0 1px 2px rgba(0, 0, 0, 0.30), 0 8px 22px rgba(0, 0, 0, 0.28);
  --sombra-barra: 0 8px 22px rgba(0, 0, 0, 0.35);
  --verde: #11A3B5; --rojo: #E5574A; --azul: #11A3B5; --ambar: #E0B54A;
  --fuente: "Plus Jakarta Sans", "Segoe UI", -apple-system, Arial, sans-serif;
}
* { box-sizing: border-box; }
body { background: var(--fondo); color: var(--texto); font-family: var(--fuente); }
p { margin: 0; }
.card { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 12px; overflow: hidden;
  min-width: 0; display: flex; flex-direction: column; box-shadow: var(--sombra); }
.card-head { background: var(--franja); border-bottom: 1px solid var(--franja-borde); text-align: left; padding: 12px 18px 11px; }
.card-head h2 { margin: 0; font-size: 1.05rem; font-weight: 700; letter-spacing: -0.01em; color: var(--texto); }
.card-head p { font-size: 0.84rem; color: var(--secundario); margin-top: 2px; }
.card-body { padding: 16px 18px; }
.kpi-value { font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; font-variant-numeric: tabular-nums; }
.kpi-note { font-size: 0.84rem; color: var(--secundario); margin-top: 4px; }
.verde { color: var(--verde); } .rojo { color: var(--rojo); }
.meter { display: grid; gap: 8px; padding-top: 30px; }
.meter-track { position: relative; height: 12px; background: var(--pista); border-radius: 999px; }
.meter-band { position: absolute; top: 0; bottom: 0; background: var(--banda); border-radius: 999px; }
.meter-mark { position: absolute; top: -7px; bottom: -7px; width: 3px; border-radius: 2px; transform: translateX(-50%); }
.meter-mark.actual { background: var(--texto); }
.meter-mark.consenso { background: var(--secundario); }
.meter-mark span { position: absolute; bottom: calc(100% + 4px); left: 50%; transform: translateX(-50%); white-space: nowrap; font-size: 0.8rem; font-weight: 700; }
.meter-mark.consenso span { color: var(--secundario); font-weight: 600; bottom: auto; top: calc(100% + 4px); }
.meter-scale { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--secundario); padding-top: 18px; font-variant-numeric: tabular-nums; }
.meter-legend { font-size: 0.8rem; color: var(--secundario); }
.sw { display: inline-block; width: 12px; height: 12px; margin-right: 6px; vertical-align: -1px; border-radius: 3px; }
.sw.band { background: var(--banda); }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td { text-align: left; padding: 9px 8px; border-bottom: 1px solid var(--linea-tabla); vertical-align: top; }
tr:last-child td { border-bottom: 0; }
th { font-weight: 600; color: var(--secundario); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
td { font-variant-numeric: tabular-nums; }
.muted { color: var(--secundario); font-size: 0.8rem; }
.tag { white-space: nowrap; }
.tag span { display: inline-block; font-size: 0.74rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; }
.tag.rojo span { background: var(--pill-rojo); }
.tag.verde span { background: var(--pill-verde); }
.tag.gris span { background: var(--pill-gris); color: var(--secundario); }
.table-scroll { max-height: 640px; overflow: auto; }
.table-scroll thead th { position: sticky; top: 0; background: var(--tarjeta); }
.lista { margin: 0; padding-left: 1.1em; display: grid; gap: 8px; font-size: 0.92rem; line-height: 1.45; }
.lista li::marker { color: var(--secundario); }
a { color: var(--azul); }
.tabs { display: flex; gap: 8px; padding: 12px 18px 4px; flex-wrap: wrap; }
.tabs button { background: var(--pista); color: var(--secundario); border: 1px solid var(--borde); border-radius: 999px;
  padding: 5px 14px; font: inherit; font-size: 0.82rem; font-weight: 600; cursor: pointer; }
.tabs button[aria-selected=true] { background: var(--pill-verde); border-color: var(--verde); color: var(--texto); }
.hidden { display: none; }
body { margin: 0; padding-left: max(12px, env(safe-area-inset-left, 0px)); padding-right: max(12px, env(safe-area-inset-right, 0px)); padding-block: 0 24px; }
.page { max-width: 1440px; margin: 0 auto; display: grid; gap: 16px; padding-top: 16px; }
.topbar { background: var(--titulo); color: var(--texto-barra); padding: 20px 26px; border-radius: 12px;
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; box-shadow: var(--sombra-barra); }
.topbar h1 { margin: 0; font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em; }
.topbar .sub { font-size: 0.9rem; opacity: 0.9; margin-top: 4px; }
.meta { display: grid; gap: 3px; font-size: 0.82rem; text-align: right; opacity: 0.95; }
@media (max-width: 700px) { .meta { text-align: left; } }
.fila { display: grid; gap: 16px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.fila.kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.fila.una { grid-template-columns: minmax(0, 1fr); }
.nota { font-size: 0.8rem; color: var(--secundario); line-height: 1.45; padding: 10px 18px 14px; border-top: 1px solid var(--linea-tabla); }
.nota b { color: var(--texto); }
.pos { color: var(--verde); } .neg { color: var(--rojo); } .neu { color: var(--ambar); } .gris { color: var(--secundario); }
.card-head p b { font-weight: 700; }
.hall-key { font-size: 0.8rem; color: var(--secundario); margin-bottom: 14px; line-height: 1.5; }
.hall-grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(255px, 1fr)); }
.hall { background: var(--fondo); border: 1px solid var(--borde); border-top: 3px solid var(--secundario); border-radius: 10px;
  padding: 14px; display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.hall.t-pos { border-top-color: var(--verde); } .hall.t-neg { border-top-color: var(--rojo); } .hall.t-neu { border-top-color: var(--ambar); }
.hall-top { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px; }
.hall h3 { margin: 0; font-size: 1.02rem; font-weight: 800; letter-spacing: -0.01em; }
.hall h3 .muted { font-weight: 500; }
.verdict { font-size: 0.7rem; font-weight: 700; padding: 3px 9px; border-radius: 999px; white-space: nowrap; }
.verdict.pos { background: var(--pill-verde); } .verdict.neg { background: var(--pill-rojo); } .verdict.neu { background: rgba(224, 181, 74, 0.16); }
.deltas { display: grid; gap: 8px; }
.delta { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 8px; padding: 8px 10px 7px; display: grid; gap: 4px; }
.delta-row { display: flex; flex-wrap: wrap; align-items: baseline; column-gap: 8px; row-gap: 0; }
.delta-row .sig { flex-basis: 100%; }
.delta .lbl { font-size: 0.66rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--secundario); }
.delta .val { font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.delta .chg { font-size: 0.78rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.delta .sig { font-size: 0.66rem; color: var(--secundario); }
.mini { display: grid; gap: 3px; }
.mini-track { position: relative; height: 8px; background: var(--pista); border-radius: 999px; }
.mini-ci { position: absolute; top: 0; bottom: 0; border-radius: 999px; }
.mini-med { position: absolute; top: -4px; bottom: -4px; width: 2px; background: var(--texto); transform: translateX(-50%); }
.mini-dot { position: absolute; top: 50%; width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--fondo);
  transform: translate(-50%, -50%); }
.mini-scale { display: flex; justify-content: space-between; font-size: 0.66rem; color: var(--secundario); }
.insight { font-size: 0.9rem; line-height: 1.45; }
.interp { font-size: 0.82rem; line-height: 1.45; color: var(--secundario); }
.hyp { font-size: 0.78rem; line-height: 1.4; color: var(--secundario); font-style: italic; background: rgba(224, 181, 74, 0.07);
  border-left: 3px solid var(--ambar); border-radius: 0 6px 6px 0; padding: 7px 10px; margin-top: auto; }
.hyp span { display: block; font-style: normal; font-weight: 700; font-size: 0.64rem; letter-spacing: 0.07em;
  text-transform: uppercase; color: var(--ambar); margin-bottom: 2px; }
.chart-scroll { overflow-x: auto; padding: 6px 4px 0; }
.chart-scroll > div { min-width: 560px; }
footer { font-size: 0.8rem; color: var(--secundario); display: grid; gap: 4px; padding: 4px 6px; line-height: 1.5; }
footer ul { margin: 0; padding-left: 1.1em; }
a:focus-visible, .tabs button:focus-visible { outline: 2px solid var(--azul); outline-offset: 2px; }
@media (max-width: 980px) { .fila, .fila.kpis { grid-template-columns: minmax(0, 1fr); } }
@media (min-width: 600px) and (max-width: 980px) { .fila.kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/4.1.1/plotly.min.js"></script>
</head><body>
"""

TAIL = """
<script>
document.querySelectorAll('.tabs button').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('.tabs button').forEach(function (x) {
      var on = x === b; x.setAttribute('aria-selected', on);
      document.getElementById(x.dataset.target).classList.toggle('hidden', !on);
    });
    var el = document.querySelector('#' + b.dataset.target + ' .plotly-graph-div');
    if (el && window.Plotly) Plotly.Plots.resize(el);
  });
});
if (document.fonts && window.Plotly) {
  document.fonts.ready.then(function () {
    document.querySelectorAll(".plotly-graph-div").forEach(function (gd) { Plotly.relayout(gd, {}); });
  });
}
</script>
</body></html>
"""
