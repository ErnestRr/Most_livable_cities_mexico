"""Gráficas estáticas editoriales (matplotlib) para notebook y redes sociales.

Identidad propia del proyecto (plantilla común a todas las figuras):
- fondo azul pizarra; título alineado a la izquierda con barra de acento verde azulado
  y subtítulo con periodo y universo;
- ejes abiertos (solo izquierdo e inferior), líneas finas y cuadrícula tenue;
- leyendas y recuadros con relleno suave (sin contorno blanco) y valores en negrita;
- recuadros «¿Cómo leer?» que explican en lenguaje llano cada indicador;
- pie con fuente y datos agregados (izquierda) y firma opcional (derecha).
Paleta validada (dataviz/validate_palette.js, modo oscuro sobre #161b24):
verde azulado #1fa596 y coral #e5683f; gris para lo no concluyente.
"""
from pathlib import Path
import json

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from pyproj import Transformer

from src.visualization import Q_LABEL, labels_to_show, short_name

ROOT = Path(__file__).resolve().parents[1]
FIRMA = ""  # p. ej. "@tu_usuario"; vacío = sin firma

FIG, PANEL, BOX = "#161b24", "#161b24", "#1f2633"
AXIS, GRID = "#5b6578", "#283041"
TEXT, TEXT2, MUTED, INK = "#f1f3f7", "#c3c9d4", "#8a93a3", "#0f141c"  # INK: texto sobre marcas de color
TEAL, CORAL, NEUTRAL = "#1fa596", "#e5683f", "#7d8697"
SLATE, SAND, GOLD = "#8592ad", "#a8946c", "#d6b25e"
OCEAN, LAND, NODATA = "#0e1726", "#000000", "#000000"
Q_COLOR = {1: TEAL, 2: SLATE, 3: SAND, 4: CORAL}
Q_TEXT = {1: "Más barata · más segura", 2: "Más cara · más segura",
          3: "Más barata · menos segura", 4: "Más cara · menos segura"}
# Secuencial de una familia (azul noche -> verde azulado -> menta), luminosidad creciente.
SEQ = LinearSegmentedColormap.from_list(
    "noche_menta", ["#1b2a3a", "#1d4a5a", "#1f6f75", "#2a968a", "#5dbd9c", "#a9dfbf", "#eaf7e4"])
DIVERGING = LinearSegmentedColormap.from_list("verde_coral", [TEAL, "#2a313d", CORAL])
HALO = [pe.withStroke(linewidth=2.2, foreground=FIG)]

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 10,
    "figure.facecolor": FIG, "axes.facecolor": PANEL, "savefig.facecolor": FIG,
    "axes.edgecolor": AXIS, "axes.labelcolor": TEXT, "xtick.color": TEXT, "ytick.color": TEXT,
    "text.color": TEXT, "grid.color": GRID, "grid.linewidth": 0.4, "axes.axisbelow": True,
    "xtick.labelcolor": TEXT, "ytick.labelcolor": TEXT,
})


# --------------------------------------------------------------------------- plantilla
def figure(w_px, h_px, rect, dpi=200):
    """Figura y panel principal; rect = (izq, abajo, ancho, alto) en fracción de figura."""
    fig = plt.figure(figsize=(w_px / dpi, h_px / dpi), dpi=dpi)
    return fig, fig.add_axes(rect)


def frame(ax, grid="both", box=False):
    """Ejes abiertos (izquierdo e inferior) finos y cuadrícula tenue; box=True cierra el marco."""
    for side, s in ax.spines.items():
        s.set_visible(box or side in ("left", "bottom"))
        s.set_color(AXIS)
        s.set_linewidth(0.6)
    if grid:
        ax.grid(True, axis=grid, color=GRID, lw=0.4)
    ax.tick_params(colors=TEXT, length=2.5, width=0.5, labelsize=9, pad=4)


def _parts(line):
    if isinstance(line, str):
        return [(line, False)]
    return [line] if isinstance(line, tuple) else line


def rich_text(fig, x, y, parts, size, ha="center", va="top", color=TEXT):
    """Texto de una línea con tramos normales y en negrita: [(texto, negrita), ...]."""
    renderer = fig.canvas.get_renderer()
    objs = [fig.text(0, y, t, fontsize=size, fontweight="bold" if b else "normal", color=color,
                     va=va, ha="left", parse_math=False) for t, b in parts]
    widths = [o.get_window_extent(renderer).width / fig.bbox.width for o in objs]
    start = {"center": x - sum(widths) / 2, "right": x - sum(widths)}.get(ha, x)
    for o, w in zip(objs, widths):
        o.set_x(start)
        start += w
    return objs


def header(fig, title_parts, subtitle=None, size=16, top=0.975, left=0.022):
    """Título alineado a la izquierda con barra de acento y subtítulo debajo."""
    lines = title_parts if isinstance(title_parts[0], list) else [title_parts]
    y = top
    step = size * 1.45 / 72 / fig.get_figheight()
    x = left + 14 / fig.bbox.width
    for parts in lines:
        rich_text(fig, x, y, parts, size, ha="left")
        y -= step
    bottom = y + step * 0.18
    if subtitle:
        subtitle = subtitle[1:-1] if subtitle.startswith("(") and subtitle.endswith(")") else subtitle
        subtitle = subtitle[0].upper() + subtitle[1:]
        fig.text(x, y - 0.002, subtitle, ha="left", va="top", fontsize=size * 0.64, color=TEXT2,
                 parse_math=False)
        bottom = y - size * 0.64 * 1.25 / 72 / fig.get_figheight()
    fig.add_artist(Rectangle((left, bottom), 5 / fig.bbox.width, top - bottom, transform=fig.transFigure,
                             color=TEAL, lw=0))


def footer(fig, parts, center=None, y=0.012):
    """Pie: fuente y datos agregados (con negritas) a la izquierda, firma a la derecha."""
    rich_text(fig, 0.022, y, _parts(parts), 8.2, ha="left", va="bottom", color=MUTED)
    if center:
        fig.text(0.5, y, center, fontsize=8.6, color=TEXT, va="bottom", ha="center", parse_math=False)
    if FIRMA:
        fig.text(0.988, y, FIRMA, fontsize=8.2, color=TEXT2, va="bottom", ha="right")


def info_box(ax, x, y, lines, anchor="ur", size=8.4, bg=BOX, zorder=20):
    """Recuadro de relleno suave. lines: str o [(texto, negrita), ...]; anchor: ul/ur/ll/lr."""
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    px = size * fig.dpi / 72
    line_h, pad = px * 1.42, px * 0.75
    rows = []
    for line in lines:
        objs = [ax.text(0, 0, t, fontsize=size, fontweight="bold" if b else "normal", color=TEXT,
                        transform=ax.transAxes, va="top", ha="left", zorder=zorder + 1, parse_math=False)
                for t, b in _parts(line)]
        rows.append((objs, [o.get_window_extent(renderer).width for o in objs]))
    w = max(sum(ws) for _, ws in rows) + 2 * pad
    h = len(rows) * line_h + 1.4 * pad
    ax_x, ax_y = ax.transAxes.transform((x, y))
    left = ax_x - (w if anchor[1] == "r" else 0)
    top = ax_y + (h if anchor[0] == "l" else 0)
    inv = ax.transAxes.inverted()
    for i, (objs, ws) in enumerate(rows):
        cursor = left + pad
        for o, wi in zip(objs, ws):
            o.set_position(inv.transform((cursor, top - pad - i * line_h)))
            cursor += wi
    (x0, y0), (x1, y1) = inv.transform((left, top - h)), inv.transform((left + w, top))
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, transform=ax.transAxes, facecolor=bg,
                           edgecolor=GRID, lw=0.5, zorder=zorder, clip_on=False))


def legend(ax, handles, loc, size=8.4, ncol=1, anchor=None):
    lg = ax.legend(handles=handles, loc=loc, fontsize=size, frameon=True, borderpad=0.8, ncol=ncol,
                   bbox_to_anchor=anchor, columnspacing=1.4,
                   handletextpad=0.6, labelspacing=0.55, facecolor=BOX, edgecolor=GRID, framealpha=1)
    lg.get_frame().set_linewidth(0.5)
    for t in lg.get_texts():
        t.set_color(TEXT)
    lg.set_zorder(20)
    return lg


def money(v, _=None):
    return f"${v:,.0f}"


def b(text):
    return (text, True)


def n(text):
    return (text, False)


def save(fig, path, svg=False):
    fig.savefig(path)
    if svg:
        fig.savefig(Path(path).with_suffix(".svg"))
    return fig


def _dot(color, label, ms=9):
    return Line2D([], [], marker="o", ls="", ms=ms, mfc=color, mec=FIG, label=label)


# --------------------------------------------------------------------------- 1. dispersión
def scatter_quadrants(df, meta, path, size_px):
    w, h = size_px
    vertical = h > w
    rect = [0.115, 0.27, 0.86, 0.565] if vertical else [0.072, 0.135, 0.91, 0.705]
    fig, ax = figure(w, h, rect)
    x_med, y_med = meta["mediana_costo"], meta["mediana_seguridad"]
    xpad = (df.costo_canasta.max() - df.costo_canasta.min()) * 0.06
    x0, x1 = df.costo_canasta.min() - xpad, df.costo_canasta.max() + xpad
    ax.add_patch(Rectangle((x0, y_med), x_med - x0, 100 - y_med, color=TEAL, alpha=0.07, lw=0))
    ax.add_patch(Rectangle((x_med, 0), x1 - x_med, y_med, color=CORAL, alpha=0.07, lw=0))
    size = 95 if vertical else 120
    for q in [2, 3, 1, 4]:
        d = df[df.cuadrante == q]
        ax.scatter(d.costo_canasta, d.seguridad_pct, s=size, color=Q_COLOR[q], edgecolor=FIG,
                   linewidth=0.9, zorder=3)
        r = d[d.cuadrante_robusto]
        ax.scatter(r.costo_canasta, r.seguridad_pct, s=size * 1.35, color=Q_COLOR[q], edgecolor=TEXT,
                   linewidth=2.0, zorder=4)
    ax.axvline(x_med, color=TEXT2, lw=0.7, ls=(0, (4, 3)), zorder=2)
    ax.axhline(y_med, color=TEXT2, lw=0.7, ls=(0, (4, 3)), zorder=2)
    frame(ax)
    ax.set(xlim=(x0, x1), ylim=(0, 100))
    ax.xaxis.set_major_formatter(money)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlabel("Costo de la canasta comparable (pesos; mediana entre supermercados)", labelpad=6)
    ax.set_ylabel("Población de 18+ que se siente segura en su ciudad", labelpad=6)
    # Nombre de cada cuadrante, escrito en su esquina y en su color.
    qs = 7.4 if vertical else 8.4
    dx = (x1 - x0) * 0.012
    for q, (x, y, ha, va) in {1: (x0 + dx, 98, "left", "top"), 2: (x_med + dx, 98, "left", "top"),
                              3: (x_med - dx, 1.5, "right", "bottom"), 4: (x1 - dx, 1.5, "right", "bottom")}.items():
        ax.text(x, y, Q_TEXT[q].upper(), ha=ha, va=va, fontsize=qs, fontweight="bold", color=Q_COLOR[q],
                zorder=6, path_effects=HALO)
    texts = [ax.text(r.costo_canasta + dx * 0.6, r.seguridad_pct + 1.2, short_name(r.area_urbana_ensu),
                     fontsize=8, color=TEXT, zorder=5, path_effects=HALO)
             for r in df[df.area_urbana_ensu.isin(labels_to_show(df))].itertuples()]
    adjust_text(texts, ax=ax, x=df.costo_canasta.to_numpy(), y=df.seguridad_pct.to_numpy(),
                arrowprops=dict(arrowstyle="-", color=TEXT2, lw=0.5), expand=(1.15, 1.35),
                force_static=(0.3, 0.6), force_pull=(0.04, 0.08), ensure_inside_axes=True)
    handles = [Line2D([], [], marker="o", ls="", ms=8, mfc=NEUTRAL, mec=TEXT, mew=2,
                      label="Contorno blanco: posición confirmada (IC 90%)"),
               Line2D([], [], color=TEXT2, lw=0.8, ls=(0, (4, 3)), label="Punteadas: mediana de las 44 áreas")]
    if vertical:  # debajo del panel para no tapar datos
        legend(ax, [_dot(Q_COLOR[q], Q_TEXT[q], 8) for q in (1, 2, 3, 4)] + handles, "upper left",
               size=6.9, anchor=(-0.005, -0.125))
    else:
        legend(ax, handles, "lower left", size=7.0, anchor=(0.003, 0.045))
    info_box(ax, 1.0 if vertical else 0.99, -0.127 if vertical else 0.985, [b("Datos clave"),
                                [n("Áreas urbanas: "), b(f"{meta['areas']}")],
                                [n("Costo típico (mediana): "), b(money(x_med))],
                                [n("Seguridad típica (mediana): "), b(f"{y_med:.1f}%")],
                                [n("Más cara vs. más barata: "), b(f"+{meta['rango_costo_pct']:.1f}%")],
                                [n("Relación costo–seguridad: "), b(f"{meta['spearman']:+.2f}")],
                                n("(0 = sin relación; ±1 = relación total)")],
             "ur", size=6.9 if vertical else 7.0)
    if vertical:
        header(fig, [[n("¿Dónde cuesta "), b("menos la canasta")],
                     [n("y se percibe "), b("mayor seguridad"), n(" en México?")]],
               f"(canasta de {meta['productos']} productos vs. percepción de seguridad; agosto y junio de 2026)",
               size=16, top=0.975)
    else:
        header(fig, [n("¿Dónde cuesta "), b("menos la canasta"), n(" y se percibe "),
                     b("mayor seguridad"), n(" en México?")],
               f"(canasta comparable de {meta['productos']} productos vs. percepción de seguridad urbana; agosto y junio de 2026)",
               size=15.5, top=0.97)
    footer(fig, [n("Fuente: PROFECO (ago 2026) e INEGI ENSU (jun 2026). Mediana: "),
                 b(money(x_med)), n(" por canasta; "), b(f"{y_med:.1f}%"), n(" seguro.")])
    return save(fig, path, svg=True)


# --------------------------------------------------------------------------- 2. rankings
def _dot_ci(d, value, lo, hi, ref, fmt, xfmt, title, subtitle, xlabel, source_parts, path,
            colors, legend_items, legend_loc, note_lines, note_anchor, ref_label):
    rows = len(d)
    row_px = 60
    hpx = 350 + row_px * rows
    fig, ax = figure(1700, hpx, [0.19, 150 / hpx, 0.785, 1 - 330 / hpx])
    y = np.arange(rows)
    # Margen de error: banda translúcida del color del punto con remates en los extremos.
    ax.hlines(y, d[lo], d[hi], color=colors, lw=8, alpha=0.38, zorder=2)
    for end in (lo, hi):
        ax.scatter(d[end], y, marker="|", s=110, color=colors, linewidths=1.4, zorder=2)
    ax.scatter(d[value], y, s=480, color=colors, edgecolor=FIG, linewidth=1.4, zorder=3)
    for yi, v in zip(y, d[value]):
        label = fmt(v)
        ax.text(v, yi, label, ha="center", va="center", fontsize=7.8 if len(label) <= 4 else 6.9,
                fontweight="bold", color=INK, zorder=4)
    ax.axvline(ref, color=TEXT2, lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.set_yticks(y, [short_name(a) for a in d.area_urbana_ensu], fontsize=8.6)
    ax.set_ylim(rows - 0.4, -1.4)
    ax.text(ref, -1.05, f"{ref_label}: {xfmt(ref, None)}", ha="center", va="center", fontsize=7.6, color=TEXT2,
            fontweight="bold", path_effects=HALO)
    span = d[hi].max() - d[lo].min()
    ax.set_xlim(d[lo].min() - span * 0.04, d[hi].max() + span * 0.2)
    # Etiqueta directa del margen de error en la primera fila.
    ax.annotate("margen de error\n(rango probable, 90%)", xy=(d[hi].iloc[0], 0), xytext=(12, 0),
                textcoords="offset points", ha="left", va="center", fontsize=7.2, color=TEXT2,
                arrowprops=dict(arrowstyle="-", color=TEXT2, lw=0.5))
    frame(ax, grid="x")
    ax.tick_params(axis="y", length=0)
    ax.xaxis.set_major_formatter(xfmt)
    handles = [_dot(c, l) for l, c in legend_items] + \
              [Line2D([], [], color=MUTED, lw=7, alpha=0.6, label="Margen de error (IC 90%)"),
               Line2D([], [], color=TEXT2, lw=0.8, ls=(0, (4, 3)), label="Mediana de las 44 áreas")]
    legend(ax, handles, legend_loc, size=8)
    nx, ny = {"ll": (0.012, 0.012), "ul": (0.012, 0.975), "lr": (0.988, 0.012), "ur": (0.988, 0.975)}[note_anchor]
    info_box(ax, nx, ny, [b("¿Cómo leer?"),
                          "La barra translúcida es el margen de error:",
                          "el valor real está casi seguro dentro de ella.",
                          "Si la barra no toca la línea punteada,",
                          "la diferencia con la mediana es clara (color).",
                          "Si la toca, no es concluyente (gris)."] + note_lines, note_anchor, size=7.6)
    ax.set_xlabel(xlabel, labelpad=7)
    header(fig, title, subtitle, size=16, top=1 - 34 / hpx)
    footer(fig, source_parts)
    return save(fig, path)


def ranking_cost(df, path):
    d = df.sort_values("costo_canasta").reset_index(drop=True)
    med = d.costo_canasta.median()
    colors = np.where(d.costo_ic90_sup < med, TEAL, np.where(d.costo_ic90_inf > med, CORAL, NEUTRAL))
    return _dot_ci(d, "costo_canasta", "costo_ic90_inf", "costo_ic90_sup", med, lambda v: f"{v:,.0f}", money,
                   [n("Costo de la "), b("canasta comparable"), n(" por área urbana")],
                   "(pesos por canasta de 21 productos en supermercados, 16–31 de agosto de 2026)",
                   "Costo de la canasta (pesos corrientes)",
                   [n("Fuente: PROFECO (2026). Mediana: "), b(money(med)), n("; mínimo "),
                    b(money(d.costo_canasta.min())), n(", máximo "), b(money(d.costo_canasta.max()))],
                   path, colors, [("Más barata que la mediana (clara)", TEAL),
                                  ("Más cara que la mediana (clara)", CORAL),
                                  ("No concluyente", NEUTRAL)], "upper right",
                   [n(""), [n("Margen calculado con "), b("1,000 simulaciones")],
                    "que cambian las tiendas observadas."], "ll", "Mediana")


def ranking_security(df, path):
    d = df.sort_values("seguridad_pct", ascending=False).reset_index(drop=True)
    med = d.seguridad_pct.median()
    colors = np.where(d.ic90_inf_seguro > med, TEAL, np.where(d.ic90_sup_seguro < med, CORAL, NEUTRAL))
    return _dot_ci(d, "seguridad_pct", "ic90_inf_seguro", "ic90_sup_seguro", med, lambda v: f"{v:.1f}",
                   lambda v, _: f"{v:.0f}%",
                   [n("Población que se siente "), b("segura"), n(" en su ciudad")],
                   "(personas de 18 años y más en las 44 áreas urbanas del análisis, junio de 2026)",
                   "Porcentaje de la población de 18 años y más",
                   [n("Fuente: INEGI, ENSU (jun 2026). Mediana: "), b(f"{med:.1f}%"), n("; nacional (91 áreas): "),
                    b("40.0%")], path, colors,
                   [("Más segura que la mediana (clara)", TEAL), ("Menos segura que la mediana (clara)", CORAL),
                    ("No concluyente", NEUTRAL)], "lower right",
                   [n(""), [n("Margen publicado por "), b("INEGI"), n(": la encuesta")],
                    "entrevista a una muestra, no a todos."], "ul", "Mediana")


# --------------------------------------------------------------------------- 3. productos
def dispersion_lollipop(disp, names, path):
    d = disp.sort_values("cv_pct", ascending=False)
    fig, ax = figure(2000, 1250, [0.065, 0.235, 0.92, 0.6])
    x = np.arange(len(d))
    colors = [CORAL if i < 5 else TEAL for i in range(len(d))]
    ax.vlines(x, 0, d.cv_pct, color=colors, lw=2.6, zorder=2)
    ax.scatter(x, d.cv_pct, s=680, color=colors, edgecolor=FIG, linewidth=1.5, zorder=3)
    for xi, cv, r in zip(x, d.cv_pct, d.razon_max_min):
        ax.text(xi, cv, f"{cv:.1f}", ha="center", va="center", fontsize=7.8, fontweight="bold", color=INK, zorder=4)
        ax.annotate(f"{r:.1f}×", (xi, cv), xytext=(0, 16), textcoords="offset points", ha="center",
                    va="bottom", fontsize=7.2, color=TEXT2)
    ax.set_xticks(x, [names[i] for i in d.index], rotation=45, ha="right", fontsize=8.4)
    ax.set(ylim=(0, d.cv_pct.max() * 1.2), xlim=(-0.7, len(d) - 0.3))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    frame(ax, grid="y")
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("Variación del precio entre ciudades (%)", labelpad=7)
    legend(ax, [_dot(CORAL, "Cinco productos que más cambian"), _dot(TEAL, "Resto de la canasta")],
           "upper center", size=8.2)
    info_box(ax, 0.988, 0.975, [b("¿Cómo leer?"),
                                [n("Número en el círculo: "), b("variación típica (%)")],
                                "   cuánto se aleja el precio de cada ciudad",
                                "   del promedio nacional (coef. de variación).",
                                [n("Número arriba (×): "), b("ciudad más cara ÷ más barata")],
                                "   2.0× = en una ciudad cuesta el doble.",
                                [n("Promedio de los 21 productos: "), b(f"{d.cv_pct.mean():.1f}%")],
                                [n("Producto de en medio (mediana): "), b(f"{d.cv_pct.median():.1f}%")]], "ur", size=7.8)
    header(fig, [n("¿Qué productos "), b("cambian más de precio"), n(" entre ciudades?")],
           "(precio mediano por área urbana en supermercados; 44 áreas, 16–31 de agosto de 2026)", top=0.965)
    footer(fig, [n("Fuente: PROFECO (2026). Productos con variación > 10%: "), b(f"{(d.cv_pct > 10).sum()} de {len(d)}")])
    return save(fig, path)


def store_spread(store_index, names, order, path):
    """Diferencias de precio entre tiendas por producto: rango (mediana, media, mitad central,
    9 de cada 10 tiendas) y reparto de tiendas más baratas / similares / más caras que lo típico."""
    s = store_index[store_index.producto_normalizado.isin(order)]
    g = s.groupby("producto_normalizado").indice
    st = pd.DataFrame({"n": g.size(), "media": g.mean(), "p05": g.quantile(.05), "p25": g.quantile(.25),
                       "p50": g.median(), "p75": g.quantile(.75), "p95": g.quantile(.95),
                       "barata": g.apply(lambda v: (v < 90).mean() * 100),
                       "cara": g.apply(lambda v: (v > 110).mean() * 100)})
    st["similar"] = 100 - st.barata - st.cara
    st = st.assign(iqr=st.p75 - st.p25).sort_values("iqr", ascending=False)
    k, row = len(st), 62
    top_px, key_px, bot_px = 150, 300, 205
    hpx = top_px + key_px + row * k + bot_px
    W = 2000
    fig = plt.figure(figsize=(W / 200, hpx / 200), dpi=200)
    pb, ph = bot_px / hpx, row * k / hpx
    ax = fig.add_axes([0.2, pb, 0.47, ph])
    ax2 = fig.add_axes([0.71, pb, 0.27, ph], sharey=ax)
    y = np.arange(k)
    lo, hi = 40, 180
    # Panel izquierdo: rango de precios.
    ax.hlines(y, st.p05.clip(lo, hi), st.p95.clip(lo, hi), color=MUTED, lw=1.3, zorder=2)
    ax.hlines(y, st.p25, st.p75, color=SLATE, lw=11, zorder=3)
    ax.scatter(st.media, y, marker="D", s=34, facecolor=FIG, edgecolor=GOLD, linewidth=1.3, zorder=5)
    ax.scatter(st.p50, y, s=70, color=TEXT, edgecolor=FIG, linewidth=1, zorder=4)
    for yi, (lo_v, hi_v) in enumerate(zip(st.p05, st.p95)):  # flechas si el 90 % central sale del eje
        if lo_v < lo:
            ax.annotate("", (lo, yi), (lo + 5, yi), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.1))
        if hi_v > hi:
            ax.annotate("", (hi, yi), (hi - 5, yi), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.1))
    ax.axvline(100, color=TEXT2, lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.set(xlim=(lo, hi), ylim=(k - 0.5, -0.6))
    ax.set_xticks(range(50, 181, 25))
    ax.xaxis.set_major_formatter(lambda v, _: "100\ntípico" if v == 100 else f"{v:.0f}\n{v - 100:+.0f}%")
    ax.set_yticks(y, [""] * k)
    frame(ax, grid="x")
    ax.tick_params(axis="y", length=0)
    for yi, (item, r) in enumerate(st.iterrows()):
        ax.text(-0.015, yi - 0.12, names[item], transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=8.8, fontweight="bold")
        ax.text(-0.015, yi + 0.26, f"{r.n:.0f} tiendas · mediana {r.p50:.0f} · media {r.media:.0f}",
                transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=6.6, color=TEXT2)
    ax.set_xlabel("Precio de la tienda vs. precio típico del producto (100 = típico)", labelpad=6)
    ax.set_title("Rango de precios entre tiendas", loc="left", fontsize=9.6, fontweight="bold", pad=8)
    # Panel derecho: de cada 100 tiendas, cuántas cobran menos, similar o más.
    left = np.zeros(k)
    for col, color in [("barata", TEAL), ("similar", NEUTRAL), ("cara", CORAL)]:
        vals = st[col].to_numpy()
        ax2.barh(y, vals, left=left, height=0.62, color=color, edgecolor=FIG, linewidth=1.2, zorder=3)
        for yi, (l, v) in enumerate(zip(left, vals)):
            if v >= 8:
                ax2.text(l + v / 2, yi, f"{v:.0f}", ha="center", va="center", fontsize=7.4, fontweight="bold",
                         color=INK, zorder=4)
        left += vals
    ax2.set_xlim(0, 100)
    ax2.set_xticks([0, 25, 50, 75, 100])
    ax2.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}")
    frame(ax2, grid=None)
    ax2.spines["left"].set_visible(False)
    ax2.tick_params(axis="y", length=0, labelleft=False)
    ax2.set_xlabel("Número de tiendas de cada 100", labelpad=6)
    ax2.set_title("De cada 100 tiendas, ¿cuántas cobran…?", loc="left", fontsize=9.6, fontweight="bold", pad=8)
    # Clave «¿Cómo leer?» con un ejemplo dibujado.
    key = fig.add_axes([0.2, (bot_px + row * k + 52) / hpx, 0.78, (key_px - 70) / hpx])
    key.set(xlim=(0, 100), ylim=(0, 1))
    key.axis("off")
    key.add_patch(Rectangle((-26, 0), 126, 1, facecolor=BOX, edgecolor=GRID, lw=0.5, clip_on=False, zorder=0))
    key.text(-24.5, 0.9, "¿Cómo leer?", fontsize=9.4, fontweight="bold", va="top")
    ky = 0.44
    key.hlines(ky, 6, 47, color=MUTED, lw=1.3)
    key.hlines(ky, 18, 38, color=SLATE, lw=11)
    key.scatter([26], [ky], s=70, color=TEXT, edgecolor=FIG, zorder=4)
    key.scatter([31], [ky], marker="D", s=34, facecolor=FIG, edgecolor=GOLD, linewidth=1.3, zorder=5)
    tk = dict(fontsize=7.3, color=TEXT2, va="center")
    arrow = dict(arrowstyle="-", color=MUTED, lw=0.5)
    key.annotate("Línea delgada: 9 de cada 10 tiendas\ncobran dentro de este rango", (7, ky), (-24.5, 0.62),
                 ha="left", arrowprops=arrow, **tk)
    key.annotate("Barra gruesa: la mitad de las tiendas\n(las de en medio) cobra aquí", (20, ky), (-24.5, 0.2),
                 ha="left", arrowprops=arrow, **tk)
    key.annotate("Punto blanco = mediana: la tienda de en medio;\nla mitad cobra menos y la mitad más", (26, ky),
                 (34, 0.8), ha="left", arrowprops=arrow, **tk)
    key.annotate("Rombo = media (promedio): sube si hay\nunas pocas tiendas muy caras", (31, ky), (40, 0.14),
                 ha="left", arrowprops=arrow, **tk)
    key.text(51, 0.47, "Barra larga = mucha\ndiferencia entre tiendas:\nconviene comparar.",
             fontsize=7.3, color=TEXT, va="center", fontweight="bold")
    key.text(72, 0.9, "Barras de la derecha:", fontsize=7.3, color=TEXT, va="top", fontweight="bold")
    for i, (lab, color) in enumerate([("Más barata: >10% abajo del típico", TEAL),
                                      ("Similar al típico (±10%)", NEUTRAL),
                                      ("Más cara: >10% arriba del típico", CORAL)]):
        yy = 0.66 - i * 0.15
        key.add_patch(Rectangle((72, yy - 0.05), 1.8, 0.1, color=color, clip_on=False))
        key.text(74.6, yy, lab, fontsize=7.1, color=TEXT2, va="center")
    key.text(72, 0.12, "Precio típico (100) = mediana del producto\nentre las 44 áreas urbanas. 120 = 20% más caro.",
             fontsize=6.8, color=MUTED, va="center")
    header(fig, [n("¿Cuánto cambia el precio de un mismo producto "), b("de una tienda a otra"), n("?")],
           "(supermercados y tiendas de autoservicio en 44 áreas urbanas, 16–31 de agosto de 2026; "
           "productos ordenados de mayor a menor diferencia)", size=15.5, top=1 - 30 / hpx)
    footer(fig, [n("Fuente: PROFECO (2026). Precios por tienda y producto: "), b(f"{len(s):,}"),
                 n(". Producto con más diferencia: "), b(names[st.index[0]]),
                 n("; con menos: "), b(names[st.index[-1]])])
    return save(fig, path)


def relative_heatmap(rel, names, order, path):
    m = rel.loc[order]
    fig, ax = figure(2300, 2550, [0.15, 0.13, 0.75, 0.78])
    im = ax.imshow(m.to_numpy(), cmap=DIVERGING, vmin=70, vmax=130, aspect="auto")
    for (i, j), v in np.ndenumerate(m.to_numpy()):
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=5.4,
                    color=TEXT if abs(v - 100) > 12 else TEXT2)
    ax.set_yticks(range(len(m)), [short_name(a) for a in m.index], fontsize=7.8)
    ax.set_xticks(range(m.shape[1]), [names[c] for c in m.columns], rotation=50, ha="right", fontsize=8.2)
    ax.set_xticks(np.arange(-0.5, m.shape[1]), minor=True)
    ax.set_yticks(np.arange(-0.5, len(m)), minor=True)
    ax.grid(True, which="minor", color=FIG, lw=1.0)
    ax.tick_params(which="minor", length=0)
    frame(ax, grid=None, box=True)
    ax.tick_params(length=0)
    ax.grid(False, which="major")
    cax = fig.add_axes([0.915, 0.30, 0.014, 0.45])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("Índice de precio (100 = mediana de las áreas)", color=TEXT)
    cb.outline.set_edgecolor(AXIS)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(colors=TEXT, length=2.5, width=0.5)
    header(fig, [b("Precio relativo"), n(" de cada producto por área urbana")],
           "(áreas ordenadas de la canasta más barata a la más cara; verde azulado = más barato que la mediana)", top=0.975)
    footer(fig, [n("Fuente: PROFECO (16–31 ago 2026). Celdas con índice < 90: "), b(f"{int((m < 90).sum().sum())}"),
                 n("; > 110: "), b(f"{int((m > 110).sum().sum())}"), n(f" de {m.size}")])
    return save(fig, path)


def chains_lollipop(chains, path):
    d = chains.sort_values("indice_medio", ascending=False).reset_index(drop=True)
    hpx = 400 + 86 * len(d)
    fig, ax = figure(1700, hpx, [0.215, 195 / hpx, 0.76, 1 - 375 / hpx])
    y = np.arange(len(d))
    colors = [NEUTRAL if abs(v - 100) < 0.5 else TEAL if v < 100 else CORAL for v in d.indice_medio]
    ax.hlines(y, 100, d.indice_medio, color=colors, lw=3, zorder=2)
    ax.scatter(d.indice_medio, y, s=820, color=colors, edgecolor=FIG, lw=1.5, zorder=3)
    for yi, v in zip(y, d.indice_medio):
        ax.text(v, yi, f"{v:.1f}", ha="center", va="center", fontsize=8.4, fontweight="bold", color=INK, zorder=4)
    ax.axvline(100, color=TEXT2, lw=0.8, ls=(0, (4, 3)))
    ax.set_yticks(y, [f"{c}\n({a} áreas, {e} tiendas)" for c, a, e in
                      zip(d.cadena_comercial, d.areas, d.establecimientos)], fontsize=8.2)
    ax.set_ylim(len(d) - 0.4, -0.6)
    lim = max(abs(d.indice_medio - 100).max() + 3, 5)
    ax.set_xlim(100 - lim, 100 + lim)
    frame(ax, grid="x")
    ax.tick_params(axis="y", length=0)
    ax.xaxis.set_major_formatter(lambda v, _: "100\ntípico" if v == 100 else f"{v:.0f}\n{v - 100:+.0f}%")
    legend(ax, [_dot(TEAL, "Más barata que la mediana local"), _dot(CORAL, "Más cara que la mediana local"),
                _dot(NEUTRAL, "Igual a la mediana local (±0.5)")],
           "lower right", size=8)
    info_box(ax, 0.012, 0.012, [b("¿Cómo leer?"), "Solo cadenas en 5 o más áreas.", "Compara el mismo producto",
                                "en la misma área urbana.", "105 = cobra 5% más que lo típico."], "ll", size=7.6)
    header(fig, [n("¿Qué "), b("cadenas"), n(" cobran más por el mismo producto?")],
           "(precio por establecimiento relativo a la mediana local; productos de la canasta, agosto de 2026)",
           top=1 - 34 / hpx)
    footer(fig, [n("Fuente: PROFECO (2026). Diferencia entre la cadena más cara y la más barata: "),
                 b(f"{d.indice_medio.max() - d.indice_medio.min():.1f} puntos")])
    ax.set_xlabel("Índice medio de precio (100 = mediana del mismo producto en la misma área)", labelpad=7)
    return save(fig, path)


def ranking_table(df, path):
    d = df.sort_values("costo_canasta").reset_index(drop=True)
    cols = ["Pos.", "Área urbana", "Entidad", "Canasta", "IC 90% (pesos)", "Seguridad", "Cuadrante"]
    widths = np.array([0.06, 0.22, 0.17, 0.10, 0.15, 0.10, 0.20])
    xs = np.r_[0, np.cumsum(widths)[:-1]]
    rows = len(d)
    hpx = 330 + 40 * rows
    fig, ax = figure(1700, hpx, [0.04, 95 / hpx, 0.92, 40 * (rows + 1) / hpx])
    ax.set(xlim=(0, 1), ylim=(rows + 1, 0))
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 1, 1, color=BOX))
    ax.plot([0, 1], [1, 1], color=TEAL, lw=1.2)
    for x, w, c in zip(xs, widths, cols):
        ax.text(x + w / 2, 0.5, c, ha="center", va="center", fontsize=7.8, fontweight="bold", color=TEXT)
    for i, r in d.iterrows():
        yy = i + 1
        if i % 2:
            ax.add_patch(Rectangle((0, yy), 1, 1, facecolor="#1a202b", lw=0))
        qcol = Q_COLOR[r.cuadrante] if r.cuadrante in (1, 4) else TEXT
        vals = [f"{i + 1}", short_name(r.area_urbana_ensu), r.estado.split(" / ")[0], money(r.costo_canasta),
                f"{r.costo_ic90_inf:,.0f} – {r.costo_ic90_sup:,.0f}", f"{r.seguridad_pct:.1f}%", Q_LABEL[r.cuadrante]]
        for j, (x, w, v) in enumerate(zip(xs, widths, vals)):
            left = j in (1, 2, 6)
            ax.text(x + (0.01 if left else w / 2), yy + 0.5, v, ha="left" if left else "center", va="center",
                    fontsize=6.9, color=qcol if j == 6 else TEXT, parse_math=False,
                    fontweight="bold" if (j == 6 and r.cuadrante_robusto) or j == 3 else "normal")
    ax.plot([0, 1], [rows + 1, rows + 1], color=AXIS, lw=0.6)
    header(fig, [n("Ranking del "), b("costo de la canasta"), n(" y la seguridad percibida")],
           "(44 áreas urbanas, de menor a mayor costo; en negrita, cuadrante robusto con IC90)", size=14,
           top=1 - 30 / hpx)
    footer(fig, [n("Fuente: PROFECO (16–31 ago 2026) e INEGI ENSU (jun 2026). Mediana: "),
                 b(money(d.costo_canasta.median())), n(" y "), b(f"{d.seguridad_pct.median():.1f}%")], y=0.01)
    return save(fig, path)


# --------------------------------------------------------------------------- 4. mapas
_TO_LCC = Transformer.from_crs("EPSG:4326", "EPSG:6372", always_xy=True)
NEIGHBORS = ["USA", "GTM", "BLZ", "HND", "SLV", "CUB", "NIC", "BHS", "JAM", "CYM"]


def load_neighbors(path=ROOT / "data/raw/naturalearth/ne_50m_admin_0_countries.geojson"):
    """Países vecinos de Natural Earth proyectados a EPSG:6372 (misma proyección que INEGI)."""
    gj = json.loads(Path(path).read_text(encoding="utf-8"))
    rings = []
    for f in gj["features"]:
        if f["properties"]["ADM0_A3"] not in NEIGHBORS:
            continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            ring = np.asarray(poly[0])
            if ring[:, 0].max() < -125 or ring[:, 1].min() > 40:  # fuera del encuadre
                continue
            x, y = _TO_LCC.transform(ring[:, 0], ring[:, 1])
            rings.append(np.c_[x, y])
    return rings


def _mun_collection(mun, values, cmap, norm, lw):
    polys, colors = [], []
    for f in mun:
        v = values.get(f["props"]["CVEGEO"], np.nan)
        c = NODATA if pd.isna(v) else cmap(norm(v))
        for ring in f["rings"]:
            polys.append(ring)
            colors.append(c)
    return PolyCollection(polys, facecolors=colors, edgecolors="#111111", linewidths=lw)


def _map_layers(ax, mun, ent, neighbors, values, cmap, norm, detail=False):
    ax.set_facecolor(OCEAN)
    ax.add_collection(PolyCollection(neighbors, facecolors=LAND, edgecolors="#4d566a", linewidths=0.3))
    ax.add_collection(_mun_collection(mun, values, cmap, norm, lw=0.3 if detail else 0.05))
    ax.add_collection(PolyCollection([r for f in ent for r in f["rings"]], facecolors="none",
                                     edgecolors="#e6e9ef", linewidths=0.7 if detail else 0.4))


def inset_bounds(mun, cvegeos, pad=0.12):
    ids = set(cvegeos)
    pts = np.vstack([r for f in mun if f["props"]["CVEGEO"] in ids for r in f["rings"]])
    (x0, y0), (x1, y1) = pts.min(axis=0), pts.max(axis=0)
    cx, cy, half = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * (0.5 + pad)
    return cx - half, cy - half, cx + half, cy + half


def municipal_map(mun, ent, neighbors, values, area_values, title, unit_title, cbar_label, fmt,
                  footer_parts, path, insets, labels=None, n_mun=None, note_lines=None):
    """Mapa de calor municipal con océano, países vecinos, contornos estatales, barra de color,
    estadísticas descriptivas y recuadros ampliados en el Pacífico."""
    fig, ax = figure(2700, 1560, [0.012, 0.06, 0.976, 0.855])
    vals = pd.Series(list(area_values), dtype=float)
    norm = Normalize(vmin=np.floor(vals.min()), vmax=np.ceil(vals.max()))
    _map_layers(ax, mun, ent, neighbors, values, SEQ, norm)
    xs = np.concatenate([r[:, 0] for f in ent for r in f["rings"]])
    ys = np.concatenate([r[:, 1] for f in ent for r in f["rings"]])
    ax.set_xlim(xs.min() - 0.22 * np.ptp(xs), xs.max() + 0.06 * np.ptp(xs))
    ax.set_ylim(ys.min() - 0.16 * np.ptp(ys), ys.max() + 0.04 * np.ptp(ys))
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xticks([]); ax.set_yticks([])
    frame(ax, grid=None, box=True)
    ax.apply_aspect()
    boxes = {name: inset_bounds(mun, ids) for name, (ids, _) in insets.items()}
    for (x, y), name in labels or []:
        if not any(bx[0] <= x - 12000 <= bx[2] and bx[1] <= y <= bx[3] for bx in boxes.values()):
            ax.text(x, y, name, fontsize=7, color=TEXT, ha="left", va="center", zorder=6, path_effects=HALO)
    for i, (name, (ids, inset_labels)) in enumerate(insets.items()):
        bx = boxes[name]
        iax = ax.inset_axes([0.105 + i * 0.137, 0.025, 0.13, 0.25])
        _map_layers(iax, mun, ent, neighbors, values, SEQ, norm, detail=True)
        iax.set(xlim=(bx[0], bx[2]), ylim=(bx[1], bx[3]), xticks=[], yticks=[])
        iax.set_aspect("equal", adjustable="datalim")
        frame(iax, grid=None, box=True)
        iax.text(0.04, 0.96, f"{i + 1}. {name}", transform=iax.transAxes, fontsize=7.6, fontweight="bold",
                 va="top", zorder=7, path_effects=HALO)
        placed = []
        span = bx[2] - bx[0]
        char_w, text_h = span * 0.0235, span * 0.055  # 5.2 pt en un recuadro de ~340 px
        for x, y, lab in inset_labels:
            half = len(lab) * char_w / 2
            box = (x - half, y - text_h / 2, x + half, y + text_h / 2)
            if any(box[0] < q[2] and q[0] < box[2] and box[1] < q[3] and q[1] < box[3] for q in placed):
                continue
            placed.append(box)
            iax.text(x, y, lab, fontsize=5.2, ha="center", va="center", zorder=7, path_effects=HALO)
        ax.add_patch(Rectangle((bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1], fill=False, ec=TEXT, lw=0.6, zorder=8))
        ax.text(bx[2], bx[3], f"{i + 1}", fontsize=7, color=TEXT, va="bottom", ha="left", zorder=8, path_effects=HALO)
    cax = ax.inset_axes([0.03, 0.36, 0.013, 0.58])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=SEQ), cax=cax)
    cb.outline.set_edgecolor(AXIS)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(colors=TEXT, length=2.5, width=0.5, labelsize=7.5)
    cb.ax.yaxis.set_major_formatter(lambda v, _: fmt(v))
    cb.ax.yaxis.set_ticks_position("right")
    cb.set_label(cbar_label, color=TEXT, fontsize=8.6, labelpad=4)
    cb.ax.yaxis.set_label_position("left")
    stats = [b("Datos clave"), n(f"({unit_title})"),
             [n("Áreas urbanas: "), b(f"{len(vals)}")]]
    if n_mun:
        stats.append([n("Municipios con dato: "), b(f"{n_mun}")])
    stats += [[n("Promedio (media): "), b(fmt(vals.mean()))], [n("Área de en medio (mediana): "), b(fmt(vals.median()))],
              [n("Dispersión (desv. est.): "), b(fmt(vals.std()))], [n("1 de cada 4 áreas, por debajo de: "), b(fmt(vals.quantile(.25)))],
              [n("1 de cada 4 áreas, por encima de: "), b(fmt(vals.quantile(.75)))], [n("Mínimo: "), b(fmt(vals.min()))],
              [n("Máximo: "), b(fmt(vals.max()))]]
    info_box(ax, 0.988, 0.975, stats, "ur", size=8.8)
    if note_lines:
        info_box(ax, 0.988, 0.025, [b("Notas:")] + note_lines, "lr", size=7.8)
    header(fig, title, None, size=16.5, top=0.972)
    footer(fig, footer_parts, y=0.018)
    return save(fig, path)


# --------------------------------------------------------------------------- 5. exploratorias
def daily_bars(daily, path):
    """Registros PROFECO por fecha de levantamiento (notebook 00)."""
    d = daily.copy()
    d["fecha"] = pd.to_datetime(d.fecha)
    fig, ax = figure(2000, 1000, [0.075, 0.17, 0.9, 0.64])
    x = np.arange(len(d))
    ax.bar(x, d.registros, color=TEAL, width=0.75, edgecolor=FIG, lw=1, zorder=3)
    for xi, v in zip(x, d.registros):
        ax.text(xi, v + d.registros.max() * 0.015, f"{v / 1000:,.1f}k" if v >= 1000 else f"{v}", ha="center",
                va="bottom", fontsize=7.6, fontweight="bold")
    meses = {8: "ago"}
    ax.set_xticks(x, [f"{t.day}\n{meses.get(t.month, t.month)}" for t in d.fecha], fontsize=8)
    ax.set_ylim(0, d.registros.max() * 1.45)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}k")
    frame(ax, grid="y")
    ax.set_ylabel("Registros de precio", labelpad=7)
    ax.set_xlabel("Fecha de levantamiento (2026)", labelpad=7)
    obs = d[d.registros > 0]
    info_box(ax, 0.988, 0.975, [b("Datos clave"), [n("Total: "), b(f"{d.registros.sum():,}")],
                                [n("Días con datos: "), b(f"{len(obs)} de {len(d)}")],
                                [n("Día típico (mediana): "), b(f"{obs.registros.median():,.0f}")],
                                [n("Máximo: "), b(f"{d.registros.max():,}")]], "ur", size=8)
    header(fig, [n("Registros de precios "), b("PROFECO"), n(" por fecha de levantamiento")],
           f"(archivo completo, {d.fecha.min():%d} al {d.fecha.max():%d} de agosto de 2026)", top=0.965)
    footer(fig, [n("Fuente: PROFECO, Quién es Quién en los Precios (archivo 08-2026_Q2.csv). Registros: "),
                 b(f"{d.registros.sum():,}")])
    return save(fig, path)


def coverage_strip(cov, low, high, path=None):
    """Cobertura geográfica PROFECO de cada área ENSU con los umbrales (notebook 01)."""
    d = cov.sort_values("cobertura_profeco_area_pct").reset_index(drop=True)
    fig, ax = figure(2000, 1200, [0.072, 0.25, 0.908, 0.6])
    colors = np.where(d.cobertura_profeco_area_pct >= high, TEAL,
                      np.where(d.cobertura_profeco_area_pct >= low, NEUTRAL, CORAL))
    x = np.arange(len(d))
    ax.vlines(x, 0, d.cobertura_profeco_area_pct, color=colors, lw=1.4, zorder=2)
    ax.scatter(x, d.cobertura_profeco_area_pct, s=60, color=colors, edgecolor=FIG, lw=0.8, zorder=3)
    for v, lab in [(low, f"umbral aproximada {low:.0f}%"), (high, f"umbral directa {high:.0f}%")]:
        ax.axhline(v, color=GOLD, lw=0.8, ls=(0, (4, 3)))
        ax.text(len(d) - 0.5, v - 4.5, lab, ha="right", fontsize=7.6, color=GOLD, path_effects=HALO)
    ax.set_xticks(x, [short_name(a) for a in d.area_urbana_ensu], rotation=90, fontsize=6.4)
    ax.set(ylim=(0, 125), xlim=(-0.8, len(d) - 0.2), yticks=range(0, 101, 20))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    frame(ax, grid="y")
    ax.set_ylabel("% de la población 18+ del área", labelpad=7)
    legend(ax, [_dot(c, l, 7) for l, c in
                [("Directa", TEAL), ("Aproximada/documentada", NEUTRAL), ("No comparable", CORAL)]],
           "upper left", size=8, ncol=3)
    header(fig, [n("Cobertura "), b("geográfica"), n(" de PROFECO en cada área urbana ENSU")],
           "(parte de la población de 18+ del área que vive en municipios observados por PROFECO)", top=0.965)
    footer(fig, [n("Fuente: INEGI, microdatos ENSU (jun 2026); PROFECO. Áreas con correspondencia: "),
                 b(f"{(d.cobertura_profeco_area_pct >= low).sum()} de {len(d)}")])
    return save(fig, path) if path else fig


def price_boxplot(obs, names, path=None):
    """Distribución del precio por unidad base de cada candidato (notebook 02)."""
    order = obs.groupby("producto_normalizado").precio_unitario.median().sort_values().index
    fig, ax = figure(1800, 1350, [0.2, 0.125, 0.77, 0.72])
    data = [obs.loc[obs.producto_normalizado == k, "precio_unitario"] for k in order]
    bp = ax.boxplot(data, orientation="horizontal", tick_labels=[names[k] for k in order], patch_artist=True,
                    widths=0.6, flierprops=dict(marker="o", markersize=2, markerfacecolor=CORAL,
                                                markeredgecolor="none", alpha=0.5),
                    medianprops=dict(color=TEXT, lw=1.4), whiskerprops=dict(color=MUTED, lw=0.8),
                    capprops=dict(color=MUTED, lw=0.8), boxprops=dict(edgecolor=FIG, lw=0.6))
    for box in bp["boxes"]:
        box.set_facecolor(SLATE)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    frame(ax, grid="x")
    ax.tick_params(axis="y", labelsize=8.2, length=0)
    ax.set_xlabel("Precio por unidad base (kg, litro o pieza; escala logarítmica)", labelpad=7)
    legend(ax, [Patch(facecolor=SLATE, label="Caja: la mitad de los precios (los de en medio)"),
                Line2D([], [], color=TEXT, lw=1.4, label="Línea en la caja: mediana (precio de en medio)"),
                Line2D([], [], marker="o", ls="", ms=4, mfc=CORAL, mec="none", label="Precio atípico (IQR 1.5×)")],
           "lower right", size=8)
    header(fig, [n("Distribución de "), b("precios"), n(" por producto candidato")],
           "(todas las observaciones de supermercados en áreas comparables; agosto de 2026)", top=0.97)
    footer(fig, [n("Fuente: PROFECO (2026). Observaciones: "), b(f"{len(obs):,}"), n("; atípicos marcados (no eliminados): "),
                 b(f"{int(obs.extremo_iqr.sum()):,}")])
    return save(fig, path) if path else fig


def methods_scatter(metodos, path=None):
    """Costo de canasta: opción A (cualquier marca) vs. opción B (misma marca) (notebook 02)."""
    d = metodos.dropna(subset=["A_mediana", "B_misma_marca"])
    fig, ax = figure(1800, 1600, [0.12, 0.1, 0.84, 0.77])
    lo, hi = min(d.A_mediana.min(), d.B_misma_marca.min()) * 0.99, max(d.A_mediana.max(), d.B_misma_marca.max()) * 1.01
    ax.plot([lo, hi], [lo, hi], color=TEXT2, lw=0.8, ls=(0, (4, 3)), zorder=1)
    above = d.B_misma_marca > d.A_mediana
    for mask, color in [(above, CORAL), (~above, TEAL)]:
        ax.scatter(d.A_mediana[mask], d.B_misma_marca[mask], s=130, color=color, edgecolor=FIG, lw=1, zorder=3)
    ax.set(xlim=(lo, hi), ylim=(lo, hi))
    ax.xaxis.set_major_formatter(money)
    ax.yaxis.set_major_formatter(money)
    frame(ax)
    ax.set_xlabel("Opción A: cualquier marca (mediana)", labelpad=7)
    ax.set_ylabel("Opción B: misma marca", labelpad=7)
    groups = [(CORAL, "Misma marca sale más cara", above.sum()),
              (TEAL, "Misma marca sale igual o más barata", (~above).sum())]
    legend(ax, [_dot(c, f"{l} ({k} áreas)") for c, l, k in groups if k] +
               [Line2D([], [], color=TEXT2, lw=0.8, ls=(0, (4, 3)), label="Diagonal: mismo costo con ambas")],
           "lower right", size=8)
    rho = d[["A_mediana", "B_misma_marca"]].corr(method="spearman").iloc[0, 1]
    info_box(ax, 0.02, 0.98, [b("Comparación"), [n("Áreas con ambas: "), b(f"{len(d)}")],
                              [n("Coincidencia del orden (Spearman): "), b(f"{rho:.2f}")],
                              n("   1 = ambas opciones ordenan igual las áreas"),
                              [n("Diferencia típica B−A: "), b(money((d.B_misma_marca - d.A_mediana).median()))]],
             "ul", size=8)
    header(fig, [n("Costo de la canasta según el "), b("tratamiento de marcas")],
           "(cada punto es un área urbana elegible)", size=15, top=0.97)
    footer(fig, [n("Fuente: PROFECO (2026). Áreas solo con opción A: "), b(f"{metodos.B_misma_marca.isna().sum()}")])
    return save(fig, path) if path else fig
