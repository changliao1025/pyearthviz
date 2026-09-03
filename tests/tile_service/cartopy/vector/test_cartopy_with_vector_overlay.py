"""Cartopy overlay supersample test."""

import os


import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg') 
import geopandas as gpd

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
    terrain_tiles = terrain_server.get_cartopy_source()
    
    ax.add_image(terrain_tiles, zoom_level, alpha=1.0)
    #now add the boundary overlay
    boundary = gpd.read_file(sFilename_lake_boundary)
    ax.add_geometries(boundary.geometry, crs=ccrs.PlateCarree(), edgecolor='blue', facecolor='none', linewidth=2.0)

    boundary = gpd.read_file(sFilename_basin_boundary)
    ax.add_geometries(boundary.geometry, crs=ccrs.PlateCarree(), edgecolor='red', facecolor='none', linewidth=2.0)

    gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False
    ax.set_title(f"Terrain + Lake Boundary", fontsize=12, pad=10)
    filename = f"{provider.replace('.', '_').lower()}_cartopy_overlay.png"
    output_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(output_path):
        os.remove(output_path)
    try:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    finally:
        plt.close(fig)
    assert os.path.exists(output_path), f'Missing output file: {output_path}'

    return True

if __name__ == '__main__':

    #test with all providers
    providers = RasterTileServer.get_available_providers()
    for provider in providers:        
        success = test_cartopy_overlay(provider) 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)