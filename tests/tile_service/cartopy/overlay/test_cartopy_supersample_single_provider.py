"""Cartopy single-provider supersample test."""

import os

import cartopy.crs as ccrs
import matplotlib.pyplot as plt

from pyearthviz.map import RasterTileServer

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_EXTENT = [97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
TEST_ZOOM = None


def test_cartopy_supersample_single_provider(provider_name='Esri.Terrain', api_key=None):
    """Render the same provider at multiple supersample levels."""
    server = RasterTileServer(provider_name, api_key=api_key)
    zoom_level = server.get_default_zoom(TEST_EXTENT) if TEST_ZOOM is None else TEST_ZOOM

    configs = [
        #{'name': 'standard', 'desc': 'Standard (no supersample)', 'supersample': 0},
        {'name': 'supersample_1', 'desc': 'Supersample=1 (2x)', 'supersample': 1},
        {'name': 'supersample_2', 'desc': 'Supersample=2 (4x)', 'supersample': 2},
    ]

    for config in configs:
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())
        tile_source = server.get_cartopy_source(supersample=config['supersample'])
        ax.add_image(tile_source, zoom_level, alpha=0.9)
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
        gl.top_labels = False
        gl.right_labels = False
        ax.set_title(f"{config['desc']}\n({provider_name})", fontsize=12, pad=10)

        safe_provider = provider_name.replace('.', '_').lower()
        filename = f"{safe_provider}_{config['name']}.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        assert os.path.exists(output_path), f'Missing output file: {output_path}'
    return True

if __name__ == '__main__':
    success = test_cartopy_supersample_single_provider() 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)