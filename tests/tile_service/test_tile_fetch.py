"""Basic tile fetch validation for the raster tile server."""

import os

import numpy as np
from PIL import Image

from pyearthviz.map import RasterTileServer
from pyearth.gis.gdal.read.vector.gdal_get_vector_extent import gdal_get_vector_extent

sProvider = 'Esri.Terrain'
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs', sProvider.replace('.', '_').lower()    )
os.makedirs(OUTPUT_DIR, exist_ok=True)
sFilename_boundary = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'basin_boundary_qinghaihu.geojson')
extent = gdal_get_vector_extent(sFilename_boundary)
print(f"extent: {extent}")
extent =[97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]
zoom = None
def test_basic_tile_fetch():
    """Verify the basic tile fetch returns a valid image array."""
    server = RasterTileServer('Esri.Terrain')      

    img_array = server.fetch_tiles_for_extent(
        extent,
        zoom_level=zoom,
        supersample=0,
        output_dpi = 150,
        resample=True,
        resample_method='lanczos'
    )

    assert isinstance(img_array, np.ndarray), 'Should return numpy array'
    assert len(img_array.shape) == 3, 'Should be a 3D array (height, width, channels)'
    assert img_array.shape[2] in [3, 4], 'Should have RGB or RGBA channels'

    img = Image.fromarray(img_array)
    output_path = os.path.join(OUTPUT_DIR, 'test1_basic_quality.png')
    img.save(output_path)
    return True

if __name__ == '__main__':
    success = test_basic_tile_fetch() 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)