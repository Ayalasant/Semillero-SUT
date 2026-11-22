"""
red_peatonal.py
===============

Funciones del flujo de preparación de la red peatonal del Semillero SUT:

    1. cargar_red_desde_gpkg / descargar_red  -> grafo crudo de OSMnx
    2. recortar_red                            -> grafo dentro del territorio de análisis
    3. aplicar_exclusiones                     -> quita ejes definidos a mano (QGIS)
    4. conservar_componente_principal          -> elimina nodos/ejes desconectados
    5. integrar_pois                           -> inserta los puntos de interés como nodos de la red
    6. exportar_red                            -> GeoPackage (QGIS) + GraphML (Python)

Convenciones:
    * El grafo es el MultiDiGraph de OSMnx (cada calle peatonal aparece en los dos
      sentidos u->v y v->u).
    * Todo el trabajo métrico se hace en EPSG:9377 (MAGNA-SIRGAS Origen Nacional).
    * Los nodos creados para los POIs tienen id negativo (-1, -2, ...) para no
      chocar con los osmid de OpenStreetMap.

Autor: Santiago Ayala Martínez — Semillero SUT 2026
"""

from __future__ import annotations

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import LineString, Point
from shapely.ops import substring

CRS_METRICO = "EPSG:9377"


# ---------------------------------------------------------------------------
# 1. Obtención de la red
# ---------------------------------------------------------------------------
def poligono_de_descarga(territorio: gpd.GeoDataFrame, buffer_m: float = 300):
    """Polígono (EPSG:4326) un poco más grande que el territorio.

    Se descarga con margen para que el recorte posterior sea limpio y no se
    pierdan ejes que cruzan el borde.
    """
    return territorio.to_crs(CRS_METRICO).buffer(buffer_m).to_crs(4326).union_all()


def descargar_red(poligono, network_type: str = "walk") -> nx.MultiDiGraph:
    """Descarga la red desde OpenStreetMap (requiere internet)."""
    return ox.graph.graph_from_polygon(poligono, network_type=network_type)


def cargar_red_desde_gpkg(ruta_nodos, ruta_ejes, poligono=None) -> nx.MultiDiGraph:
    """Reconstruye un grafo OSMnx a partir de capas exportadas con ox.graph_to_gdfs.

    Si se da `poligono`, sólo se leen las entidades dentro de su bounding box
    (mucho más rápido con la red de todo el AMVA).
    """
    bbox = tuple(gpd.GeoSeries([poligono], crs=4326).total_bounds) if poligono is not None else None
    nodos = gpd.read_file(ruta_nodos, bbox=bbox).set_index("osmid")
    ejes = gpd.read_file(ruta_ejes, bbox=bbox)
    ejes = ejes[ejes["u"].isin(nodos.index) & ejes["v"].isin(nodos.index)]
    ejes = ejes.set_index(["u", "v", "key"])
    return ox.convert.graph_from_gdfs(nodos, ejes, graph_attrs={"crs": nodos.crs.to_string()})


# ---------------------------------------------------------------------------
# 2-4. Recorte y limpieza
# ---------------------------------------------------------------------------
def recortar_red(G: nx.MultiDiGraph, territorio: gpd.GeoDataFrame,
                 truncate_by_edge: bool = False) -> nx.MultiDiGraph:
    """Conserva los nodos dentro del territorio y los ejes entre ellos."""
    poligono = territorio.to_crs(G.graph["crs"]).union_all()
    return ox.truncate.truncate_graph_polygon(G, poligono, truncate_by_edge=truncate_by_edge)


def aplicar_exclusiones(G: nx.MultiDiGraph, exclusiones: pd.DataFrame,
                        ambos_sentidos: bool = True) -> nx.MultiDiGraph:
    """Elimina los ejes (u, v, key) listados y los nodos que queden aislados.

    Con `ambos_sentidos=True` también se elimina la arista del sentido contrario
    (v -> u), porque en la red peatonal cada calle existe en las dos direcciones.
    Así basta con listar un sentido y nunca queda una calle "a medias".
    """
    H = G.copy()
    ejes = {(int(r.u), int(r.v), int(r.key)) for r in exclusiones.itertuples()}
    ejes = {e for e in ejes if H.has_edge(*e)}
    if ambos_sentidos:
        for u, v, k in list(ejes):
            k_inv = _arista_inversa(H, u, v, k)
            if k_inv is not None:
                ejes.add((v, u, k_inv))
    H.remove_edges_from(ejes)
    H.remove_nodes_from(list(nx.isolates(H)))
    return H


def resumen_componentes(G: nx.MultiDiGraph) -> pd.DataFrame:
    """Tabla con el tamaño de cada componente conexo (débil) de la red."""
    comps = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
    filas = []
    for i, c in enumerate(comps):
        sub = G.subgraph(c)
        filas.append({"componente": i, "nodos": len(c), "ejes": sub.number_of_edges(),
                      "longitud_m": sum(d.get("length", 0) for *_, d in sub.edges(data=True))})
    return pd.DataFrame(filas)


def conservar_componente_principal(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Elimina todo lo que no esté conectado con la red principal."""
    return ox.truncate.largest_component(G, strongly=False)


def recalcular_street_count(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Actualiza `street_count` con la red recortada.

    OSMnx lo calcula sobre la red descargada; tras recortar, los nodos del borde
    conservan el valor viejo. Para índices como R_dead hay que recalcularlo.
    """
    nx.set_node_attributes(G, ox.stats.count_streets_per_node(G), name="street_count")
    return G


# ---------------------------------------------------------------------------
# 5. Integración de puntos de interés
# ---------------------------------------------------------------------------
def _arista_inversa(G, u, v, k):
    """Busca la arista v->u que representa la misma calle que u->v (key k)."""
    if not G.has_edge(v, u):
        return None
    d = G.edges[u, v, k]
    for k2, d2 in G[v][u].items():
        if (str(d2.get("osmid")) == str(d.get("osmid")) or set(_lista(d2.get("osmid"))) == set(_lista(d.get("osmid")))) \
                and abs(d2.get("length", 0) - d.get("length", 0)) < 0.01:
            return k2
    return None


def _lista(x):
    return x if isinstance(x, list) else [x]


def _geometria(G, u, v, k) -> LineString:
    d = G.edges[u, v, k]
    if "geometry" in d:
        return d["geometry"]
    return LineString([(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])])


def integrar_pois(G: nx.MultiDiGraph, pois: gpd.GeoDataFrame, col_nombre: str,
                  tolerancia_nodo_m: float = 1.0, columnas_extra: list[str] | None = None):
    """Inserta cada punto de interés como un nodo de la red.

    Para cada POI:
      1. Se busca la arista más cercana (distancia euclidiana, grafo proyectado).
      2. Se proyecta el POI sobre esa arista (punto de acceso).
      3. Si el punto de acceso queda a menos de `tolerancia_nodo_m` de un extremo,
         el POI se asocia a ese nodo existente.
      4. Si no, la arista se divide en dos y se crea un nodo nuevo en el punto de
         acceso (también se divide la arista del sentido contrario).

    Parámetros
    ----------
    G : grafo PROYECTADO (metros).
    pois : GeoDataFrame de puntos.
    col_nombre : columna con el nombre del POI.
    columnas_extra : columnas de `pois` que se copian al nodo (p. ej. categoría).

    Retorna
    -------
    G_poi : copia del grafo con los POIs integrados.
    pois_out : los POIs con el nodo de la red asignado y la distancia de ajuste.
    """
    if not ox.projection.is_projected(G.graph["crs"]):
        raise ValueError("Proyecte el grafo antes (ox.project_graph).")
    columnas_extra = columnas_extra or []
    G = G.copy()
    pois = pois.to_crs(G.graph["crs"]).reset_index(drop=True)
    nx.set_node_attributes(G, "red", name="tipo_nodo")

    registros = []
    nuevo_id = -1
    for i, poi in pois.iterrows():
        pt: Point = poi.geometry
        u, v, k = ox.distance.nearest_edges(G, pt.x, pt.y)
        geom = _geometria(G, u, v, k)
        largo_geom = geom.length
        d = geom.project(pt)
        acceso = geom.interpolate(d)
        dist_ajuste = pt.distance(acceso)

        if d <= tolerancia_nodo_m or largo_geom - d <= tolerancia_nodo_m:
            nodo = u if d <= tolerancia_nodo_m else v
            metodo = "nodo existente"
        else:
            nodo = nuevo_id
            nuevo_id -= 1
            metodo = "arista dividida"
            datos = dict(G.edges[u, v, k])
            largo = datos.get("length", largo_geom)
            f = d / largo_geom
            g1, g2 = substring(geom, 0, d), substring(geom, d, largo_geom)

            k_inv = _arista_inversa(G, u, v, k)
            G.remove_edge(u, v, k)
            if k_inv is not None:
                datos_inv = dict(G.edges[v, u, k_inv])
                G.remove_edge(v, u, k_inv)

            G.add_node(nodo, x=acceso.x, y=acceso.y, street_count=2, tipo_nodo="poi")
            G.add_edge(u, nodo, **{**datos, "geometry": g1, "length": largo * f})
            G.add_edge(nodo, v, **{**datos, "geometry": g2, "length": largo * (1 - f)})
            if k_inv is not None:
                G.add_edge(v, nodo, **{**datos_inv, "geometry": g2.reverse(), "length": largo * (1 - f)})
                G.add_edge(nodo, u, **{**datos_inv, "geometry": g1.reverse(), "length": largo * f})

        # Un nodo puede recibir varios POIs: se acumulan los nombres
        nd = G.nodes[nodo]
        nd["poi_nombre"] = "; ".join(filter(None, [nd.get("poi_nombre"), str(poi[col_nombre]).strip()]))
        for c in columnas_extra:
            nd[f"poi_{c}"] = "; ".join(filter(None, [nd.get(f"poi_{c}"), str(poi[c])]))
        if nd.get("tipo_nodo") != "poi":
            nd["tipo_nodo"] = "red+poi"

        registros.append({"nodo_red": nodo, "metodo": metodo,
                          "dist_ajuste_m": round(dist_ajuste, 2),
                          "geometry_acceso": acceso})

    info = pd.DataFrame(registros)
    pois_out = pois.join(info.drop(columns="geometry_acceso"))
    pois_out["acceso_x"] = [p.x for p in info["geometry_acceso"]]
    pois_out["acceso_y"] = [p.y for p in info["geometry_acceso"]]
    return G, pois_out


def lineas_de_ajuste(pois_out: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Líneas POI -> punto de acceso en la red (útil para revisar en QGIS)."""
    geoms = [LineString([(p.x, p.y), (ax_, ay_)])
             for p, ax_, ay_ in zip(pois_out.geometry, pois_out.acceso_x, pois_out.acceso_y)]
    return gpd.GeoDataFrame(pois_out.drop(columns="geometry"), geometry=geoms, crs=pois_out.crs)


# ---------------------------------------------------------------------------
# Verificación
# ---------------------------------------------------------------------------
def verificar_red(G: nx.MultiDiGraph, tol: float = 0.01) -> dict:
    """Chequeos de consistencia básicos de la red final."""
    errores_geom = 0
    for u, v, k, d in G.edges(keys=True, data=True):
        if "geometry" in d:
            p0 = Point(d["geometry"].coords[0])
            if p0.distance(Point(G.nodes[u]["x"], G.nodes[u]["y"])) > tol:
                errores_geom += 1
    sin_inversa = sum(1 for u, v, k in G.edges(keys=True) if not G.has_edge(v, u))
    return {
        "nodos": G.number_of_nodes(),
        "ejes_dirigidos": G.number_of_edges(),
        "componentes": nx.number_weakly_connected_components(G),
        "nodos_aislados": nx.number_of_isolates(G),
        "ejes_sin_sentido_contrario": sin_inversa,
        "geometrias_mal_orientadas": errores_geom,
        "longitud_red_km (sin duplicar sentidos)": round(
            sum(d["length"] for *_, d in ox.convert.to_undirected(G).edges(data=True)) / 1000, 2),
    }


# ---------------------------------------------------------------------------
# 6. Exportación
# ---------------------------------------------------------------------------
def exportar_red(G: nx.MultiDiGraph, ruta_gpkg, ruta_graphml=None, capas_extra: dict | None = None):
    """Guarda nodos y ejes en un GeoPackage (y opcionalmente el grafo en GraphML).

    Las columnas con listas (p. ej. osmid de ejes simplificados) se convierten a
    texto porque GeoPackage no admite listas.
    """
    nodos, ejes = ox.convert.graph_to_gdfs(G)
    for gdf in (nodos, ejes):
        for c in gdf.columns:
            if c != "geometry" and gdf[c].map(lambda x: isinstance(x, list)).any():
                gdf[c] = gdf[c].astype(str)
    nodos.reset_index().to_file(ruta_gpkg, layer="nodos", driver="GPKG")
    ejes.reset_index().to_file(ruta_gpkg, layer="ejes", driver="GPKG")
    for nombre, gdf in (capas_extra or {}).items():
        gdf.to_file(ruta_gpkg, layer=nombre, driver="GPKG")
    if ruta_graphml:
        ox.io.save_graphml(G, ruta_graphml)
