"""
Test script for get_cartopy_source_with_supersample() method.
Tests the supersample feature when using Cartopy's add_image() method.
"""

import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for testing
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from pyearthviz.map import RasterTileServer

# Create output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Test extent (smaller area for faster testing)
dLongitude_center_in = 121
dLatitude_center_in = 31
buffer = 0.4
TEST_EXTENT = [
    dLongitude_center_in - buffer,
    dLongitude_center_in + buffer,
    dLatitude_center_in - buffer,
    dLatitude_center_in + buffer
]
TEST_ZOOM = 10


def test_cartopy_supersample_single_provider(provider_name, api_key=None):
    """
    Test get_cartopy_source_with_supersample() for a single provider.

    Args:
        provider_name: Name of the tile provider
        api_key: Optional API key for providers that require it
    """
    print(f"\n{'='*60}")
    print(f"Testing Cartopy Supersample: {provider_name}")
    print('='*60)

    try:
        server = RasterTileServer(provider_name, api_key=api_key)

        # Create a figure with 4 subplots for comparison
        fig = plt.figure(figsize=(16, 12))

        # Test configurations
        configs = [
            {
                'name': 'standard',
                'desc': 'Standard (no supersample)',
                'method': 'get_cartopy_source',
                'params': {'supersample': 0}
            },
            {
                'name': 'supersample_1',
                'desc': 'Supersample=1 (2x)',
                'method': 'get_cartopy_source',
                'params': {'supersample': 1}
            },
            {
                'name': 'supersample_2',
                'desc': 'Supersample=2 (4x)',
                'method': 'get_cartopy_source',
                'params': {'supersample': 2}
            }
        ]

        for idx, config in enumerate(configs, 1):
            try:
                print(f"  Testing {config['name']:20s} - {config['desc']}")

                # Create subplot
                ax = fig.add_subplot(2, 2, idx, projection=ccrs.PlateCarree())
                ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())

                # Get tile source using the specified method

                tile_source = server.get_cartopy_source(supersample=config['params']['supersample'])

                # Add image to map
                ax.add_image(tile_source, TEST_ZOOM, alpha=0.9)

                # Add gridlines and labels
                gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
                gl.top_labels = False
                gl.right_labels = False

                # Set title
                ax.set_title(f"{config['desc']}\n({provider_name})",
                           fontsize=12, pad=10)

                print(f"    ✓ Success!")

            except Exception as e:
                print(f"    ✗ Failed: {e}")

        # Save the comparison figure
        plt.tight_layout()
        safe_provider = provider_name.replace('.', '_').lower()
        filename = f"{safe_provider}_cartopy_supersample_comparison.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Saved comparison: {filename}")
        return True

    except Exception as e:
        print(f"  ✗ Provider test failed: {e}")
        plt.close('all')
        return False


def test_cartopy_supersample_overlay():
    """
    Test supersample with overlay layers (Terrain + Hydro).
    Tests that black transparency works with supersample.
    """
    print(f"\n{'='*60}")
    print(f"Testing Cartopy Supersample: Terrain + Hydro Overlay")
    print('='*60)

    try:
        # Create figure with 3 subplots
        fig = plt.figure(figsize=(18, 6))

        configs = [
            {
                'name': 'no_supersample',
                'desc': 'No Supersample',
                'supersample': 0
            },
            {
                'name': 'supersample_1',
                'desc': 'Supersample=1',
                'supersample': 1
            },
            {
                'name': 'supersample_2',
                'desc': 'Supersample=2',
                'supersample': 2
            }
        ]

        for idx, config in enumerate(configs, 1):
            try:
                print(f"  Testing {config['name']:20s} - {config['desc']}")

                # Create subplot
                ax = fig.add_subplot(1, 3, idx, projection=ccrs.PlateCarree())
                ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())

                # Add base terrain layer
                terrain_server = RasterTileServer('Esri.Terrain')
                if config['supersample'] > 0:
                    terrain_tiles = terrain_server.get_cartopy_source_with_supersample(
                        supersample=config['supersample']
                    )
                else:
                    terrain_tiles = terrain_server.get_cartopy_source()

                ax.add_image(terrain_tiles, TEST_ZOOM, alpha=1.0)

                # Add hydro overlay (with transparent black areas)
                hydro_server = RasterTileServer('Esri.Hydro')
                if config['supersample'] > 0:
                    hydro_tiles = hydro_server.get_cartopy_source_with_supersample(
                        supersample=config['supersample']
                    )
                else:
                    hydro_tiles = hydro_server.get_cartopy_source()

                ax.add_image(hydro_tiles, TEST_ZOOM, alpha=0.8)

                # Add gridlines
                gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
                gl.top_labels = False
                gl.right_labels = False

                # Set title
                ax.set_title(f"Terrain + Hydro\n{config['desc']}",
                           fontsize=12, pad=10)

                print(f"    ✓ Success!")

            except Exception as e:
                print(f"    ✗ Failed: {e}")

        # Save the comparison figure
        plt.tight_layout()
        filename = "terrain_hydro_overlay_supersample_comparison.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Saved overlay comparison: {filename}")
        return True

    except Exception as e:
        print(f"  ✗ Overlay test failed: {e}")
        plt.close('all')
        return False


def test_cartopy_supersample_resample_methods():
    """
    Test different resampling methods with supersample.
    """
    print(f"\n{'='*60}")
    print(f"Testing Cartopy Supersample: Resampling Methods")
    print('='*60)

    try:
        provider_name = 'Esri.Terrain'
        server = RasterTileServer(provider_name)

        # Create figure with 4 subplots
        fig = plt.figure(figsize=(16, 12))

        # Test different resampling methods
        methods = [
            ('lanczos', 'Lanczos (best quality)'),
            ('bicubic', 'Bicubic (good quality)'),
            ('bilinear', 'Bilinear (faster)'),
            ('nearest', 'Nearest (fastest)')
        ]

        for idx, (method, desc) in enumerate(methods, 1):
            try:
                print(f"  Testing {method:15s} - {desc}")

                # Create subplot
                ax = fig.add_subplot(2, 2, idx, projection=ccrs.PlateCarree())
                ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())

                # Get tile source with supersample and specific resample method
                tile_source = server.get_cartopy_source_with_supersample(
                    supersample=1,
                    resample_method=method
                )

                # Add image to map
                ax.add_image(tile_source, TEST_ZOOM, alpha=0.9)

                # Add gridlines
                gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5)
                gl.top_labels = False
                gl.right_labels = False

                # Set title
                ax.set_title(f"Supersample=1\n{desc}", fontsize=12, pad=10)

                print(f"    ✓ Success!")

            except Exception as e:
                print(f"    ✗ Failed: {e}")

        # Save the comparison figure
        plt.tight_layout()
        filename = "resample_methods_comparison.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Saved resample methods comparison: {filename}")
        return True

    except Exception as e:
        print(f"  ✗ Resample methods test failed: {e}")
        plt.close('all')
        return False


def run_all_tests():
    """Run all Cartopy supersample tests."""
    print("="*60)
    print("CARTOPY SUPERSAMPLE TEST SUITE")
    print("="*60)
    print(f"Test extent: {TEST_EXTENT}")
    print(f"Test zoom: {TEST_ZOOM}")
    print(f"Output directory: {OUTPUT_DIR}/")

    # Get API key from environment if available
    stadia_api_key = os.environ.get('STADIA_API_KEY')

    results = []

    # Test 1: Single provider comparison (multiple supersample levels)
    print("\n" + "="*60)
    print("TEST 1: Single Provider Supersample Comparison")
    print("="*60)

    providers_to_test = [
        ('Esri.Terrain', None),
        ('Esri.Hydro', None),
        ('Esri.WorldImagery', None),
    ]

    for provider_name, api_key in providers_to_test:
        result = test_cartopy_supersample_single_provider(provider_name, api_key)
        results.append((f"{provider_name} (single)", result))

    # Test 2: Overlay test (Terrain + Hydro)
    print("\n" + "="*60)
    print("TEST 2: Overlay Test (Terrain + Hydro)")
    print("="*60)
    result = test_cartopy_supersample_overlay()
    results.append(("Terrain + Hydro Overlay", result))

    # Test 3: Resampling methods comparison
    print("\n" + "="*60)
    print("TEST 3: Resampling Methods Comparison")
    print("="*60)
    result = test_cartopy_supersample_resample_methods()
    results.append(("Resampling Methods", result))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8s} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")
    print("="*60)

    # List output files
    output_files = sorted([f for f in os.listdir(OUTPUT_DIR)
                          if f.endswith('.png') and 'cartopy' in f or 'overlay' in f or 'resample' in f])
    if output_files:
        print(f"\nGenerated {len(output_files)} test images:")
        for filename in output_files:
            print(f"  - {filename}")

    print("\n" + "="*60)
    print("USAGE GUIDE")
    print("="*60)
    print("""
To use supersample with Cartopy in your code:

# Standard method (no supersample):
server = RasterTileServer('Esri.Terrain')
tiles = server.get_cartopy_source()
ax.add_image(tiles, zoom_level, alpha=0.9)

# With supersample for better quality:
server = RasterTileServer('Esri.Terrain')
tiles = server.get_cartopy_source_with_supersample(supersample=1)
ax.add_image(tiles, zoom_level, alpha=0.9)

# With custom resampling method:
tiles = server.get_cartopy_source_with_supersample(
    supersample=1,
    resample_method='lanczos'
)
ax.add_image(tiles, zoom_level, alpha=0.9)

Supersample levels:
- 0: No supersampling (same as standard)
- 1: 2x resolution (recommended, good balance)
- 2: 4x resolution (best quality, slower)
""")

    return passed == total


if __name__ == '__main__':
    success = run_all_tests()

    print("\n" + "="*60)
    if success:
        print("✓ All Cartopy supersample tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)
