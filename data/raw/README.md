# Datos originales

## PROFECO

Colocar aquí `08-2026_Q2.csv`. En este equipo también se busca en la carpeta
inmediatamente superior al proyecto. El original no se modifica; su SHA-256 se registra
en `data/metadata/profeco_manifest.json`. Fuente declarada: PROFECO, archivo aportado
por el usuario (URL de descarga pendiente de documentar).

## INEGI ENSU (`ensu/`)

Descargados del sitio oficial de INEGI el 19 de octubre de 2026. El notebook 01 los
vuelve a descargar si faltan (`src/ensu.py`, función `download`).

- Tabulados básicos, junio 2026 (estimaciones, coeficientes de variación, intervalos):
  `https://www.inegi.org.mx/contenidos/programas/ensu/tabulados/2026/ensu_tabulados_basicos_junio_2026_{estimacion|coeficiente|intervalos}_xlsx.zip`
- Microdatos 2026 (marzo y junio):
  `https://www.inegi.org.mx/contenidos/programas/ensu/microdatos/ensu_bd_2026_csv.zip`
- Catálogo de ciudades de interés 2025:
  `https://www.inegi.org.mx/contenidos/programas/ensu/doc/ensu2025_catalogo_ciudades_interes.pdf`

Los SHA-256 de los paquetes de tabulados están en `data/metadata/ensu_manifest.json`.

## INEGI Marco Geoestadístico 2024 (`inegi_mg/`)

`mg_2024_integrado.zip` (284 MB), descargado el 19 de octubre de 2026 de
`https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/mg_2024_integrado.zip`.
Se extraen solo las capas nacionales `00mun` (municipios) y `00ent` (entidades).
`src/geo.py` las simplifica en `data/processed/geo/` para los mapas.

## Natural Earth (`naturalearth/`)

`ne_50m_admin_0_countries.geojson` (3 MB, dominio público), descargado el 19 de octubre
de 2026 de `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson`.
Solo se usa para dibujar los países vecinos en los mapas.
