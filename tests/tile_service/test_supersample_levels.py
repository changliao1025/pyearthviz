"""Supersample validation for tile fetching."""

import os

from PIL import Image

from pyearthviz.map import RasterTileServer
sProvider = 'Esri.Terrain'
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs', sProvider.replace('.', '_').lower()    )
os.makedirs(OUTPUT_DIR, exist_ok=True)
extent =[97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
zoom = None

def test_supersample_levels():
    """Test different supersample levels for raster tiles."""
    server = RasterTileServer(sProvider)
    

    for supersample in [0, 1]:
        img_array = server.fetch_tiles_for_extent(
            extent,
            zoom_level=zoom,
            supersample=supersample,
            resample=True,
        )

        img = Image.fromarray(img_array)
        output_path = os.path.join(OUTPUT_DIR, f'test2_supersample_{supersample}.png')
        img.save(output_path)

        assert img_array.ndim == 3
        assert img_array.shape[2] in (3, 4)
    return True

if __name__ == '__main__':
    success = test_supersample_levels() 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)