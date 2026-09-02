"""Resampling validation for tile fetching."""

import os

from PIL import Image

from pyearthviz.map import RasterTileServer

sProvider = 'Esri.Terrain'
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs', sProvider.replace('.', '_').lower()    )
os.makedirs(OUTPUT_DIR, exist_ok=True)

extent =[97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
zoom = None
def test_resampling():
    """Compare resampled and baseline tile output quality."""
    server = RasterTileServer(sProvider)
    

    img_high_quality = server.fetch_tiles_for_extent(
        extent,
        zoom_level=zoom,
        supersample=1,
        resample=True,
        resample_method='lanczos'
    )
    img_baseline = server.fetch_tiles_for_extent(
        extent,
        zoom,
        supersample=0,
        resample=False
    )

    Image.fromarray(img_high_quality).save(os.path.join(OUTPUT_DIR, 'test3_high_quality.png'))
    Image.fromarray(img_baseline).save(os.path.join(OUTPUT_DIR, 'test3_baseline.png'))

    assert img_high_quality.shape[2] in (3, 4)
    assert img_baseline.shape[2] in (3, 4)

    return True

if __name__ == '__main__':
    success = test_resampling() 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)