#!/usr/bin/env python
# coding: utf-8


import geopandas as gpd
import folium
from shapely.geometry import Point, LineString, Polygon, MultiPolygon


def plot_togo_layers_geom(layers,
                          color_col_list,
                          palette_list,
                          legend_name_list=None,
                          zoom_start=7,
                          map_height="400px",
                          map_width="100%",
                          basemap="Esri.WorldImagery"):
    """
    Plot multiple GeoDataFrame layers (any geometry) over the Plateaux region of Togo, each with its own color column and palette.

    Parameters
    ----------
    layers : list of GeoDataFrame
        List of GeoDataFrames to plot.
    color_col_list : list of str
        List of column names (one per layer) used for coloring.
    palette_list : list of dict
        List of palettes (one per layer), mapping class value to color.
    legend_name_list : list of str, optional
        List of legend titles per layer. Defaults to "Layer 1", "Layer 2", etc.
    zoom_start : int
        Initial map zoom level.
    map_height : str
        Height of the map (e.g., "400px").
    map_width : str
        Width of the map (e.g., "100%").
    basemap : str
        Folium tiles provider (e.g., "Esri.WorldImagery" for satellite).
    """

    if legend_name_list is None:
        legend_name_list = [f"Layer {i + 1}" for i in range(len(layers))]

    # --- Load AOI boundary (Plateaux region, Togo) ---
    world1 = gpd.read_file(
        "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip"
    )
    aoi = world1[(world1["admin"] == "Togo") & (world1["name"] == "Plateaux")]
    aoi = aoi.to_crs("ESRI:102022")
    aoi_4326 = aoi.to_crs(epsg=4326)

    # --- Reproject layers ---
    layers_4326 = [gdf.to_crs(epsg=4326) for gdf in layers]

    # --- Create map ---
    bounds = aoi_4326.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=basemap,
                   width=map_width, height=map_height)

    # --- Add AOI boundary ---
    folium.GeoJson(
        aoi_4326,
        name="Plateaux region boundary",
        style_function=lambda x: {"color": "black", "weight": 2, "fill": False}
    ).add_to(m)

    # --- Add layers ---
    for i, gdf in enumerate(layers_4326):
        color_col = color_col_list[i]
        palette = palette_list[i]
        fg = folium.FeatureGroup(name=legend_name_list[i])
        for cls, color in palette.items():
            sub = gdf[gdf[color_col] == cls]
            for _, row in sub.iterrows():
                geom = row.geometry
                if isinstance(geom, Point):
                    folium.CircleMarker(
                        location=[geom.y, geom.x],
                        radius=4,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.8,
                        popup=f"{color_col}: {cls}"
                    ).add_to(fg)
                elif isinstance(geom, LineString):
                    folium.PolyLine(
                        locations=[(y, x) for x, y in geom.coords],
                        color=color,
                        weight=3,
                        popup=f"{color_col}: {cls}"
                    ).add_to(fg)
                elif isinstance(geom, (Polygon, MultiPolygon)):
                    folium.GeoJson(
                        geom.__geo_interface__,
                        style_function=lambda x, c=color: {
                            "fillColor": c,
                            "color": c,
                            "weight": 2,
                            "fillOpacity": 0.5
                        },
                        popup=f"{color_col}: {cls}"
                    ).add_to(fg)
                else:
                    folium.GeoJson(
                        geom.__geo_interface__,
                        style_function=lambda x, c=color: {
                            "fillColor": c,
                            "color": c,
                            "weight": 2,
                            "fillOpacity": 0.5
                        },
                        popup=f"{color_col}: {cls}"
                    ).add_to(fg)
        fg.add_to(m)

    # --- Add Layer Control ---
    folium.LayerControl().add_to(m)

    return m


# !/usr/bin/env python
# coding: utf-8

import geopandas as gpd
import folium
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import branca.colormap as cm


def plot_map(layers,
                              color_col_list=None,
                              palette_list=None,
                              legend_name_list=None,
                              zoom_start=7,
                              map_height="400px",
                              map_width="100%",
                              basemap="Esri.WorldImagery"):
    """
    Flexible plotting of multiple GeoDataFrame layers over the Plateaux region of Togo.
    - Layers can be categorical, continuous, or None (just plot geometries).
    - Palette and color column can be None for default styling.

    Parameters
    ----------
    layers : list of GeoDataFrame
        List of GeoDataFrames to plot.
    color_col_list : list of str or None
        List of column names used for coloring per layer. Use None for default styling.
    palette_list : list of dict or None
        List of palettes (for categorical columns). Use None for default styling.
    legend_name_list : list of str, optional
        List of legend titles per layer.
    zoom_start : int
        Initial map zoom level.
    map_height, map_width : str
        Map display dimensions.
    basemap : str
        Folium tiles provider (default Esri.WorldImagery for satellite).
    """

    n_layers = len(layers)

    if legend_name_list is None:
        legend_name_list = [f"Layer {i + 1}" for i in range(n_layers)]
    if color_col_list is None:
        color_col_list = [None] * n_layers
    if palette_list is None:
        palette_list = [None] * n_layers

    # --- Load AOI boundary (Plateaux region, Togo) ---
    world1 = gpd.read_file(
        "https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip"
    )
    aoi = world1[(world1["admin"] == "Togo") & (world1["name"] == "Plateaux")]
    aoi = aoi.to_crs("ESRI:102022")
    aoi_4326 = aoi.to_crs(epsg=4326)

    # --- Reproject layers ---
    layers_4326 = [gdf.to_crs(epsg=4326) for gdf in layers]

    # --- Create map ---
    bounds = aoi_4326.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=basemap,
                   width=map_width, height=map_height)

    # --- Add AOI boundary ---
    folium.GeoJson(
        aoi_4326,
        name="Plateaux region boundary",
        style_function=lambda x: {"color": "black", "weight": 2, "fill": False}
    ).add_to(m)

    # --- Add layers ---
    for i, gdf in enumerate(layers_4326):
        color_col = color_col_list[i]
        palette = palette_list[i]
        fg = folium.FeatureGroup(name=legend_name_list[i])

        # No color column → default styling
        if color_col is None or color_col not in gdf.columns:
            for _, row in gdf.iterrows():
                geom = row.geometry
                if isinstance(geom, Point):
                    folium.CircleMarker(
                        location=[geom.y, geom.x],
                        radius=4,
                        color="blue",
                        fill=True,
                        fill_color="blue",
                        fill_opacity=0.6
                    ).add_to(fg)
                elif isinstance(geom, LineString):
                    folium.PolyLine(
                        locations=[(y, x) for x, y in geom.coords],
                        color="green",
                        weight=2
                    ).add_to(fg)
                elif isinstance(geom, (Polygon, MultiPolygon)):
                    folium.GeoJson(
                        geom.__geo_interface__,
                        style_function=lambda x: {
                            "fillColor": "orange",
                            "color": "orange",
                            "weight": 2,
                            "fillOpacity": 0.4
                        }
                    ).add_to(fg)
            fg.add_to(m)
            continue

        # Categorical column with palette
        if palette is not None:
            for cls, color in palette.items():
                sub = gdf[gdf[color_col] == cls]
                for _, row in sub.iterrows():
                    geom = row.geometry
                    _add_geom_to_fg(fg, geom, color, color_col, cls)
            fg.add_to(m)
            continue

        # Continuous column → LinearColormap
        values = gdf[color_col]
        colormap = cm.LinearColormap(['blue', 'yellow', 'red'],
                                     vmin=values.min(), vmax=values.max())
        for _, row in gdf.iterrows():
            geom = row.geometry
            color = colormap(row[color_col])
            _add_geom_to_fg(fg, geom, color, color_col, row[color_col])
        colormap.caption = legend_name_list[i]
        colormap.add_to(m)
        fg.add_to(m)

    # --- Add Layer Control ---
    folium.LayerControl().add_to(m)

    return m


def _add_geom_to_fg(fg, geom, color, col_name=None, value=None):
    """Helper to add a single geometry to a FeatureGroup."""
    popup_text = f"{col_name}: {value}" if col_name else None
    if isinstance(geom, Point):
        folium.CircleMarker(
            location=[geom.y, geom.x],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=popup_text
        ).add_to(fg)
    elif isinstance(geom, LineString):
        folium.PolyLine(
            locations=[(y, x) for x, y in geom.coords],
            color=color,
            weight=3,
            popup=popup_text
        ).add_to(fg)
    elif isinstance(geom, (Polygon, MultiPolygon)):
        folium.GeoJson(
            geom.__geo_interface__,
            style_function=lambda x, c=color: {
                "fillColor": c,
                "color": c,
                "weight": 2,
                "fillOpacity": 0.5
            },
            popup=popup_text
        ).add_to(fg)
    else:
        folium.GeoJson(
            geom.__geo_interface__,
            style_function=lambda x, c=color: {
                "fillColor": c,
                "color": c,
                "weight": 2,
                "fillOpacity": 0.5
            },
            popup=popup_text
        ).add_to(fg)
