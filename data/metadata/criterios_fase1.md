# Criterios de exploración

## Alcance

Archivo completo aportado por el usuario. Sin selección temporal, de categorías
o de municipios. La fecha se convierte con formato explícito `%Y/%m/%d`;
las conversiones fallidas se reportan. No se deduce trimestre del nombre del archivo.

## Columnas originales

| Campo | Uso en la exploración |
|---|---|
| producto | Conteo de nombres literales |
| presentacion | Identidad literal de presentación, sin homologar unidades |
| marca | Variante comercial literal; S/M se conserva |
| categoria | Composición del archivo |
| catalogo | Composición del archivo |
| precio | Conversión numérica auxiliar y validación de signo/finitud |
| fecha_registro | Fechas efectivas y cobertura temporal |
| cadena_comercial | Conteo de cadenas e identidad operativa de establecimiento |
| giro | Se conserva para análisis posteriores |
| nombre_comercial | Identidad operativa de establecimiento |
| direccion | Identidad operativa de establecimiento |
| estado | Identidad geográfica literal |
| municipio | Identidad geográfica literal junto con estado |
| latitud | Conversión numérica y validación de rango mundial |
| longitud | Conversión numérica y validación de rango mundial |

Las descripciones se basan en los nombres de las columnas, no sustituyen
un diccionario oficial. Unidad monetaria, protocolo de levantamiento y delimitación
geográfica deberán contrastarse con documentación PROFECO antes de publicar.

## Cobertura e identidad

Se consideran vacíos los campos que quedan sin caracteres al retirar espacios
en los extremos. No se interpretan automáticamente textos como `S/M` o `NA`.
Las agregaciones conservan la escritura literal. La normalización auxiliar de
geografía sirve únicamente para detectar colisiones textuales para revisión.
No valida municipios contra el catálogo INEGI ni detecta todos los errores ortográficos.

Los productos/presentaciones y las claves de establecimiento en el resumen incluyen
combinaciones incompletas si existen. Se informan sus registros en los controles.
La cobertura transversal de variantes requiere los tres campos de producto completos.
Las claves de establecimiento no usan coordenadas: pequeñas variaciones de
geolocalización no deberían crear establecimientos nuevos.

## Duplicados y extremos

Duplicado exacto significa igualdad en las 15 columnas leídas como texto.
Los conteos no eliminan duplicados. Debe investigarse su origen antes de
considerar el número de registros como observaciones independientes.

No se resume el precio medio de todos los productos por municipio.
Tampoco se aplica IQR mezclando categorías. La detección de extremos por
producto comparable, la comparación media/mediana y las reglas de exclusión
corresponden a las fases de canasta y transformación.

## Trazabilidad

El manifiesto conserva tamaño y SHA-256 del CSV, configuración de lectura y
resumen calculado. La ruta local se registra separadamente. La versión de
dependencias se conserva en `requirements-lock.txt`.
