# Diagnóstico de triangulación

Abrir `diagnostics.html` directamente en un navegador. Incluye Plotly y los datos;
funciona sin conexión, servidor ni kernel. También está integrado mediante IFrame
en la nueva sección 12 de `notebooks/13_multiview_3d_reconstruction.ipynb`.
Si Jupyter no permite acceder al HTML por su raíz de archivos o confianza del notebook,
abrir el archivo HTML directamente.

Se conservan todas las celdas históricas y sus outputs. El backup completo está en
`original_13_multiview_3d_reconstruction.ipynb`. `image_sha256.json` registra las 12
imágenes originales, sin modificarlas. No se instalaron dependencias.

## Resultado de referencia

Umbrales exploratorios: ángulo efectivo mínimo 2°, error máximo en cada cámara
3 px y profundidad máxima de 10 baselines; asociaciones propagadas desactivadas.
Siempre se exige geometría finita y profundidad positiva en ambas cámaras de origen.

| Métrica | Antes | Después |
|---|---:|---:|
| Puntos | 386 | 376 |
| Semilla 03/04 | 188 | 188 |
| Añadidos View 05 | 113 | 103 |
| Añadidos View 06 | 85 | 85 |
| Profundidad máxima en las cámaras de origen | 31,633 | 9,270 |
| Profundidad máxima / baseline | 31,974 | 9,370 |
| Ángulo efectivo mínimo | 1,708° | 5,237° |
| Error máximo de reproyección | 2,916 px | 2,916 px |
| Mediana del error máximo de reproyección | 0,257 px | 0,252 px |

10 puntos fallan el filtro de profundidad, de los cuales 2 también fallan el filtro
angular. Ninguno falla el umbral de error. Los IDs rechazados son 191, 193, 194,
195, 196, 202, 297, 298, 299 y 300. Sus errores máximos de reproyección abarcan
0,075–1,174 px. Los IDs 195 y 196 coinciden geométricamente y tienen ángulo 1,708°;
los conteos corresponden a IDs del mapa, no necesariamente a posiciones distintas.

La auditoría de los diccionarios finales encuentra 7 puntos con alguna asociación
por encima de 3 px. La opción de validación de asociaciones permite investigarlos;
no mezcla esos errores con los de la pareja original de triangulación.

## Decisiones matemáticas

- Convención: `X_cam = R @ X_world + t`, centro `C = -R.T @ t`.
  La Z del mundo coincide con profundidad solo para la cámara semilla View 03.
- El ángulo se calcula entre `X-C_a` y `X-C_b` mediante atan2 del producto
  vectorial y escalar normalizados. Se usa `min(theta, 180-theta)` para detectar
  también rayos casi antiparalelos.
- La reproyección se compara con keypoints observados, no con los propios rayos
  reconstruidos. Se limita el máximo error euclídeo de ambas vistas, en imágenes
  de anchura 900 px. La semilla también recibe esta comprobación.
- La profundidad máxima se divide por la baseline de la pareja de nacimiento.
  Es invariante ante cambio de escala monocular, pero el umbral de 10 sigue siendo
  una hipótesis exploratoria sobre la escena. Un punto lejano puede ser real.
- Error pequeño y profundidad muy incierta pueden coexistir con poco paralaje.
  Los filtros de profundidad y ángulo están correlacionados; los motivos de rechazo
  pueden solaparse. Un subconjunto filtrado no es ground truth ni una estimación
  calibrada de incertidumbre.
- K es aproximada, no se modela distorsión y no hay bundle adjustment. Filtrar al
  final no elimina la influencia previa de puntos débiles en PnP.

El diagnóstico reconstruye las asociaciones de nacimiento ejecutando `expand_map`
sin cambios sobre copias, comprobando IDs y coordenadas contra el mapa existente.
Las observaciones de cada candidato se capturan antes de las inserciones para
evitar perder asociaciones por sobrescrituras muchos-a-uno. No se sustituyen
poses, puntos ni diccionarios del experimento.

Modelo de cámara: [OpenCV calib3d](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).
Referencia para ángulos de triangulación:
[COLMAP triangulation.cc](https://github.com/colmap/colmap/blob/main/src/colmap/geometry/triangulation.cc).

## Archivos y reproducción

- `points.csv`: una fila por ID original, origen, keypoints, métricas, aceptación
  y motivos bajo los umbrales iniciales. Cambiar controles del HTML no reescribe el CSV.
- `summary.json`: estadísticas globales y por origen con la configuración exportada.
- `control_cases.json`: resultados Python de seis configuraciones para validar JavaScript.
- `src/triangulation_diagnostics.py` y `src/triangulation_dashboard.js`: implementación.

Desde la raíz del proyecto, usando el entorno existente:

```bash
.venv/bin/python scripts/run_triangulation_diagnostics.py
.venv/bin/python -m unittest discover -s tests -v
```

El runner reproduce el notebook histórico, omite su celda `%pip install plotly`,
no abre las figuras antiguas, valida las imágenes y conserva los outputs históricos.
Actualiza únicamente los outputs de la sección nueva y sus exportaciones de diagnóstico.
La referencia de 386 puntos se reprodujo con el entorno actual; otras versiones
de OpenCV pueden variar los resultados RANSAC. El diagnóstico usa los IDs reales,
sin imponer 386 como tamaño del mapa.

La lógica de los controles se verificó también con Node mediante
`tests/test_triangulation_dashboard.mjs`, contrastando las seis configuraciones con
Python, el selector de origen, restablecimiento, encuadre y subconjuntos vacíos.
Estas pruebas usan dobles de DOM/Plotly: no verifican renderizado ni WebGL.
El navegador de la sesión no estaba disponible para una inspección visual.
