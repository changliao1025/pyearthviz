"""Optimal zoom recommendation validation."""

from pyearthviz.map import RasterTileServer
extent =[97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]

def test_suggest_optimal_zoom():
    """Ensure the optimal zoom helper returns a value for each preference."""
    server = RasterTileServer('Esri.Terrain')
  

    for preference in ['fast', 'balanced', 'quality']:
        zoom = server.suggest_optimal_zoom(
            extent,
            output_dpi=150,
            output_size=(1200, 1200),
            quality_preference=preference
        )

        assert isinstance(zoom, int)
        assert zoom > 0

if __name__ == '__main__':
    success = test_suggest_optimal_zoom() 

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)