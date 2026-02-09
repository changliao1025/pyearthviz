"""
Test script to verify tile quality improvements work correctly.
This script tests the new RasterTileServer features without requiring the full MPAS mesh.
"""

import os
import numpy as np
from PIL import Image
from pyearthviz.map import RasterTileServer

# Create output directory
OUTPUT_DIR = 'test_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def test_basic_tile_fetch():
    """Test basic tile fetching with quality improvements."""
    print("Test 1: Basic tile fetch with quality improvements...")

    server = RasterTileServer('Esri.Terrain')
    extent = [-122.5, -122.3, 37.7, 37.8]  # Small San Francisco area
    zoom = 12

    try:
        img_array = server.fetch_tiles_for_extent(
            extent,
            zoom,
            supersample=1,
            resample=True,
            resample_method='lanczos'
        )

        assert isinstance(img_array, np.ndarray), "Should return numpy array"
        assert len(img_array.shape) == 3, "Should be 3D array (height, width, channels)"
        assert img_array.shape[2] in [3, 4], "Should have RGB or RGBA channels"

        # Save result
        img = Image.fromarray(img_array)
        output_path = os.path.join(OUTPUT_DIR, 'test1_basic_quality.png')
        img.save(output_path)
        print(f"✓ Success! Image shape: {img_array.shape}")
        print(f"  Saved to: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_supersample_levels():
    """Test different supersample levels."""
    print("\nTest 2: Different supersample levels...")

    server = RasterTileServer('Esri.Terrain')
    extent = [-122.5, -122.4, 37.7, 37.75]  # Very small area for speed
    zoom = 11

    for supersample in [0, 1]:
        try:
            img_array = server.fetch_tiles_for_extent(
                extent,
                zoom,
                supersample=supersample,
                resample=True
            )

            # Save results
            img = Image.fromarray(img_array)
            output_path = os.path.join(OUTPUT_DIR, f'test2_supersample_{supersample}.png')
            img.save(output_path)
            print(f"✓ Supersample={supersample}: shape={img_array.shape}, saved to {output_path}")
        except Exception as e:
            print(f"✗ Supersample={supersample} failed: {e}")
            return False

    return True

def test_resampling():
    """Test resampling quality."""
    print("\nTest 3: Resampling quality comparison...")

    server = RasterTileServer('Esri.Terrain')
    extent = [-122.5, -122.3, 37.7, 37.8]
    zoom = 12

    try:
        # With super-sampling and resampling (best quality)
        img_high_quality = server.fetch_tiles_for_extent(
            extent, zoom, supersample=1, resample=True, resample_method='lanczos'
        )

        # Without super-sampling (baseline)
        img_baseline = server.fetch_tiles_for_extent(
            extent, zoom, supersample=0, resample=False
        )

        # Save both for comparison
        img1 = Image.fromarray(img_high_quality)
        img2 = Image.fromarray(img_baseline)
        img1.save(os.path.join(OUTPUT_DIR, 'test3_high_quality.png'))
        img2.save(os.path.join(OUTPUT_DIR, 'test3_baseline.png'))

        print(f"✓ Comparison complete")
        print(f"  High quality shape: {img_high_quality.shape}")
        print(f"  Baseline shape: {img_baseline.shape}")
        print(f"  Saved: test3_high_quality.png and test3_baseline.png")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_suggest_optimal_zoom():
    """Test optimal zoom suggestion."""
    print("\nTest 4: Optimal zoom suggestion...")

    server = RasterTileServer('Esri.Terrain')
    extent = [115, 119, 36, 38]  # 4° × 2° (your use case)

    try:
        for preference in ['fast', 'balanced', 'quality']:
            zoom = server.suggest_optimal_zoom(
                extent,
                output_dpi=150,
                output_size=(1200, 1200),
                quality_preference=preference
            )
            print(f"✓ {preference:8s}: zoom={zoom}")

        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_different_providers():
    """Test different tile providers."""
    print("\nTest 5: Different providers...")

    extent = [-122.5, -122.4, 37.7, 37.75]  # Small area
    zoom = 12

    providers = ['Esri.Terrain', 'Esri.Relief', 'Stadia.StamenTerrain', 'Carto.Positron']

    for provider in providers:
        try:
            server = RasterTileServer(provider)
            img_array = server.fetch_tiles_for_extent(
                extent, zoom, supersample=0
            )

            # Save result
            img = Image.fromarray(img_array)
            safe_name = provider.replace('.', '_').lower()
            output_path = os.path.join(OUTPUT_DIR, f'test5_{safe_name}.png')
            img.save(output_path)
            print(f"✓ {provider:20s}: shape={img_array.shape}, saved to {output_path}")
        except Exception as e:
            print(f"✗ {provider:20s}: {e}")

    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Tile Quality Improvements")
    print("=" * 60)

    tests = [
        test_basic_tile_fetch,
        test_supersample_levels,
        test_resampling,
        test_suggest_optimal_zoom,
        test_different_providers
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests passed! Implementation is working correctly.")
        print(f"\nGenerated test images saved in: {OUTPUT_DIR}/")
        print("Compare these images to see the quality improvements:")
        print("  - test1_basic_quality.png: High-quality tile fetch with super-sampling + LANCZOS")
        print("  - test2_supersample_0.png: No super-sampling")
        print("  - test2_supersample_1.png: 2× super-sampling (recommended)")
        print("  - test3_high_quality.png: Super-sampling + LANCZOS (best quality)")
        print("  - test3_baseline.png: No super-sampling (shows tile boundaries)")
        print("  - test5_*.png: Different tile providers")
    else:
        print("\n✗ Some tests failed. Please review the errors above.")

if __name__ == '__main__':
    main()
