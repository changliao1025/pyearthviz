"""
Example usage of the RasterTileServer class for accessing map tile servers.

This script demonstrates the new unified API for working with tile servers.
"""

import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from pyearthviz.map.raster_map_servers import RasterTileServer


def example_basic_usage():
    """Basic RasterTileServer usage example."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Create a tile server instance
    server = RasterTileServer('Esri.Terrain')
    print(f"Created: {server}")
    print(f"Tile size: {server.tile_size} pixels")
    print(f"URL template: {server.get_url_template()}")
    print()


def example_list_providers():
    """List all available tile server providers."""
    print("=" * 60)
    print("Example 2: List Available Providers")
    print("=" * 60)

    providers = RasterTileServer.get_available_providers()
    print(f"Available providers ({len(providers)} total):")
    for provider in providers:
        info = RasterTileServer.get_provider_info(provider)
        api_key_required = "Yes" if info['requires_api_key'] else "No"
        print(f"  - {provider:25s} | Tile: {info['tile_size']}x{info['tile_size']} | "
              f"API Key: {api_key_required:3s} | {info['description']}")
    print()


def example_fetch_single_tile():
    """Fetch a single tile."""
    print("=" * 60)
    print("Example 3: Fetch Single Tile")
    print("=" * 60)

    server = RasterTileServer('Esri.Terrain')

    # Fetch a tile for San Francisco area
    # Zoom 10, tile coordinates for SF
    try:
        tile = server.fetch_tile(z=10, x=163, y=395)
        print(f"Fetched tile: {tile.size} pixels, mode: {tile.mode}")

        # Save the tile
        output_file = '/tmp/example_tile.png'
        tile.save(output_file)
        print(f"Saved tile to: {output_file}")
    except Exception as e:
        print(f"Error fetching tile: {e}")
    print()


def example_fetch_extent():
    """Fetch tiles for an extent."""
    print("=" * 60)
    print("Example 4: Fetch Tiles for Extent")
    print("=" * 60)

    server = RasterTileServer('Esri.WorldImagery')

    # San Francisco area extent [minx, maxx, miny, maxy]
    extent = [-122.5, -122.3, 37.7, 37.8]
    zoom_level = 12

    try:
        image_array = server.fetch_tiles_for_extent(extent, zoom_level)
        print(f"Fetched image array: {image_array.shape}")
        print(f"Data type: {image_array.dtype}")

        # Display using matplotlib
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(image_array)
        ax.set_title(f'San Francisco Area\n{server.provider} - Zoom {zoom_level}')
        ax.axis('off')

        output_file = '/tmp/example_extent.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved map to: {output_file}")
        plt.close()
    except Exception as e:
        print(f"Error fetching extent: {e}")
    print()


def example_cartopy_integration():
    """Use RasterTileServer with Cartopy."""
    print("=" * 60)
    print("Example 5: Cartopy Integration")
    print("=" * 60)

    # Create figure with map projection
    fig = plt.figure(figsize=(12, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Set extent for San Francisco Bay Area
    ax.set_extent([-122.6, -122.2, 37.6, 37.9], crs=ccrs.PlateCarree())

    # Add tile server as background
    server = RasterTileServer('Esri.Terrain')
    try:
        ax.add_image(server.get_cartopy_source(), 11)

        # Add some features
        ax.coastlines(resolution='10m', color='red', linewidth=2)
        ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)

        plt.title(f'San Francisco Bay Area\nUsing {server.provider}', fontsize=14)

        output_file = '/tmp/example_cartopy.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved Cartopy map to: {output_file}")
        plt.close()
    except Exception as e:
        print(f"Error with Cartopy: {e}")
    print()


def example_with_api_key():
    """Use a provider that requires an API key (Stadia)."""
    print("=" * 60)
    print("Example 6: Provider with API Key (Stadia)")
    print("=" * 60)

    # Check if API key is available
    api_key = os.environ.get('STADIA_API_KEY')

    if api_key:
        server = RasterTileServer('Stadia.StamenTerrain', api_key=api_key)
        print(f"Created: {server}")
        print("API key loaded from environment variable")

        # Fetch a single tile
        try:
            tile = server.fetch_tile(z=10, x=163, y=395)
            print(f"Fetched tile: {tile.size} pixels")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("STADIA_API_KEY environment variable not set")
        print("You can still create the server, but tile fetching will fail:")
        server = RasterTileServer('Stadia.StamenTerrain')
        print(f"Created: {server}")
    print()


def example_coordinate_conversions():
    """Use static utility methods for coordinate conversions."""
    print("=" * 60)
    print("Example 7: Coordinate Conversions")
    print("=" * 60)

    # Convert lon/lat to tile coordinates
    lon, lat = -122.4, 37.8  # San Francisco
    zoom = 10

    x, y = RasterTileServer.lonlat_to_tile(lon, lat, zoom)
    print(f"Lon/Lat: ({lon}, {lat})")
    print(f"Tile indices at zoom {zoom}: x={x}, y={y}")

    # Convert extent to tile range
    extent = [-122.5, -122.3, 37.7, 37.8]
    x_min, y_min, x_max, y_max = RasterTileServer.extent_to_tile_indices(extent, zoom)
    print(f"\nExtent: {extent}")
    print(f"Tile range at zoom {zoom}:")
    print(f"  X: {x_min} to {x_max} ({x_max - x_min + 1} tiles)")
    print(f"  Y: {y_min} to {y_max} ({y_max - y_min + 1} tiles)")
    print(f"  Total tiles needed: {(x_max - x_min + 1) * (y_max - y_min + 1)}")
    print()


def example_compare_providers():
    """Compare different providers for the same area."""
    print("=" * 60)
    print("Example 8: Compare Different Providers")
    print("=" * 60)

    extent = [-122.5, -122.3, 37.7, 37.8]
    zoom_level = 11

    providers_to_compare = ['Esri.Terrain', 'Esri.Relief', 'Esri.WorldImagery']

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for idx, provider_name in enumerate(providers_to_compare):
        try:
            server = RasterTileServer(provider_name)
            image_array = server.fetch_tiles_for_extent(extent, zoom_level)

            axes[idx].imshow(image_array)
            axes[idx].set_title(provider_name)
            axes[idx].axis('off')
            print(f"Fetched {provider_name}: {image_array.shape}")
        except Exception as e:
            print(f"Error with {provider_name}: {e}")
            axes[idx].text(0.5, 0.5, f'Error:\n{provider_name}',
                          ha='center', va='center', transform=axes[idx].transAxes)
            axes[idx].axis('off')

    plt.suptitle('Comparison of Different Tile Providers\nSan Francisco Bay Area',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_file = '/tmp/example_provider_comparison.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved comparison to: {output_file}")
    plt.close()
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("RasterTileServer Usage Examples")
    print("=" * 60 + "\n")

    example_basic_usage()
    example_list_providers()
    example_fetch_single_tile()
    example_fetch_extent()
    example_cartopy_integration()
    example_with_api_key()
    example_coordinate_conversions()
    example_compare_providers()

    print("=" * 60)
    print("All examples completed!")
    print("Check /tmp/ directory for generated images")
    print("=" * 60)


if __name__ == '__main__':
    main()
