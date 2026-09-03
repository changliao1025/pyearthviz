import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import geopandas as gpd

# 1. Setup the Cartopy Map with Web Mercator (Standard for web tiles)
request = cimgt.MapQuestOSM()
fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': request.crs})


TEST_EXTENT = [97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
TEST_ZOOM = None

ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree()) # Example: Beijing area

sFilename_basin_boundary = os.path.join(os.path.dirname(__file__), '..', '..', '..','..','data', 'basin_boundary_qinghaihu.geojson')
sFilename_lake_boundary = os.path.join(os.path.dirname(__file__), '..', '..', '..','..','data', 'lake_boundary_qinghaihu.geojson')
##convert to absolute path
sFilename_basin_boundary = os.path.abspath(sFilename_basin_boundary)
print(f"Boundary file: {sFilename_basin_boundary}")

# Add the Esri basemap
ax.add_image(request, 8)

# 2. Load the GeoJSONs
boundary = gpd.read_file(sFilename_lake_boundary)
ax.add_geometries(boundary.geometry, crs=ccrs.PlateCarree(), edgecolor='blue', facecolor='none', linewidth=2.0)
boundary = gpd.read_file(sFilename_basin_boundary)
ax.add_geometries(boundary.geometry, crs=ccrs.PlateCarree(), edgecolor='red', facecolor='none', linewidth=2.0)

plt.show()