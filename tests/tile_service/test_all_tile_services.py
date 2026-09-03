"""
Comprehensive test script for all tile services with quality comparisons.
This script tests each provider with different quality settings and saves PNG outputs.
"""

import os
import numpy as np
from PIL import Image
from pyearthviz.map import RasterTileServer

# Create output directory using relative path to ensure it works in different environments

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Test extent (San Francisco area - small for faster testing)
TEST_EXTENT = [97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]



TEST_ZOOM = None

def test_provider_baseline(provider_name, api_key=None):
    """Fetch a single provider using the baseline configuration only."""
    print(f"\n{'='*60}")
    print(f"Testing baseline for: {provider_name}")
    print('='*60)

    try:
        server = RasterTileServer(provider_name, api_key=api_key)
        if not getattr(server, 'is_accessible', True):
            print(f"  ✗ Provider '{provider_name}' is not accessible or requires an API key.")
            return False

        img_array = server.fetch_tiles_for_extent(
            TEST_EXTENT,
            TEST_ZOOM,
            supersample=0,
            resample=False,
        )

        img = Image.fromarray(img_array)
        safe_provider = provider_name.replace('.', '_').lower()
        filename = f"{safe_provider}_baseline.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        img.save(output_path)

        print(f"    ✓ Success! Shape: {img_array.shape}, saved: {filename}")
        return True

    except Exception as e:
        print(f"  ✗ Provider initialization failed: {e}")
        return False


def test_all_providers():
    """Test all available tile service providers using baseline quality only."""
    print("="*60)
    print("BASELINE TILE SERVICE TEST")
    print("="*60)
    print(f"Test extent: {TEST_EXTENT}")
    print(f"Test zoom: {TEST_ZOOM}")
    print(f"Output directory: {OUTPUT_DIR}/")

    providers = RasterTileServer.get_available_providers()

    results = []
    for provider_name in providers:
        result = test_provider_baseline(provider_name, None)
        results.append((provider_name, result))

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for provider_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8s} - {provider_name}")

    print(f"\nResults: {passed}/{total} providers tested successfully")
    print("="*60)
    return passed == total

def create_comparison_grid():
    """Create a visual comparison grid of different quality settings."""
    print("\n" + "="*60)
    print("Creating comparison grids...")
    print("="*60)

    try:
        from PIL import ImageDraw, ImageFont

        # Find one provider that has all quality levels
        output_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.png')]
        if not output_files:
            print("No output files found. Run tests first.")
            return False

        # Group files by provider
        providers_dict = {}
        for filename in output_files:
            parts = filename.replace('.png', '').split('_')
            if len(parts) >= 2:
                provider = '_'.join(parts[:-1])
                quality = parts[-1]
                if provider not in providers_dict:
                    providers_dict[provider] = {}
                providers_dict[provider][quality] = filename

        # Create grid for each provider that has multiple quality levels
        for provider, files_dict in providers_dict.items():
            if len(files_dict) < 2:
                continue

            print(f"  Creating grid for {provider}...")

            # Load images
            qualities = ['baseline', 'blend_only', 'resample_only', 'balanced', 'high_quality']
            images = []
            labels = []

            for quality in qualities:
                if quality in files_dict:
                    img_path = os.path.join(OUTPUT_DIR, files_dict[quality])
                    img = Image.open(img_path)
                    # Resize to smaller for grid
                    img = img.resize((400, 400), Image.LANCZOS)
                    images.append(img)
                    labels.append(quality.replace('_', ' ').title())

            if len(images) < 2:
                continue

            # Create grid (2 columns)
            cols = 2
            rows = (len(images) + 1) // 2
            grid_width = 400 * cols
            grid_height = 450 * rows  # Extra space for labels

            grid = Image.new('RGB', (grid_width, grid_height), 'white')
            draw = ImageDraw.Draw(grid)

            for idx, (img, label) in enumerate(zip(images, labels)):
                row = idx // cols
                col = idx % cols
                x = col * 400
                y = row * 450

                # Paste image
                grid.paste(img, (x, y))

                # Draw label
                text_y = y + 410
                draw.text((x + 200, text_y), label, fill='black', anchor='mm')

            # Save grid
            grid_filename = f"{provider}_comparison_grid.png"
            grid_path = os.path.join(OUTPUT_DIR, grid_filename)
            grid.save(grid_path)
            print(f"    ✓ Saved: {grid_filename}")

        return True

    except ImportError:
        print("  Skipping grid creation (PIL ImageDraw not available)")
        return False
    except Exception as e:
        print(f"  ✗ Grid creation failed: {e}")
        return False

if __name__ == '__main__':
    success = test_all_providers()

    # Try to create comparison grids
    success = create_comparison_grid()

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)
