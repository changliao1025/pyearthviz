# RasterTileServer - Unified Map Tile Server Interface

## Overview

The `RasterTileServer` class provides a clean, unified interface for accessing various map tile servers. Instead of managing multiple functions and classes for different providers, you now have **one class to rule them all**.

## Quick Start

```python
from pyearthviz.map import RasterTileServer

# Create a tile server
server = RasterTileServer('Esri.Terrain')

# Fetch tiles for an extent
extent = [-122.5, -122.3, 37.7, 37.8]  # [minx, maxx, miny, maxy]
image = server.fetch_tiles_for_extent(extent, zoom_level=12)

# Use with Cartopy
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
ax.add_image(server.get_cartopy_source(), 10)
plt.show()
```

## Available Providers

List all available providers:

```python
providers = RasterTileServer.get_available_providers()
print(providers)
```

### Current Providers

| Provider | Description | Tile Size | API Key Required |
|----------|-------------|-----------|------------------|
| `Stadia.StamenTerrain` | Stadia Maps terrain (formerly Stamen) | 512×512 | Yes |
| `Stadia.AlidadeSmooth` | Stadia Maps smooth basemap | 512×512 | Yes |
| `Esri.Terrain` | Esri World Terrain Base | 256×256 | No |
| `Esri.Relief` | Esri World Shaded Relief | 256×256 | No |
| `Esri.Hydro` | Esri Hydro Reference Overlay | 256×256 | No |
| `Esri.WorldImagery` | Esri World Imagery (satellite) | 256×256 | No |
| `Carto.Positron` | Carto Positron (light basemap) | 512×512 | No |
| `Carto.DarkMatter` | Carto Dark Matter (dark basemap) | 512×512 | No |

## Core Methods

### `fetch_tile(z, x, y)`

Fetch a single tile at specific coordinates:

```python
server = RasterTileServer('Esri.WorldImagery')
tile = server.fetch_tile(z=10, x=163, y=395)  # Returns PIL Image
```

### `fetch_tiles_for_extent(extent, zoom_level)`

Fetch and combine all tiles needed for an extent:

```python
server = RasterTileServer('Esri.Terrain')
extent = [-122.5, -122.3, 37.7, 37.8]  # [minx, maxx, miny, maxy] in degrees
image_array = server.fetch_tiles_for_extent(extent, zoom_level=12)
# Returns NumPy array
```

### `get_cartopy_source()`

Get a Cartopy-compatible tile source:

```python
server = RasterTileServer('Esri.Relief')
ax.add_image(server.get_cartopy_source(), zoom_level=10)
```

### `calculate_zoom_level(scale_denominator, projection, dpi=96)`

Calculate appropriate zoom level for a map:

```python
server = RasterTileServer('Esri.Terrain')
zoom = server.calculate_zoom_level(
    scale_denominator=50000,
    projection=projection_wkt,
    dpi=300
)
```

### `calculate_scale_denominator(extent, image_size, dpi=96)`

Calculate scale denominator for an extent and image size:

```python
server = RasterTileServer('Esri.Terrain')
extent = [-122.5, -122.3, 37.7, 37.8]
scale = server.calculate_scale_denominator(extent, (800, 600), dpi=96)
```

## Static Utility Methods

These work without creating a server instance:

### `lonlat_to_tile(lon, lat, zoom)`

Convert longitude/latitude to tile coordinates:

```python
x, y = RasterTileServer.lonlat_to_tile(-122.4, 37.8, zoom=10)
```

### `extent_to_tile_indices(extent, zoom)`

Convert extent to tile index range:

```python
extent = [-122.5, -122.3, 37.7, 37.8]
x_min, y_min, x_max, y_max = RasterTileServer.extent_to_tile_indices(extent, zoom=10)
```

### `combine_tiles(tiles, tile_size)`

Combine a 2D array of tiles into one image:

```python
tiles = [[tile1, tile2], [tile3, tile4]]
combined = RasterTileServer.combine_tiles(tiles, tile_size=256)
```

## Class Methods

### `get_available_providers()`

Get list of all available providers:

```python
providers = RasterTileServer.get_available_providers()
# Returns: ['Stadia.StamenTerrain', 'Esri.Terrain', ...]
```

### `get_provider_info(provider=None)`

Get information about a provider:

```python
# Single provider
info = RasterTileServer.get_provider_info('Esri.Terrain')
print(info['description'])  # 'Esri World Terrain Base'
print(info['tile_size'])    # 256

# All providers
all_info = RasterTileServer.get_provider_info()
```

## Using Providers with API Keys

Some providers (like Stadia Maps) require an API key:

```python
# Option 1: Pass API key directly
server = RasterTileServer('Stadia.StamenTerrain', api_key='your_key_here')

# Option 2: Use environment variable
import os
os.environ['STADIA_API_KEY'] = 'your_key_here'
server = RasterTileServer('Stadia.StamenTerrain')  # Automatically uses env var
```

## Complete Example

```python
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from pyearthviz.map import RasterTileServer

# List available providers
print("Available providers:")
for provider in RasterTileServer.get_available_providers():
    info = RasterTileServer.get_provider_info(provider)
    print(f"  {provider}: {info['description']}")

# Create a map with Esri terrain tiles
fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# Set extent for San Francisco Bay Area
extent = [-122.6, -122.2, 37.6, 37.9]
ax.set_extent(extent, crs=ccrs.PlateCarree())

# Add tile server background
server = RasterTileServer('Esri.Terrain')
ax.add_image(server.get_cartopy_source(), 11)

# Add features
ax.coastlines(resolution='10m', color='red', linewidth=2)
ax.gridlines(draw_labels=True)

plt.title(f'San Francisco Bay Area\nUsing {server.provider}')
plt.savefig('map_output.png', dpi=150, bbox_inches='tight')
plt.show()
```

## Comparing Providers

```python
from pyearthviz.map import RasterTileServer
import matplotlib.pyplot as plt

extent = [-122.5, -122.3, 37.7, 37.8]
zoom = 11

providers = ['Esri.Terrain', 'Esri.Relief', 'Esri.WorldImagery']
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for idx, provider_name in enumerate(providers):
    server = RasterTileServer(provider_name)
    image = server.fetch_tiles_for_extent(extent, zoom)

    axes[idx].imshow(image)
    axes[idx].set_title(provider_name)
    axes[idx].axis('off')

plt.tight_layout()
plt.savefig('provider_comparison.png', dpi=150)
plt.show()
```

## Design Benefits

### For Users
- ✅ **Simple API**: One class, consistent methods
- ✅ **Easy discovery**: IDE autocomplete shows all options
- ✅ **Clear documentation**: Comprehensive docstrings
- ✅ **Type hints**: Better IDE support and error catching

### For Developers
- ✅ **Easy to extend**: Add new providers via configuration
- ✅ **No code duplication**: Common logic in base class
- ✅ **Clean structure**: Configuration-driven design
- ✅ **Maintainable**: Clear separation of concerns

## Migration from Old API

If you have existing code using the old function-based API, you'll need to update it to use the new `RasterTileServer` class. Here's a quick migration guide:

### Old API
```python
from pyearthviz.map.map_servers import (
    fetch_esri_terrain_tile,
    Esri_terrain_images,
    EsriTerrain
)

# Fetch single tile
tile = fetch_esri_terrain_tile(z, x, y)

# Fetch extent
image = Esri_terrain_images(extent, zoom)

# Cartopy
terrain = EsriTerrain()
ax.add_image(terrain, zoom)
```

### New API
```python
from pyearthviz.map import RasterTileServer

# Create server once, reuse for all operations
server = RasterTileServer('Esri.Terrain')

# Fetch single tile
tile = server.fetch_tile(z, x, y)

# Fetch extent
image = server.fetch_tiles_for_extent(extent, zoom)

# Cartopy
ax.add_image(server.get_cartopy_source(), zoom)
```

## Advanced Usage

### Custom Processing

You can subclass `RasterTileServer` for custom processing:

```python
from pyearthviz.map import RasterTileServer
import numpy as np

class CustomTileServer(RasterTileServer):
    def fetch_tiles_for_extent(self, extent, zoom_level):
        # Get base image
        image = super().fetch_tiles_for_extent(extent, zoom_level)

        # Apply custom processing
        image = self.apply_custom_filter(image)

        return image

    def apply_custom_filter(self, image):
        # Your custom processing here
        return image

server = CustomTileServer('Esri.Terrain')
```

### Adding New Providers

To add a new tile provider, you can modify the `_PROVIDERS` dictionary:

```python
# This would be done in the map_servers.py file
RasterTileServer._PROVIDERS['MyProvider.CustomLayer'] = {
    'url_template': 'https://my-tile-server.com/{z}/{x}/{y}.png',
    'tile_size': 256,
    'requires_api_key': False,
    'special_handling': None,
    'description': 'My custom tile provider'
}
```

## Examples

See [`examples/map_servers_usage.py`](../examples/map_servers_usage.py) for comprehensive examples including:

1. Basic usage
2. Listing providers
3. Fetching single tiles
4. Fetching extents
5. Cartopy integration
6. Using API keys
7. Coordinate conversions
8. Provider comparisons

## API Reference

For detailed API documentation, see the docstrings in the [`RasterTileServer`](../pyearthviz/map/map_servers.py:50) class.

## Contributing

To add new tile providers:

1. Add provider configuration to `_PROVIDERS` dictionary
2. Include URL template with placeholders
3. Specify tile size and API key requirements
4. Add special handling if needed (e.g., transparency)
5. Update documentation

## License

Same as PyEarthViz package license.
