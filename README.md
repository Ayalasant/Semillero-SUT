# Encuestas de percepción peatonal — La Aurora

Esta carpeta reúne todo lo relacionado con el **análisis en Python de las encuestas** aplicadas a peatones en La Aurora: los datos, el notebook de análisis y sus resultados.

> 🚧 **En construcción.** El notebook de análisis todavía no existe. Esta carpeta y su estructura quedan reservadas para él.

## 🎯 Propósito

Las encuestas aportan la dimensión **perceptual** de la caminabilidad. Con las calificaciones Likert (1 a 5) que cada peatón da a las variables físicas del entorno se estiman los coeficientes de percepción β<sub>k</sub> del índice de caminabilidad híbrido (WI, ec. 17–18 del compendio de índices):

$$\beta_k = \frac{1}{n}\sum_{j=1}^{n} R_{jk}, \qquad WI = \sum_{i} \beta_i \, X_i$$

Los β<sub>k</sub> se combinan después con las variables físicas X<sub>i</sub> calculadas por segmento sobre la red peatonal (`GPKG/Aurora/Resultados/Red_Aurora.gpkg`).

## 📂 Estructura

```
Encuestas/
├── README.md                          # Este archivo
├── Analisis_de_encuestas.ipynb        # (futuro) notebook de análisis
├── Datos/
│   ├── Crudos/                        # Respuestas originales: NO se suben a GitHub (.gitignore)
│   └── Anonimizados/                  # Respuestas sin datos personales: sí se suben
└── Resultados/                        # Tablas, β_k, figuras y capas de salida del análisis
```

## 🔒 Privacidad de los datos

El repositorio es **público**. Las respuestas originales pueden contener nombres, teléfonos, direcciones, coordenadas exactas o combinaciones de edad, género y barrio que permiten identificar a una persona. Por eso:

1. Las respuestas originales van en `Datos/Crudos/`. Git ignora esa carpeta y no se sube.
2. Antes de pasar los datos a `Datos/Anonimizados/`, se eliminan los nombres, contactos y cualquier identificador directo, y se agrupan variables sensibles (por ejemplo, edad en rangos).
3. En `Resultados/` sólo van agregados (promedios, conteos, β<sub>k</sub>), nunca respuestas individuales.

## 📝 Pendiente

- [ ] Subir la base anonimizada a `Datos/Anonimizados/`.
- [ ] Crear `Analisis_de_encuestas.ipynb`: limpieza, descriptivos por género, edad y contexto, y estimación de β<sub>k</sub>.
- [ ] Unir los β<sub>k</sub> con las variables físicas por segmento para calcular el WI.
