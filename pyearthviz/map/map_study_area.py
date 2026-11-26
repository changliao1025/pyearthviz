"""Plot a publication-ready map of a study area with basemap, DEM, and vector data."""

import os
import textwrap
from urllib.error import URLError

import cartopy as cpl
import cartopy.crs as ccrs
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter
from osgeo import gdal, ogr, osr
from pyearth.gis.gdal.read.raster.gdal_read_geotiff_file import gdal_read_geotiff_file
from pyearth.gis.location.get_geometry_coordinates import get_geometry_coordinates
from pyearth.gis.spatialref.reproject_coordinates import reproject_coordinates_batch

from pyearthviz.map.raster_map_servers import RasterTileServer
from pyearthviz.map.zebra_frame import zebra_frame

PROVIDER_ALIASES = {
    "openstreetmap": "OSM.Standard",
    "osm": "OSM.Standard",
    "osm.standard": "OSM.Standard",
    "osm.hot": "OSM.HOT",
    "esri.imagery": "Esri.WorldImagery",
    "esri.worldimagery": "Esri.WorldImagery",
    "esri.terrain": "Esri.Terrain",
    "esri.topo": "Esri.WorldTopo",
    "esri.worldtopo": "Esri.WorldTopo",
    "google.satellite": "Google.Satellite",
    "google.streets": "Google.Streets",
}


def _resolve_provider(provider_name):
    if not provider_name:
        return "OSM.Standard"
    return PROVIDER_ALIASES.get(provider_name.lower(), provider_name)


def _to_file_list(val):
    if val is None:
        return []
    if isinstance(val, (str, os.PathLike)):
        return [str(val)]
    return [str(x) for x in val]


def _extract_coords_from_geometry(pGeometry):
    """Extract list of Nx2 coordinate arrays from geometry."""
    if pGeometry is None:
        return []
    sGeometry_type = pGeometry.GetGeometryName().upper()
    if sGeometry_type in ["MULTIPOLYGON", "MULTILINESTRING", "GEOMETRYCOLLECTION"]:
        result = []
        for i in range(pGeometry.GetGeometryCount()):
            sub_geom = pGeometry.GetGeometryRef(i)
            result.extend(_extract_coords_from_geometry(sub_geom))
        return result
    else:
        coords = get_geometry_coordinates(pGeometry)
        arr = np.array(coords)
        if arr.ndim == 1 and len(arr) >= 2:
            arr = arr.reshape(1, -1)
        if arr.ndim == 2 and arr.shape[1] >= 2:
            return [arr[:, 0:2]]
        return []


def map_study_area(
    sFilename_dem_in=None,
    sFilename_out=None,
    sFilename_polygon_in=None,
    sFilename_slope_in=None,
    sFilename_point_in=None,
    sFilename_polyline_in=None,
    aFilename_vector_in=None,
    aBasemap_provider_in=None,
    iBasemap_zoom_level_in=None,
    dAlpha_dem_in=None,
    aExtent_in=None,
    pProjection_map_in=None,
    sTitle_in=None,
    iDPI_in=None,
    iSize_x_in=None,
    iSize_y_in=None,
    sColormap_dem_in=None,
    sColormap_slope_in=None,
    sUnit_dem_in=None,
    iFlag_zebra_in=None,
    iFlag_inset_in=None,
    sFilename_output_in=None,
    **kwargs,
):
    """Plot a study area map with optional DEM overlay, basemap tiles, slope distribution,

    and vector layers.

    Parameters
    ----------
    sFilename_dem_in : str, optional
        Path to digital elevation model (DEM) GeoTIFF file. If provided, DEM is
        plotted with transparency and the slope distribution is calculated and
        plotted in a histogram.
    sFilename_out : str, optional
        Output image file path (e.g. .png, .pdf, .jpg).
    sFilename_polygon_in : str or list of str, optional
        Path or list of paths to polygon vector file(s).
    sFilename_slope_in : str, optional
        Path to slope GeoTIFF file. If not provided and DEM is available,
        slope is calculated directly from DEM.
    sFilename_point_in : str or list of str, optional
        Path or list of paths to point vector file(s).
    sFilename_polyline_in : str or list of str, optional
        Path or list of paths to polyline vector file(s).
    aFilename_vector_in : list of str, optional
        List of vector files (polygons, polylines, or points).
    aBasemap_provider_in : str or list of str, optional
        Tile provider(s) for the basemap (e.g. 'OpenStreetMap', 'Esri.WorldImagery',
        'Esri.Terrain'). Defaults to ['OpenStreetMap'].
    iBasemap_zoom_level_in : int, optional
        Zoom level for the basemap tiles. Auto-calculated if None.
    dAlpha_dem_in : float, optional
        Alpha transparency for the DEM overlay (default 0.5).
    aExtent_in : list of float, optional
        Map extent [min_lon, max_lon, min_lat, max_lat] in degrees.
    pProjection_map_in : cartopy.crs.CRS, optional
        Cartopy projection for the main map. Defaults to ccrs.PlateCarree().
    sTitle_in : str, optional
        Title for the map.
    iDPI_in : int, optional
        Figure DPI (default 300).
    iSize_x_in : float, optional
        Figure width in inches (default 8).
    iSize_y_in : float, optional
        Figure height in inches (default 8).
    sColormap_dem_in : str or Colormap, optional
        Colormap for the DEM layer (default 'terrain').
    sColormap_slope_in : str, optional
        Color for slope histogram (default 'skyblue').
    sUnit_dem_in : str, optional
        Elevation unit label for colorbar (default 'Unit: meter').
    iFlag_inset_in : int, optional
        Flag to show overview inset map (1 to show, 0 to hide).
    sFilename_output_in : str, optional
        Alias for sFilename_out.
    """
    # Resolve output path
    if sFilename_out is None and sFilename_output_in is not None:
        sFilename_out = sFilename_output_in
    if sFilename_dem_in is not None and sFilename_out is None:
        ext = os.path.splitext(str(sFilename_dem_in))[1].lower()
        if ext in [
            ".png",
            ".jpg",
            ".jpeg",
            ".pdf",
            ".svg",
            ".tif",
        ] and not os.path.exists(str(sFilename_dem_in)):
            sFilename_out = sFilename_dem_in
            sFilename_dem_in = None

    # Collect vector files
    aPolygon_files = _to_file_list(sFilename_polygon_in)
    aPolyline_files = _to_file_list(sFilename_polyline_in)
    aPoint_files = _to_file_list(sFilename_point_in)

    if aFilename_vector_in is not None:
        for sFile in _to_file_list(aFilename_vector_in):
            if not os.path.exists(sFile):
                continue
            ds_check = ogr.Open(sFile, gdal.GA_ReadOnly)
            if ds_check is None:
                continue
            layer_check = ds_check.GetLayer(0)
            feat_check = layer_check.GetNextFeature()
            if feat_check is not None:
                geom_check = feat_check.GetGeometryRef()
                if geom_check is not None:
                    gname = geom_check.GetGeometryName().upper()
                    if "POLYGON" in gname:
                        aPolygon_files.append(sFile)
                    elif "LINE" in gname:
                        aPolyline_files.append(sFile)
                    elif "POINT" in gname:
                        aPoint_files.append(sFile)
                    else:
                        aPolygon_files.append(sFile)
            ds_check = None

    has_dem = sFilename_dem_in is not None and os.path.exists(str(sFilename_dem_in))
    has_slope_file = sFilename_slope_in is not None and os.path.exists(
        str(sFilename_slope_in)
    )
    has_slope = has_slope_file or has_dem

    # First vector file determines extent if no explicit input extent is provided
    sFirst_vector_file = None
    if aFilename_vector_in:
        sFirst_vector_file = _to_file_list(aFilename_vector_in)[0]
    elif aPolygon_files:
        sFirst_vector_file = aPolygon_files[0]
    elif aPolyline_files:
        sFirst_vector_file = aPolyline_files[0]
    elif aPoint_files:
        sFirst_vector_file = aPoint_files[0]

    # Target CRS is WGS84 (EPSG:4326) with traditional GIS order (lon, lat)
    pSRS_wgs84 = ccrs.PlateCarree()
    pSpatialRef_wgs84 = osr.SpatialReference()
    pSpatialRef_wgs84.ImportFromEPSG(4326)
    pSpatialRef_wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    # Determine extent:
    # 1. explicit aExtent_in
    # 2. first vector file
    # 3. if DEM is provided and no vector, DEM extent in degree
    aExtent = None
    if aExtent_in is not None:
        aExtent = [float(x) for x in aExtent_in]
    elif sFirst_vector_file is not None and os.path.exists(sFirst_vector_file):
        ds_vec = ogr.Open(sFirst_vector_file, gdal.GA_ReadOnly)
        if ds_vec is not None:
            layer = ds_vec.GetLayer(0)
            layer_srs = layer.GetSpatialRef()
            coord_trans = None
            if layer_srs and not layer_srs.IsSame(pSpatialRef_wgs84):
                layer_srs_clone = layer_srs.Clone()
                layer_srs_clone.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                coord_trans = osr.CoordinateTransformation(
                    layer_srs_clone, pSpatialRef_wgs84
                )

            dLon_min, dLon_max = 180.0, -180.0
            dLat_min, dLat_max = 90.0, -90.0
            found_coords = False

            for feat in layer:
                geom = feat.GetGeometryRef()
                if geom is None:
                    continue
                if coord_trans is not None:
                    geom = geom.Clone()
                    geom.Transform(coord_trans)
                sub_coords_list = _extract_coords_from_geometry(geom)
                for coords in sub_coords_list:
                    if len(coords) > 0:
                        found_coords = True
                        dLon_min = min(dLon_min, float(np.min(coords[:, 0])))
                        dLon_max = max(dLon_max, float(np.max(coords[:, 0])))
                        dLat_min = min(dLat_min, float(np.min(coords[:, 1])))
                        dLat_max = max(dLat_max, float(np.max(coords[:, 1])))

            ds_vec = None
            if found_coords:
                marginx = (dLon_max - dLon_min) / 20.0
                marginy = (dLat_max - dLat_min) / 20.0
                if marginx <= 0:
                    marginx = 0.02
                if marginy <= 0:
                    marginy = 0.02
                dLon_min = max(-180.0, dLon_min - marginx)
                dLon_max = min(180.0, dLon_max + marginx)
                dLat_min = max(-90.0, dLat_min - marginy)
                dLat_max = min(90.0, dLat_max + marginy)
                aExtent = [dLon_min, dLon_max, dLat_min, dLat_max]

    if aExtent is None and has_dem:
        ds_dem = gdal.Open(str(sFilename_dem_in), gdal.GA_ReadOnly)
        if ds_dem is not None:
            srs_wkt = ds_dem.GetProjection()
            dem_srs = osr.SpatialReference()
            if srs_wkt:
                dem_srs.ImportFromWkt(srs_wkt)
            else:
                dem_srs.ImportFromEPSG(4326)
            dem_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

            gt = ds_dem.GetGeoTransform()
            x0 = gt[0]
            x1 = gt[0] + gt[1] * ds_dem.RasterXSize
            y0 = gt[3]
            y1 = gt[3] + gt[5] * ds_dem.RasterYSize

            if dem_srs.IsGeographic():
                aExtent = [min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)]
            else:
                corners_x = [x0, x1, x0, x1]
                corners_y = [y0, y0, y1, y1]
                reproj_lon, reproj_lat = reproject_coordinates_batch(
                    corners_x, corners_y, dem_srs, pSpatialRef_wgs84
                )
                aExtent = [
                    min(reproj_lon),
                    max(reproj_lon),
                    min(reproj_lat),
                    max(reproj_lat),
                ]
            ds_dem = None

    if aExtent is None:
        raise ValueError(
            "Map extent could not be determined. Please provide aExtent_in, a valid vector file, or sFilename_dem_in."
        )

    # Validate and clamp aExtent [min_lon, max_lon, min_lat, max_lat]
    minx, maxx, miny, maxy = aExtent
    if abs(minx) <= 90 and abs(maxx) <= 90 and (abs(miny) > 90 or abs(maxy) > 90):
        aExtent = [miny, maxy, minx, maxx]
    aExtent = [
        max(-180.0, min(180.0, aExtent[0])),
        max(-180.0, min(180.0, aExtent[1])),
        max(-85.0511, min(85.0511, aExtent[2])),
        max(-85.0511, min(85.0511, aExtent[3])),
    ]
    dLon_min, dLon_max, dLat_min, dLat_max = aExtent

    # Defaults and parameters
    iDPI = iDPI_in if iDPI_in is not None else 300
    iSize_x = iSize_x_in if iSize_x_in is not None else 8
    iSize_y = iSize_y_in if iSize_y_in is not None else 8
    dAlpha_dem = dAlpha_dem_in if dAlpha_dem_in is not None else 0.5
    sColormap_dem = sColormap_dem_in if sColormap_dem_in is not None else "terrain"
    sColor_slope = sColormap_slope_in if sColormap_slope_in is not None else "skyblue"
    sUnit_dem = sUnit_dem_in if sUnit_dem_in is not None else "Unit: meter"

    if pProjection_map_in is not None:
        pProjection_map = pProjection_map_in
    else:
        pProjection_map = ccrs.Orthographic(
            central_longitude=0.50 * (dLon_max + dLon_min),
            central_latitude=0.50 * (dLat_max + dLat_min),
            globe=None,
        )

    # Basemap provider setup
    if aBasemap_provider_in is None:
        aBasemap_provider = [_resolve_provider("OSM.Standard")]
    elif not aBasemap_provider_in:
        aBasemap_provider = []
    elif isinstance(aBasemap_provider_in, str):
        aBasemap_provider = [_resolve_provider(aBasemap_provider_in)]
    else:
        aBasemap_provider = [_resolve_provider(x) for x in aBasemap_provider_in]

    # Zebra frame flag
    if iFlag_zebra_in is not None:
        iFlag_zebra = int(iFlag_zebra_in)
    else:
        iFlag_zebra = 0

    # Inset flag
    if iFlag_inset_in is not None:
        iFlag_inset = int(iFlag_inset_in)
    else:
        iFlag_inset = 1 if (len(aPolygon_files) > 0 or aExtent is not None) else 0

    # Initialize figure
    fig = plt.figure(dpi=iDPI, figsize=(iSize_x, iSize_y))
    plot_width_inch = fig.get_size_inches()[0] * fig.dpi
    char_width_inch = 0.1 * fig.dpi
    cwidth = max(20, int(plot_width_inch / char_width_inch))

    # Initial main map placement (will be dynamically measured after drawing)
    if has_dem:
        ax = fig.add_axes([0.17, 0.05, 0.76, 0.65], projection=pProjection_map)
    else:
        ax = fig.add_axes([0.15, 0.05, 0.78, 0.65], projection=pProjection_map)
    ax.set_extent(aExtent, crs=pSRS_wgs84)

    # 1. Add basemap tiles on the main map
    try:
        if iBasemap_zoom_level_in is not None:
            iBasemap_zoom_level = iBasemap_zoom_level_in
        else:
            image_size = [1000, 1000]
            scale_denominator = RasterTileServer.calculate_scale_denominator(
                aExtent, image_size
            )
            pSrc = osr.SpatialReference()
            pSrc.ImportFromEPSG(3857)
            pProjection = pSrc.ExportToWkt()
            iBasemap_zoom_level = RasterTileServer.calculate_zoom_level(
                scale_denominator, pProjection, dpi=int(iDPI / 2)
            )
            iBasemap_zoom_level = min(18, max(0, iBasemap_zoom_level))

        if aBasemap_provider:
            nTile_provider = min(len(aBasemap_provider), 5)
            dAlpha_base = 1.0
            aLicense_info_list = []
            for i in range(nTile_provider):
                sBasemap_provider = aBasemap_provider[i]
                pTile_service = RasterTileServer(sBasemap_provider)
                pBasemap = pTile_service.add_basemap(
                    ax,
                    aExtent,
                    iBasemap_zoom_level,
                    alpha=max(0.1, dAlpha_base - i * 0.1),
                    zorder=1,
                )
                aLicense_info_list.append(pBasemap.attribution)

            if aLicense_info_list:
                aLicense_info_list.append("Visualized by PyEarthViz")
                sLicense_info = " | ".join(aLicense_info_list)
                sLicense_info_wrapped = "\n".join(
                    textwrap.wrap(sLicense_info, width=cwidth)
                )
                ax.text(
                    0.98,
                    0.02,
                    sLicense_info_wrapped,
                    transform=ax.transAxes,
                    ha="right",
                    va="bottom",
                    fontsize=4.5,
                    color="dimgray",
                    bbox=dict(
                        facecolor="white",
                        edgecolor="none",
                        alpha=0.6,
                        boxstyle="round,pad=0.2",
                    ),
                    zorder=20,
                )
    except (URLError, Exception) as e:
        print(f"Notice: Basemap tile fetch skipped or unavailable ({e}).")
        iBasemap_zoom_level = 7

    # 2. Add DEM overlay with transparency if provided
    demplot = None
    if has_dem:
        ds_dem_in = gdal.Open(str(sFilename_dem_in), gdal.GA_ReadOnly)
        if ds_dem_in is not None:
            srs_wkt = ds_dem_in.GetProjection()
            dem_srs = osr.SpatialReference()
            if srs_wkt:
                dem_srs.ImportFromWkt(srs_wkt)
            else:
                dem_srs.ImportFromEPSG(4326)

            if not dem_srs.IsGeographic():
                ds_dem_geo = gdal.Warp("", ds_dem_in, dstSRS="EPSG:4326", format="MEM")
            else:
                ds_dem_geo = ds_dem_in

            gt_dem = ds_dem_geo.GetGeoTransform()
            x_min = gt_dem[0]
            x_max = gt_dem[0] + gt_dem[1] * ds_dem_geo.RasterXSize
            y_max = gt_dem[3]
            y_min = gt_dem[3] + gt_dem[5] * ds_dem_geo.RasterYSize
            aDem_extent = [
                min(x_min, x_max),
                max(x_min, x_max),
                min(y_min, y_max),
                max(y_min, y_max),
            ]

            band_dem = ds_dem_geo.GetRasterBand(1)
            aImage_dem = band_dem.ReadAsArray().astype(float)
            nodata_dem = band_dem.GetNoDataValue()
            if nodata_dem is not None:
                aImage_dem[aImage_dem == nodata_dem] = np.nan

            demplot = ax.imshow(
                aImage_dem,
                origin="upper",
                extent=aDem_extent,
                cmap=plt.colormaps.get(sColormap_dem, mpl.cm.terrain),
                alpha=dAlpha_dem,
                transform=cpl.crs.PlateCarree(),
                zorder=2,
            )

    # 3. Add vector layers
    # Extract first polygon coords for overview inset map
    first_polygon_coords = []

    # Polygons
    sEdgecolor_poly = kwargs.get("sEdgecolor_polygon_in", "blue")
    dLinewidth_poly = kwargs.get("dLinewidth_polygon_in", 0.8)
    for sPolyFile in aPolygon_files:
        if not os.path.exists(sPolyFile):
            continue
        ds_poly = ogr.Open(sPolyFile, gdal.GA_ReadOnly)
        if ds_poly is None:
            continue
        layer_poly = ds_poly.GetLayer(0)
        srs_p = layer_poly.GetSpatialRef()
        coord_trans_p = None
        if srs_p and not srs_p.IsSame(pSpatialRef_wgs84):
            srs_p_clone = srs_p.Clone()
            srs_p_clone.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            coord_trans_p = osr.CoordinateTransformation(srs_p_clone, pSpatialRef_wgs84)

        for feat in layer_poly:
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            if coord_trans_p is not None:
                geom = geom.Clone()
                geom.Transform(coord_trans_p)
            for sub_coords in _extract_coords_from_geometry(geom):
                if len(sub_coords) >= 3:
                    if len(first_polygon_coords) == 0:
                        first_polygon_coords.append(sub_coords)
                    patch = mpl.patches.Polygon(
                        sub_coords,
                        closed=True,
                        linewidth=dLinewidth_poly,
                        edgecolor=sEdgecolor_poly,
                        facecolor="none",
                        alpha=0.9,
                        transform=cpl.crs.PlateCarree(),
                        zorder=10,
                    )
                    ax.add_patch(patch)
        ds_poly = None

    # Polylines
    sColor_line = kwargs.get("sColor_polyline_in", "navy")
    dLinewidth_line = kwargs.get("dLinewidth_polyline_in", 0.7)
    for sLineFile in aPolyline_files:
        if not os.path.exists(sLineFile):
            continue
        ds_line = ogr.Open(sLineFile, gdal.GA_ReadOnly)
        if ds_line is None:
            continue
        layer_line = ds_line.GetLayer(0)
        srs_l = layer_line.GetSpatialRef()
        coord_trans_l = None
        if srs_l and not srs_l.IsSame(pSpatialRef_wgs84):
            srs_l_clone = srs_l.Clone()
            srs_l_clone.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            coord_trans_l = osr.CoordinateTransformation(srs_l_clone, pSpatialRef_wgs84)

        for feat in layer_line:
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            if coord_trans_l is not None:
                geom = geom.Clone()
                geom.Transform(coord_trans_l)
            for sub_coords in _extract_coords_from_geometry(geom):
                if len(sub_coords) >= 2:
                    ax.plot(
                        sub_coords[:, 0],
                        sub_coords[:, 1],
                        color=sColor_line,
                        linewidth=dLinewidth_line,
                        transform=cpl.crs.PlateCarree(),
                        zorder=11,
                    )
        ds_line = None

    # Points
    sColor_pt = kwargs.get("sColor_point_in", "red")
    dSize_pt = kwargs.get("dSize_point_in", 20)
    for sPointFile in aPoint_files:
        if not os.path.exists(sPointFile):
            continue
        ds_point = ogr.Open(sPointFile, gdal.GA_ReadOnly)
        if ds_point is None:
            continue
        layer_point = ds_point.GetLayer(0)
        srs_pt = layer_point.GetSpatialRef()
        coord_trans_pt = None
        if srs_pt and not srs_pt.IsSame(pSpatialRef_wgs84):
            srs_pt_clone = srs_pt.Clone()
            srs_pt_clone.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
            coord_trans_pt = osr.CoordinateTransformation(
                srs_pt_clone, pSpatialRef_wgs84
            )

        for feat in layer_point:
            geom = feat.GetGeometryRef()
            if geom is None:
                continue
            if coord_trans_pt is not None:
                geom = geom.Clone()
                geom.Transform(coord_trans_pt)
            for sub_coords in _extract_coords_from_geometry(geom):
                if len(sub_coords) > 0:
                    ax.scatter(
                        sub_coords[:, 0],
                        sub_coords[:, 1],
                        color=sColor_pt,
                        s=dSize_pt,
                        marker="o",
                        edgecolors="black",
                        linewidths=0.5,
                        transform=cpl.crs.PlateCarree(),
                        zorder=12,
                    )
        ds_point = None

    # Frame, gridlines, and zebra frame on main map
    if iFlag_zebra == 1:
        ax.set_axis_off()
        ax.zebra_frame(crs=pSRS_wgs84, iFlag_outer_frame_in=1)
    else:
        for axis in ["top", "bottom", "left", "right"]:
            ax.spines[axis].set_linewidth(0.5)
        ax.tick_params(width=0.5)

        gl = ax.gridlines(
            crs=cpl.crs.PlateCarree(),
            draw_labels=True,
            linewidth=0.5,
            color="gray",
            alpha=0.4,
            linestyle="--",
        )
        gl.top_labels = False
        gl.right_labels = False
        gl.xformatter = LongitudeFormatter()
        gl.yformatter = LatitudeFormatter()
        gl.xlabel_style = {"size": 8, "color": "k"}
        gl.ylabel_style = {"size": 8, "color": "k"}

    # Set Title if provided
    if sTitle_in:
        ax.set_title(sTitle_in, fontsize=9, pad=6)

    # Re-apply extent and measure exact rendered position of ax
    ax.set_extent(aExtent, crs=pSRS_wgs84)
    fig.canvas.draw()
    map_pos = ax.get_position()
    map_x0 = map_pos.x0
    map_x1 = map_pos.x1
    map_y0 = map_pos.y0
    map_y1 = map_pos.y1
    map_h = map_pos.height

    # 4. Colorbar placed directly adjacent to main map matching exact map height
    cb_x0 = map_x0
    if has_dem and demplot is not None:
        cb_w = 0.020
        cb_gap = 0.050
        cb_x0 = max(0.02, map_x0 - cb_gap - cb_w)
        ax_cb = fig.add_axes([cb_x0, map_y0, cb_w, map_h])
        cb = plt.colorbar(demplot, cax=ax_cb, extend="both")
        cb.ax.get_yaxis().set_ticks_position("left")
        cb.ax.get_yaxis().set_label_position("left")
        cb.ax.set_ylabel(sUnit_dem, fontsize=7, labelpad=4)
        cb.ax.tick_params(labelsize=6, pad=2, length=2)

    # 5. Calculate slope if DEM or slope file is provided
    aSlope = None
    if has_slope:
        if has_slope_file:
            dummy_slope = gdal_read_geotiff_file(sFilename_slope_in)
            aSlope = np.array(dummy_slope["dataOut"], dtype=float)
            mv = dummy_slope.get(
                "missingValue", dummy_slope.get("missing_value", -9999)
            )
            if mv is not None:
                aSlope = aSlope[aSlope != mv]
            aSlope = aSlope[~np.isnan(aSlope)]
        elif has_dem:
            ds_dem_calc = gdal.Open(str(sFilename_dem_in), gdal.GA_ReadOnly)
            if ds_dem_calc is not None:
                srs_wkt = ds_dem_calc.GetProjection()
                srs_dem = osr.SpatialReference()
                if srs_wkt:
                    srs_dem.ImportFromWkt(srs_wkt)
                else:
                    srs_dem.ImportFromEPSG(4326)

                scale = 1.0
                if srs_dem.IsGeographic():
                    gt_calc = ds_dem_calc.GetGeoTransform()
                    lat_center = gt_calc[3] + 0.5 * gt_calc[5] * ds_dem_calc.RasterYSize
                    scale = 111120.0 * np.cos(np.radians(lat_center))
                    if scale <= 0:
                        scale = 111120.0

                ds_slope_res = gdal.DEMProcessing(
                    "",
                    ds_dem_calc,
                    "slope",
                    format="MEM",
                    slopeFormat="degree",
                    computeEdges=True,
                    scale=scale,
                )
                if ds_slope_res is not None:
                    band_sl = ds_slope_res.GetRasterBand(1)
                    aSlope = band_sl.ReadAsArray().astype(float)
                    nodata_sl = band_sl.GetNoDataValue()
                    if nodata_sl is not None:
                        aSlope = aSlope[aSlope != nodata_sl]
                    aSlope = aSlope[~np.isnan(aSlope)]
                ds_dem_calc = None

    has_slope_data = aSlope is not None and len(aSlope) > 0

    # 6. Dynamic placement of top row (Overview Inset and Slope Histogram)
    gap_y = 0.05 if sTitle_in else 0.04
    top_y0 = min(0.78, map_y1 + gap_y)
    top_h = max(0.16, min(0.24, 0.96 - top_y0))
    top_left = cb_x0 if (has_dem and demplot is not None) else map_x0
    top_right = map_x1
    total_w = top_right - top_left
    gap_x = 0.04

    ax_inset = None
    ax_histo = None
    if iFlag_inset == 1 and has_slope_data:
        inset_w = max(0.18, min(0.26, (total_w - gap_x) * 0.36))
        histo_w = (total_w - gap_x) - inset_w
        inset_x0 = top_left
        histo_x0 = inset_x0 + inset_w + gap_x
        ax_inset = fig.add_axes(
            [inset_x0, top_y0, inset_w, top_h], projection=ccrs.Mercator()
        )
        ax_histo = fig.add_axes([histo_x0, top_y0, histo_w, top_h])
    elif iFlag_inset == 1:
        inset_w = min(0.30, total_w)
        ax_inset = fig.add_axes(
            [top_left, top_y0, inset_w, top_h], projection=ccrs.Mercator()
        )
    elif has_slope_data:
        histo_w = min(0.60, total_w)
        histo_x0 = top_left + (total_w - histo_w) / 2.0
        ax_histo = fig.add_axes([histo_x0, top_y0, histo_w, top_h])

    # Draw overview inset map
    if ax_inset is not None:
        span_x = aExtent[1] - aExtent[0]
        span_y = aExtent[3] - aExtent[2]
        inset_extent = [
            max(-180.0, aExtent[0] - span_x * 1.5),
            min(180.0, aExtent[1] + span_x * 1.5),
            max(-80.0, aExtent[2] - span_y * 1.5),
            min(80.0, aExtent[3] + span_y * 1.5),
        ]
        ax_inset.set_extent(inset_extent, crs=pSRS_wgs84)

        try:
            sInset_provider = (
                aBasemap_provider[0]
                if aBasemap_provider
                else _resolve_provider("OSM.Standard")
            )
            pTile_inset = RasterTileServer(sInset_provider)
            inset_zoom = (
                min(14, max(0, iBasemap_zoom_level - 3))
                if iBasemap_zoom_level is not None
                else 4
            )
            pTile_inset.add_basemap(
                ax_inset, inset_extent, zoom_level=inset_zoom, alpha=0.9
            )
        except Exception:
            pass

        if len(first_polygon_coords) > 0:
            for poly_coords in first_polygon_coords:
                patch_inset = mpl.patches.Polygon(
                    poly_coords,
                    closed=True,
                    linewidth=1.2,
                    edgecolor="red",
                    facecolor="red",
                    alpha=0.3,
                    transform=cpl.crs.PlateCarree(),
                    zorder=10,
                )
                ax_inset.add_patch(patch_inset)
        else:
            box_coords = np.array(
                [
                    [aExtent[0], aExtent[2]],
                    [aExtent[1], aExtent[2]],
                    [aExtent[1], aExtent[3]],
                    [aExtent[0], aExtent[3]],
                ]
            )
            rect_inset = mpl.patches.Polygon(
                box_coords,
                closed=True,
                linewidth=1.2,
                edgecolor="red",
                facecolor="red",
                alpha=0.3,
                transform=cpl.crs.PlateCarree(),
                zorder=10,
            )
            ax_inset.add_patch(rect_inset)

        gl_inset = ax_inset.gridlines(
            crs=cpl.crs.PlateCarree(),
            draw_labels=True,
            linewidth=0.4,
            color="gray",
            alpha=0.3,
            linestyle="--",
        )
        gl_inset.top_labels = False
        gl_inset.right_labels = False
        gl_inset.xformatter = LongitudeFormatter()
        gl_inset.yformatter = LatitudeFormatter()
        gl_inset.xlabel_style = {"size": 4, "color": "k"}
        gl_inset.ylabel_style = {"size": 4, "color": "k"}

    # Draw slope histogram
    if ax_histo is not None and has_slope_data:
        dMin_x = 0
        dMax_x = float(min(90.0, max(45.0, np.percentile(aSlope, 99.5))))
        dSpace_x = 2
        n_bins = max(10, int((dMax_x - dMin_x) / dSpace_x))
        ax_histo.hist(
            aSlope,
            bins=n_bins,
            range=(dMin_x, dMax_x),
            color=sColor_slope,
            ec="steelblue",
            alpha=0.8,
        )
        ax_histo.tick_params(axis="x", labelsize=6, pad=1, length=2)
        ax_histo.tick_params(axis="y", labelsize=6, pad=2, length=2)
        ax_histo.set_xlabel("Slope (degree)", fontsize=7, labelpad=1)
        ax_histo.set_ylabel("Frequency", fontsize=7, labelpad=2)
        ax_histo.set_xlim(dMin_x, dMax_x)
        formatter = mpl.ticker.ScalarFormatter(useMathText=True)
        formatter.set_scientific(True)
        formatter.set_powerlimits((-2, 3))
        ax_histo.yaxis.set_major_formatter(formatter)
        ax_histo.yaxis.offsetText.set_fontsize(6)

    # Output handling
    if sFilename_out is not None:
        sDirname = os.path.dirname(sFilename_out)
        if sDirname and not os.path.exists(sDirname):
            os.makedirs(sDirname, exist_ok=True)
        plt.savefig(sFilename_out, bbox_inches="tight", dpi=iDPI)
        plt.close(fig)
    else:
        plt.show()

    return fig
