"""Cartopy overlay supersample test."""

import os

import cartopy.crs as ccrs
import matplotlib.pyplot as plt

from pyearthviz.map import RasterTileServer

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_EXTENT = [97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
TEST_ZOOM = None


def test_cartopy_overlay():
    """Render terrain and hydro overlays for each supersample setting."""
    terrain_server = RasterTileServer('Esri.Terrain')
    hydro_server = RasterTileServer('Esri.Hydro')
    zoom_level = terrain_server.get_default_zoom(TEST_EXTENT) if TEST_ZOOM is None else TEST_ZOOM

    for config in [
        {'name': 'no_supersample', 'desc': 'No Supersample', 'supersample': 0},
        {'name': 'supersample_1', 'desc': 'Supersample=1', 'supersample': 1},
        {'name': 'supersample_2', 'desc': 'Supersample=2', 'supersample': 2},
    ]:
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())

        terrain_tiles = (
            terrain_server.get_cartopy_source(supersample=config['supersample'])
            if config['supersample'] > 0
            else terrain_server.get_cartopy_source()
        )
        ax.add_image(terrain_tiles, zoom_level, alpha=1.0)

        hydro_tiles = (
            hydro_server.get_cartopy_source(supersample=config['supersample'])
            if config['supersample'] > 0
            else hydro_server.get_cartopy_source()
        )
        ax.add_image(hydro_tiles, zoom_level, alpha=0.8)

        gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
        gl.top_labels = False
        gl.right_labels = False
        ax.set_title(f"Terrain + Hydro\n{config['desc']}", fontsize=12, pad=10)

        filename = f"terrain_hydro_overlay_{config['name']}.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        assert os.path.exists(output_path), f'Missing output file: {output_path}'

    return True

if __name__ == '__main__':
    success = test_cartopy_overlay() 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)