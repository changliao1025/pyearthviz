import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import geopandas as gpd
from pyearthviz.map import RasterTileServer
import contextily as cx
from pyearth.gis.gdal.read.vector.gdal_get_vector_extent import gdal_get_vector_extent
# 1. Define your exact Esri URL that works in QGIS
# Or {z}/{x}/{y} depending on your URL format
url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
TEST_EXTENT = [97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
TEST_ZOOM = None

#read boundary file

sFilename_basin_boundary = os.path.join(os.path.dirname(__file__), '..', '..', '..','..','data', 'basin_boundary_qinghaihu.geojson')
sFilename_lake_boundary = os.path.join(os.path.dirname(__file__), '..', '..', '..','..','data', 'lake_boundary_qinghaihu.geojson')
##convert to absolute path
sFilename_basin_boundary = os.path.abspath(sFilename_basin_boundary)
print(f"Boundary file: {sFilename_basin_boundary}")
extent = gdal_get_vector_extent(sFilename_basin_boundary)
class ExactQGISTiles(cimgt.GoogleTiles):
    def _image_url(self, tile):
        x, y, z = tile        
        
        return url.format(x=x, y=y, z=z)

tiles = ExactQGISTiles()

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': ccrs.PlateCarree()})

ax.add_image(tiles, 9)
boundary = gpd.read_file(sFilename_lake_boundary)

ax.add_geometries(boundary.geometry, crs=ccrs.PlateCarree(), edgecolor='blue', facecolor='none', linewidth=2.0)
boundary = gpd.read_file(sFilename_basin_boundary)
ax.add_geometries(boundary.geometry, crs=ccrs.PlateCarree(), edgecolor='red', facecolor='none', linewidth=2.0)
ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())


plt.show()