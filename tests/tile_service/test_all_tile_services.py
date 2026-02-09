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
TEST_EXTENT = [-122.5, -122.3, 37.7, 37.8]
dLongitude_center_in = 117
dLatitude_center_in = 39
buffer = 0.8

TEST_EXTENT = [dLongitude_center_in - buffer, dLongitude_center_in + buffer, dLatitude_center_in - buffer, dLatitude_center_in + buffer]
TEST_ZOOM = 10

def test_provider_quality_comparison(provider_name, api_key=None):
    """
    Test a single provider with different quality settings.

    Args:
        provider_name: Name of the tile provider
        api_key: Optional API key for providers that require it
    """
    print(f"\n{'='*60}")
    print(f"Testing: {provider_name}")
    print('='*60)

    try:
        server = RasterTileServer(provider_name, api_key=api_key)

        # Test configurations
        # Note: Edge blending removed - super-sampling + LANCZOS naturally eliminates boundaries
        configs = [
            {
                'name': 'baseline',
                'desc': 'No improvements (shows tile boundaries)',
                'params': {
                    'supersample': 0,
                    'resample': False
                }
            },
            {
                'name': 'resample_only',
                'desc': 'LANCZOS resampling only',
                'params': {
                    'supersample': 0,
                    'resample': True,
                    'resample_method': 'lanczos'
                }
            },
            {
                'name': 'balanced',
                'desc': 'Balanced (supersample=1 + resample)',
                'params': {
                    'supersample': 1,
                    'resample': True,
                    'resample_method': 'lanczos'
                }
            },
            {
                'name': 'high_quality',
                'desc': 'High quality (supersample=2 + LANCZOS)',
                'params': {
                    'supersample': 2,
                    'resample': True,
                    'resample_method': 'lanczos'
                }
            }
        ]

        for config in configs:
            try:
                print(f"  Testing {config['name']:15s} - {config['desc']}")

                img_array = server.fetch_tiles_for_extent(
                    TEST_EXTENT,
                    TEST_ZOOM,
                    **config['params']
                )
                print("dimension of the Stamen Terrain image: ", img_array.shape)

                # Save result
                img = Image.fromarray(img_array)
                safe_provider = provider_name.replace('.', '_').lower()
                filename = f"{safe_provider}_{config['name']}.png"
                output_path = os.path.join(OUTPUT_DIR, filename)
                img.save(output_path)

                print(f"    ✓ Success! Shape: {img_array.shape}, saved: {filename}")

            except Exception as e:
                print(f"    ✗ Failed: {e}")

        return True

    except Exception as e:
        print(f"  ✗ Provider initialization failed: {e}")
        return False

def test_all_providers():
    """Test all available tile service providers."""
    print("="*60)
    print("COMPREHENSIVE TILE SERVICE QUALITY TEST")
    print("="*60)
    print(f"Test extent: {TEST_EXTENT}")
    print(f"Test zoom: {TEST_ZOOM}")
    print(f"Output directory: {OUTPUT_DIR}/")

    # Get API key from environment if available
    stadia_api_key = os.environ.get('STADIA_API_KEY')
    if stadia_api_key:
        print(f"Found STADIA_API_KEY in environment")
    else:
        print("No STADIA_API_KEY found - Stadia tests may fail")

    # List of all providers to test
    providers = [
        # Esri providers (no API key needed)
        #('Esri.Terrain', None),
        #('Esri.Relief', None),
        #('Esri.Hydro', None),
        #('Esri.WorldImagery', None),
        #('Esri.WorldTopo', None),
        #('Esri.NatGeo', None),
        #('Esri.WorldStreet', None),
        #('Esri.GrayCanvasBase', None),
        #('Esri.GrayCanvasLabels', None),
        #('Esri.WorldOceanBase', None),

        # Stadia providers (require API key)
        ('Stadia.StamenTerrain', stadia_api_key),
        #('Stadia.AlidadeSmooth', stadia_api_key),

        # Carto providers (no API key needed)
        #('Carto.Positron', None),
        #('Carto.DarkMatter', None),
    ]

    results = []
    for provider_name, api_key in providers:
        result = test_provider_quality_comparison(provider_name, api_key)
        results.append((provider_name, result))

    # Summary
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

    # List output files
    output_files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.png')])
    if output_files:
        print(f"\nGenerated {len(output_files)} test images in {OUTPUT_DIR}/:")

        # Group by provider
        providers_dict = {}
        for filename in output_files:
            provider = '_'.join(filename.split('_')[:-1])
            quality = filename.split('_')[-1].replace('.png', '')
            if provider not in providers_dict:
                providers_dict[provider] = []
            providers_dict[provider].append(quality)

        for provider in sorted(providers_dict.keys()):
            print(f"\n  {provider}:")
            for quality in sorted(providers_dict[provider]):
                print(f"    - {quality}")

    print("\n" + "="*60)
    print("COMPARISON GUIDE")
    print("="*60)
    print("""
Compare these quality levels for each provider:

1. baseline       - Original quality (may show tile boundaries)
2. blend_only     - Removes tile seams
3. resample_only  - Smooths image but may keep some boundaries
4. balanced       - Good balance of quality and speed
5. high_quality   - Best quality (2× super-sampling, slower)

Look for:
- Visible tile boundaries in 'baseline'
- Smooth transitions in 'blend_only' and higher
- Overall image smoothness in 'resample_only' and higher
- Best overall quality in 'high_quality'
""")

    if not stadia_api_key:
        print("\nNOTE: Stadia tests failed because no API key was provided.")
        print("To test Stadia providers, set environment variable:")
        print("  export STADIA_API_KEY='your_api_key'")
        print("  or pass it in the script")

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
    create_comparison_grid()

    print("\n" + "="*60)
    if success:
        print("✓ All tests completed successfully!")
    else:
        print("✗ Some tests failed. Check output above.")
    print("="*60)
