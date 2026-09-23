# Semillero SUT

## Modelación Computacional para SUT: Herramientas y Procesos

**Autor:** Santiago Ayala

---

## 📖 Descripción

Este repositorio documenta el flujo de trabajo utilizado en la **modelación computacional** del proyecto SUT 2026, desde la descarga de datos geoespaciales hasta la exportación de capas para su análisis en Sistemas de Información Geográfica (SIG) como QGIS.

El notebook principal (`Proceso_y_uso_de_OSMNX.ipynb`) muestra paso a paso cómo:

- Descargar redes viales y peatonales reales desde OpenStreetMap usando [OSMnx](https://osmnx.readthedocs.io/)
- Convertir esa infraestructura en grafos (nodos y aristas) para análisis de conectividad
- Visualizar las redes descargadas
- Exportar los datos a formatos compatibles con software SIG (GeoPackage / Shapefile)

## 📂 Estructura del repositorio

```
Semillero-SUT/
├── Notebooks/
│   └── Proceso_y_uso_de_OSMNX.ipynb   # Notebook principal
├── Images/
│   └── Red_Peatonal_Aurora.png               # Imágenes usadas en el notebook
├── Geopackage/
│   └── *.gpkg                         # Capas exportadas (nodos y aristas)
├── .gitattributes
├── .gitignore
└── README.md
```

## ⚙️ Requisitos

Este proyecto usa Python a través de un entorno de **conda**. Las librerías principales son:

- [`osmnx`](https://osmnx.readthedocs.io/) — descarga y modela infraestructura urbana desde OpenStreetMap
- [`networkx`](https://networkx.org/) — manejo de grafos
- [`geopandas`](https://geopandas.org/) — manejo de datos espaciales vectoriales
- `jupyterlab` — para ejecutar el notebook

### Instalación del entorno

```bash
conda create --strict-channel-priority -c conda-forge -n ox osmnx jupyterlab
conda activate ox
```

## 🚀 Uso

1. Clona este repositorio:
   ```bash
   git clone https://github.com/TU-USUARIO/Semillero-SUT.git
   ```
2. Activa el entorno:
   ```bash
   conda activate ox
   ```
3. Abre JupyterLab:
   ```bash
   jupyter lab
   ```
4. Navega hasta `Notebooks/` y abre `Proceso_y_uso_de_OSMNX.ipynb`.

## 📊 Salidas

El notebook genera capas geoespaciales de nodos (intersecciones) y aristas (calles) de la red analizada, guardadas en la carpeta `GPKG/`, listas para abrir en QGIS o ArcGIS.

## 🗺️ Zona de estudio

El análisis se centra en la red peatonal y vial de **Medellín, Antioquia, Colombia**, con foco particular en el sector de **La Aurora** y **San Juan**.

---

*Proyecto desarrollado en el marco del Semillero SUT 2026.*
