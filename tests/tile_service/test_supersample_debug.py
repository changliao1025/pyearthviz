"""
Simple debug test for get_cartopy_source_with_supersample()
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from pyearthviz.map import RasterTileServer

# Test with a very simple case
print("Testing get_cartopy_source_with_supersample()...")

# Small extent for quick testing
extent = [-122.5, -122.3, 37.7, 37.8]
zoom = 10

try:
    print("\n1. Testing standard get_cartopy_source()...")
    server = RasterTileServer('Esri.Terrain')
    tiles = server.get_cartopy_source()

    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_image(tiles, zoom)
    plt.savefig('test_standard.png', dpi=100)
    plt.close()
    print("   ✓ Standard method works!")

except Exception as e:
    print(f"   ✗ Standard method failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n2. Testing get_cartopy_source_with_supersample(supersample=0)...")
    server = RasterTileServer('Esri.Terrain')
    tiles = server.get_cartopy_source_with_supersample(supersample=0)

    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_image(tiles, zoom)
    plt.savefig('test_supersample_0.png', dpi=100)
    plt.close()
    print("   ✓ Supersample=0 works!")

except Exception as e:
    print(f"   ✗ Supersample=0 failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n3. Testing get_cartopy_source_with_supersample(supersample=1)...")
    server = RasterTileServer('Esri.Terrain')
    tiles = server.get_cartopy_source_with_supersample(supersample=1)

    fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_image(tiles, zoom)
    plt.savefig('test_supersample_1.png', dpi=100)
    plt.close()
    print("   ✓ Supersample=1 works!")

except Exception as e:
    print(f"   ✗ Supersample=1 failed: {e}")
    import traceback
    traceback.print_exc()

print("\nDebug test complete!")
