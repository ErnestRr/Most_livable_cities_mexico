# PROYECTO: ¿Dónde cuesta menos vivir y existen mejores condiciones urbanas en México?

Quiero desarrollar desde cero un proyecto completo de análisis de datos en Python utilizando VS Code.

El proyecto debe replicar conceptualmente una visualización de dispersión por cuadrantes donde cada punto representa una ciudad/municipio mexicano.

IMPORTANTE:

No quiero simplemente copiar visualmente una gráfica existente. Quiero construir un análisis mexicano reproducible utilizando datos públicos oficiales.

El proyecto debe parecer y funcionar como un proyecto real desarrollado por mí: debe conservar notebooks, código, transformaciones, validaciones, datos procesados, documentación y visualizaciones.

Debe poder publicarse posteriormente en GitHub y utilizar las gráficas en LinkedIn/X.

También quiero generar una versión interactiva en HTML que pueda publicarse mediante GitHub Pages y posteriormente utilizar mi propio dominio.

---

# 1. PREGUNTA PRINCIPAL

Responder:

**¿En qué ciudades de México una canasta comparable cuesta menos y existen mejores condiciones urbanas?**

La visualización principal será un scatter plot de cuadrantes.

Cada punto = ciudad/municipio comparable.

Eje X:

**Costo de una canasta homogénea de productos**

Eje Y:

**Percepción de seguridad**

Preferentemente:

% de población adulta que considera segura su ciudad.

Si ENSU publica originalmente percepción de inseguridad, transformar:

seguridad = 100 - inseguridad

Documentar explícitamente la transformación.

La interpretación será:

- superior izquierda = menor costo + mayor seguridad
- superior derecha = mayor costo + mayor seguridad
- inferior izquierda = menor costo + menor seguridad
- inferior derecha = mayor costo + menor seguridad

No llamar al eje Y "calidad de vida".

La seguridad es solamente una dimensión de las condiciones urbanas.

---

# 2. FUENTES PRINCIPALES

## PROFECO

Utilizar datos abiertos oficiales de precios.

El dataset contiene aproximadamente estas variables:

- producto
- presentacion
- marca
- categoria
- catalogo
- precio
- fecha_registro
- cadena_comercial
- giro
- nombre_comercial
- direccion
- estado
- municipio
- latitud
- longitud

No asumir previamente cuántos municipios existen.

Leer el dataset real y calcular:

- número de estados
- número de municipios únicos
- número de establecimientos
- número de cadenas
- número de productos
- rango de fechas
- registros por municipio
- productos por municipio
- establecimientos por municipio

En una revisión preliminar del dataset se encontraron aproximadamente 70 municipios únicos, pero esto DEBE verificarse programáticamente.

## INEGI — ENSU

Utilizar la Encuesta Nacional de Seguridad Pública Urbana.

Obtener el último periodo disponible compatible con el periodo de precios seleccionado.

Extraer el indicador de percepción de inseguridad/seguridad por área urbana.

No asumir que municipio PROFECO y área urbana ENSU significan exactamente lo mismo.

---

# 3. FASE OBLIGATORIA: AUDITORÍA DE COBERTURA

ESTA FASE DEBE REALIZARSE ANTES DE CONSTRUIR LA GRÁFICA.

El objetivo es determinar qué municipios PROFECO pueden compararse correctamente con áreas urbanas ENSU.

Crear un notebook:

`notebooks/01_auditoria_cobertura.ipynb`

Analizar independientemente ambas fuentes.

### PROFECO

Mostrar:

- municipios disponibles
- estados
- registros
- establecimientos
- productos
- fechas disponibles
- cobertura temporal
- cobertura de productos

### ENSU

Mostrar:

- áreas urbanas disponibles
- entidades
- periodo
- indicador seleccionado

Después construir una tabla de homologación:

`data/processed/homologacion_geografica.csv`

Columnas mínimas:

- estado
- municipio_profeco
- area_urbana_ensu
- correspondencia
- tipo_correspondencia
- incluir
- observaciones

Tipos posibles:

- directa
- aproximada/documentada
- no comparable

NO hacer joins simplemente porque los nombres se parecen.

Ejemplo:

una zona urbana/metropolitana ENSU puede comprender más de un municipio mientras PROFECO identifica establecimientos mediante municipio.

Las equivalencias dudosas deben excluirse o documentarse explícitamente.

---

# 4. CONSTRUCCIÓN DE UNA CANASTA COMPARABLE

Este es uno de los componentes metodológicos más importantes.

NO comparar simplemente el promedio de todos los precios existentes en cada municipio.

Eso produciría sesgos porque diferentes municipios pueden tener diferentes:

- productos
- marcas
- presentaciones
- cadenas
- establecimientos.

Primero determinar qué productos tienen suficiente cobertura transversal.

Crear:

`notebooks/02_canasta_comparable.ipynb`

Analizar:

- producto
- presentación
- marca
- municipio
- fecha
- establecimiento

Crear una matriz:

producto/presentación × municipio

Calcular porcentaje de cobertura.

Seleccionar automáticamente candidatos con alta cobertura.

Intentar construir una canasta de aproximadamente 10–20 productos.

NO forzar este número.

Si solamente 8 productos cumplen criterios estrictos, utilizar 8.

Si 25 cumplen, evaluar utilizar más.

Priorizar productos de consumo común.

---

# 5. HOMOLOGACIÓN DE PRODUCTOS

Evitar comparar:

"Cebolla 1 kg"

contra

"Cebolla bolsa 500 g"

sin transformación.

Crear una clave comparable:

`producto_normalizado`

y cuando corresponda:

`presentacion_normalizada`

Conservar siempre las variables originales.

No modificar silenciosamente los datos.

Si las unidades pueden normalizarse correctamente, calcular precio por:

- kilogramo
- litro
- pieza
- unidad comparable

Cuando no sea posible establecer equivalencia fiable, excluir ese producto.

---

# 6. MARCAS

Analizar primero la cobertura.

Preferencia metodológica:

### Opción A

Producto + presentación equivalente independientemente de marca, utilizando una medida robusta de precio.

### Opción B

Producto + presentación + misma marca cuando exista cobertura suficiente.

Comparar ambas metodologías antes de decidir.

Documentar cuál se seleccionó y por qué.

No permitir que una ciudad parezca más cara simplemente porque PROFECO observó marcas premium allí.

---

# 7. VENTANA TEMPORAL

No utilizar indiscriminadamente todos los precios de 2026.

Determinar las fechas disponibles.

Seleccionar una ventana temporal suficientemente cercana al periodo ENSU.

Preferentemente utilizar un periodo acotado, por ejemplo:

- último mes completo disponible;
- o ventana de 30 días;
- o periodo alrededor del trimestre ENSU.

La elección debe depender de la cobertura observada.

Documentar:

`fecha_inicio`

`fecha_fin`

`periodo_ensu`

---

# 8. PRECIO REPRESENTATIVO

No utilizar automáticamente el promedio simple.

Analizar distribución de precios y outliers.

Utilizar preferentemente:

**mediana**

por:

municipio + producto normalizado

cuando resulte metodológicamente adecuado.

Comparar media vs mediana y explicar la decisión.

Implementar detección sencilla de valores extremos mediante IQR.

No eliminar outliers automáticamente sin documentarlos.

---

# 9. COSTO DE LA CANASTA

Una vez seleccionados productos comparables:

Para cada municipio:

1. obtener precio representativo de cada producto;
2. verificar que tenga todos o un porcentaje mínimo de productos;
3. sumar precios normalizados;
4. calcular costo total de la canasta.

Crear:

`data/processed/canasta_municipio.csv`

Columnas:

- estado
- municipio
- productos_disponibles
- productos_canasta
- cobertura_pct
- establecimientos
- costo_canasta
- fecha_inicio
- fecha_fin

No imputar precios faltantes para fabricar cobertura.

---

# 10. CRITERIOS DE INCLUSIÓN

Definir criterios explícitos.

Ejemplo inicial:

- correspondencia geográfica válida PROFECO–ENSU;
- >= 80% de productos de la canasta;
- número mínimo razonable de establecimientos;
- número mínimo razonable de observaciones;
- ventana temporal compatible.

Estos thresholds NO deben aceptarse ciegamente.

Analizar primero la distribución y justificar los valores finalmente utilizados.

Generar:

`data/processed/auditoria_cobertura.csv`

con:

- municipio
- estado
- registros_profeco
- establecimientos
- productos
- cobertura_canasta_pct
- area_ensu
- dato_ensu
- pasa_validacion
- motivo_exclusion

Quiero poder demostrar exactamente por qué una ciudad aparece o no aparece.

---

# 11. DATASET ANALÍTICO FINAL

Crear:

`data/processed/dataset_final.csv`

Una fila por localidad comparable.

Columnas mínimas:

- estado
- municipio
- area_urbana_ensu
- costo_canasta
- seguridad_pct
- inseguridad_pct
- productos_canasta
- cobertura_pct
- establecimientos
- observaciones_precio
- fecha_inicio_precios
- fecha_fin_precios
- periodo_ensu
- latitud
- longitud

---

# 12. GRÁFICA PRINCIPAL

Crear una visualización inspirada en la referencia proporcionada.

Scatter plot profesional.

X:

`costo_canasta`

Y:

`seguridad_pct`

Cada punto:

una localidad.

Agregar líneas de referencia para crear cuatro cuadrantes.

Preferentemente utilizar:

- mediana de X
- mediana de Y

No utilizar valores arbitrarios.

Etiquetar ciudades relevantes sin saturar la gráfica.

Etiquetar, por ejemplo:

- extremos
- mejores combinaciones
- peores combinaciones
- outliers

Implementar ajuste de etiquetas para minimizar solapamientos.

---

# 13. CUADRANTES

Asignar automáticamente:

### Cuadrante 1
**Menor costo + mayor seguridad**

### Cuadrante 2
**Mayor costo + mayor seguridad**

### Cuadrante 3
**Menor costo + menor seguridad**

### Cuadrante 4
**Mayor costo + menor seguridad**

Crear variable:

`cuadrante`

No afirmar que el cuadrante 1 representa automáticamente "las mejores ciudades para vivir".

La gráfica solamente compara las dimensiones analizadas.

---

# 14. DISEÑO PARA REDES SOCIALES

Generar una versión estática editorial de alta calidad.

Utilizar:

- matplotlib
- pandas
- numpy
- adjustText si resulta útil

Estilo:

- limpio
- fondo claro
- minimalista
- profesional
- similar a visualización de periodismo de datos
- sin exceso de elementos
- sin apariencia de dashboard corporativo genérico

Título sugerido:

**¿Dónde cuesta menos la canasta y se percibe mayor seguridad en México?**

Subtítulo:

Costo de una canasta comparable vs. percepción de seguridad urbana.

Agregar discretamente:

Fuente: PROFECO + INEGI ENSU  
Periodo: [periodos reales]

Exportar:

`outputs/social/grafica_principal_1080x1350.png`

para LinkedIn.

También:

`outputs/social/grafica_principal_1600x900.png`

para X/web.

Exportar adicionalmente SVG.

Usar mínimo 200–300 DPI para PNG.

---

# 15. VISUALIZACIONES COMPLEMENTARIAS

Además del scatter principal generar:

### Ranking
Municipios ordenados por costo de canasta.

### Heatmap
Productos × municipios mostrando precio relativo.

### Producto con mayor dispersión geográfica
Identificar productos cuyo precio cambia más entre municipios.

### Comparación de cadenas
Cuando la cobertura permita comparar las mismas cadenas y productos.

No crear conclusiones cuando la muestra no permita una comparación justa.

---

# 16. DASHBOARD INTERACTIVO

Crear una versión interactiva utilizando Plotly.

Debe incluir:

### Scatter principal

Hover:

- ciudad
- estado
- costo canasta
- seguridad
- cobertura
- establecimientos
- número de observaciones

### Ranking

Costo de canasta por municipio.

### Explorador de productos

Permitir seleccionar un producto y visualizar precios por municipio.

### Mapa

Utilizar latitud/longitud de establecimientos o centroides apropiados.

No saturar la interfaz.

---

# 17. HTML PARA GITHUB PAGES

Como GitHub Pages es estático, NO depender de un servidor Python/Dash para la versión pública principal.

Generar:

`docs/index.html`

con visualizaciones Plotly autocontenidas o recursos compatibles con GitHub Pages.

El sitio debe poder funcionar directamente desde GitHub Pages.

Prepararlo para posteriormente conectar un dominio personalizado.

No introducir React, Node u otros frameworks innecesarios.

---

# 18. DASH OPCIONAL

Crear adicionalmente:

`app.py`

con una aplicación Dash sencilla que reutilice el dataset procesado.

Debe servir como versión avanzada/local.

Pero el proyecto NO debe depender de Dash para funcionar públicamente en GitHub Pages.

---

# 19. NOTEBOOK PRINCIPAL

Quiero que el análisis pueda seguirse como si yo hubiera realizado el proyecto paso a paso.

Crear:

`notebooks/00_exploracion_profeco.ipynb`

`notebooks/01_auditoria_cobertura.ipynb`

`notebooks/02_canasta_comparable.ipynb`

`notebooks/03_limpieza_transformacion.ipynb`

`notebooks/04_analisis.ipynb`

`notebooks/05_visualizaciones.ipynb`

Cada notebook debe contener:

- Markdown breve explicando qué hacemos;
- código visible;
- resultados;
- tablas;
- controles de calidad;
- conclusiones breves.

NO crear notebooks artificialmente enormes.

El código debe parecer código razonable de un analista BI/Data Analyst, no una arquitectura innecesariamente sofisticada.

---

# 20. ESTRUCTURA

Crear:

mexico-costo-canasta/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── metadata/
│
├── notebooks/
│   ├── 00_exploracion_profeco.ipynb
│   ├── 01_auditoria_cobertura.ipynb
│   ├── 02_canasta_comparable.ipynb
│   ├── 03_limpieza_transformacion.ipynb
│   ├── 04_analisis.ipynb
│   └── 05_visualizaciones.ipynb
│
├── src/
│   ├── __init__.py
│   ├── cleaning.py
│   ├── geographic_matching.py
│   ├── basket.py
│   └── visualization.py
│
├── outputs/
│   ├── social/
│   └── charts/
│
├── docs/
│   └── index.html
│
└── app.py

---

# 21. LIBRERÍAS

Utilizar principalmente:

pandas  
numpy  
matplotlib  
plotly  
jupyter  
requests  
openpyxl  
adjustText  
dash

Agregar solamente otras dependencias cuando realmente sean necesarias.

Crear `requirements.txt`.

---

# 22. CALIDAD Y REPRODUCIBILIDAD

Agregar controles como:

- duplicados
- nulos
- precios <= 0
- fechas inválidas
- municipios inconsistentes
- productos sin equivalencia
- observaciones extremas
- cobertura insuficiente

Utilizar funciones reutilizables cuando tenga sentido.

No sobreingenierizar.

---

# 23. README

Crear un README profesional pero natural.

Debe explicar:

## Objetivo

Qué pregunta intenta responder.

## Fuentes

PROFECO e INEGI ENSU.

## Metodología

Cómo se construyó la canasta.

## Cobertura

Qué localidades pudieron compararse.

## Limitaciones

Especialmente:

PROFECO no necesariamente constituye una muestra estadísticamente representativa de todos los establecimientos de cada ciudad.

ENSU utiliza áreas urbanas y PROFECO municipios.

El precio de una canasta NO equivale al costo total de vida.

La percepción de seguridad NO equivale a calidad de vida.

## Resultados

Principales hallazgos una vez ejecutado el análisis.

---

# 24. REGLA CRÍTICA

NO inventar datos.

NO crear datos simulados para completar ciudades.

NO rellenar municipios faltantes.

NO asumir equivalencias geográficas.

NO afirmar causalidad.

Si una fuente oficial no puede descargarse automáticamente:

1. explicar exactamente qué archivo necesito descargar;
2. proporcionar su fuente oficial;
3. preparar el código para leerlo desde `data/raw/`;
4. continuar con todo lo que sí pueda desarrollarse.

---

# 25. FORMA DE TRABAJO

No construyas todo de golpe sin verificar los datos.

Trabaja por fases.

FASE 1:
crear estructura, entorno, requirements y explorar PROFECO.

FASE 2:
obtener/procesar ENSU y realizar auditoría geográfica.

FASE 3:
determinar canasta comparable.

FASE 4:
construir dataset analítico.

FASE 5:
realizar análisis.

FASE 6:
crear visualización estática.

FASE 7:
crear HTML interactivo.

FASE 8:
documentar y preparar GitHub Pages.

Después de cada fase:

- ejecuta el código;
- corrige errores;
- verifica outputs;
- explica brevemente qué se obtuvo;
- continúa únicamente cuando el resultado sea válido.

Empieza ahora por la FASE 1.