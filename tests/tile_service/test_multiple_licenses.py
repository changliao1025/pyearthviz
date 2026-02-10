"""
Test that multiple tile service licenses are properly displayed.

This test verifies that when multiple tile services are used together,
all license attributions are collected and displayed (not just the last one).
"""

import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyearthviz.map.raster_map_servers import RasterTileServer


def test_multiple_license_collection():
    """Test that we can collect licenses from multiple tile services."""

    # Simulate what happens in the vector map files
    providers = ['Esri.Terrain', 'Esri.WorldImagery', 'OSM.Standard']

    license_info_list = []

    for provider in providers:
        if provider == 'OSM':
            license_info_list.append("© OpenStreetMap contributors")
        else:
            tile_service = RasterTileServer(provider)
            license_info_list.append(tile_service.get_license_info())

    # Combine all licenses
    combined_license = " | ".join(license_info_list)

    print("\nCollected licenses:")
    for i, lic in enumerate(license_info_list, 1):
        print(f"  {i}. {lic}")

    print(f"\nCombined license info:\n  {combined_license}")

    # Verify all licenses are present
    assert len(license_info_list) == 3, "Should have collected 3 licenses"
    assert "Esri" in combined_license, "Should contain Esri attribution"
    assert "OpenStreetMap" in combined_license, "Should contain OSM attribution"
    assert " | " in combined_license, "Should be separated by pipes"

    print("\n✓ Test passed: All licenses are properly collected and combined!")


def test_single_license():
    """Test that single license still works correctly."""

    providers = ['Esri.Terrain']

    license_info_list = []

    for provider in providers:
        tile_service = RasterTileServer(provider)
        license_info_list.append(tile_service.get_license_info())

    combined_license = " | ".join(license_info_list)

    print(f"\nSingle license: {combined_license}")

    assert len(license_info_list) == 1, "Should have collected 1 license"
    assert " | " not in combined_license, "Single license should not have separator"

    print("✓ Test passed: Single license works correctly!")


if __name__ == "__main__":
    print("Testing multiple tile service license collection...")
    print("=" * 60)

    test_multiple_license_collection()
    print()
    test_single_license()

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
