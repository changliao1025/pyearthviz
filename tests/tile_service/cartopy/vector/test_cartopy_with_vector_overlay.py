"""Cartopy overlay supersample test."""

import os


import matplotlib
import matplotlib.pyplot as plt
#matplotlib.use('Agg') 
import cartopy.crs as ccrs
from osgeo import gdal
from matplotlib.patches import Polygon as mpolygon
from pyearth.gis.gdal.gdal_vector_format_support import get_vector_driver_from_filename
from pyearth.gis.location.get_geometry_coordinates import get_geometry_coordinates

from pyearthviz.map import RasterTileServer
from pyearth.gis.gdal.read.vector.gdal_get_vector_extent import gdal_get_vector_extent

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_EXTENT = [97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
TEST_ZOOM = None

#read boundary file

sFilename_basin_boundary = os.path.join(os.path.dirname(__file__), '..', '..', '..','..','data', 'basin_boundary_qinghaihu.geojson')
sFilename_lake_boundary = os.path.join(os.path.dirname(__file__), '..', '..', '..','..','data', 'lake_boundary_qinghaihu.geojson')
##convert to absolute path
sFilename_basin_boundary = os.path.abspath(sFilename_basin_boundary)
print(f"Boundary file: {sFilename_basin_boundary}")
extent = gdal_get_vector_extent(sFilename_basin_boundary)
print(f"Boundary extent: {extent}")


def add_vector_overlay(ax, sFilename_vector, edgecolor='blue', linewidth=2.0,
                       pProjection_data=None):
    """Add a polygon vector overlay to a cartopy axes using pure GDAL/OGR.

    Mirrors the manual matplotlib.patches.Polygon approach used in
    pyearthviz.map.vector.map_vector_polygon_file (no geopandas dependency).
    """
    if pProjection_data is None:
        pProjection_data = ccrs.PlateCarree()

    pDriver = get_vector_driver_from_filename(sFilename_vector)
    pDataset = pDriver.Open(sFilename_vector, gdal.GA_ReadOnly)
    pLayer = pDataset.GetLayer(0)
    for pFeature in pLayer:
        pGeometry_in = pFeature.GetGeometryRef()
        sGeometry_type = pGeometry_in.GetGeometryName()
        if sGeometry_type == 'MULTIPOLYGON':
            for i in range(pGeometry_in.GetGeometryCount()):
                pPolygon = pGeometry_in.GetGeometryRef(i)
                aCoords_gcs = get_geometry_coordinates(pPolygon)[:, 0:2]
                mPolygon = mpolygon(aCoords_gcs, closed=True, edgecolor=edgecolor,
                                    facecolor='none', linewidth=linewidth,
                                    transform=pProjection_data)
                ax.add_patch(mPolygon)
        elif sGeometry_type == 'POLYGON':
            aCoords_gcs = get_geometry_coordinates(pGeometry_in)[:, 0:2]
            mPolygon = mpolygon(aCoords_gcs, closed=True, edgecolor=edgecolor,
                                facecolor='none', linewidth=linewidth,
                                transform=pProjection_data)
            ax.add_patch(mPolygon)
        else:
            print('Geometry type not supported: ', sGeometry_type)
    pDataset = pLayer = pFeature = None


def test_cartopy_overlay(provider=None):
    import cartopy.crs as ccrs
    TEST_ZOOM = None
    """Render terrain and hydro overlays for each supersample setting."""
    terrain_server = RasterTileServer(provider) if provider else RasterTileServer('Esri.Terrain')
    if not getattr(terrain_server, 'is_accessible', True):
        print(f"  - Skipping provider '{provider}': unavailable or requires an API key.")
        return False
    zoom_level = terrain_server.get_default_zoom(TEST_EXTENT) if TEST_ZOOM is None else TEST_ZOOM
    
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())

    terrain_server.add_basemap(ax,TEST_EXTENT, zoom_level=zoom_level)
    
    #now add the boundary overlay (pure GDAL/OGR, no geopandas)
    add_vector_overlay(ax, sFilename_lake_boundary, edgecolor='blue', linewidth=2.0)
    add_vector_overlay(ax, sFilename_basin_boundary, edgecolor='red', linewidth=2.0)

    gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False
    ax.set_title(f"Terrain + Lake Boundary", fontsize=12, pad=10)
    #show the figure
    
    filename = f"{provider.replace('.', '_').lower()}_cartopy_overlay.png"
    output_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(output_path):
        os.remove(output_path)
    try:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(output_path)
    finally:
        plt.close(fig)
    assert os.path.exists(output_path), f'Missing output file: {output_path}'

    return True

if __name__ == '__main__':

    #test with all providers
    provider = 'Esri.WorldTopo'
          
    success = test_cartopy_overlay(provider) 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)