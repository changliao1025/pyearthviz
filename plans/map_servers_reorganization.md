# Map Servers Module Reorganization Plan

## Current State Analysis

The [`map_servers.py`](../pyearthviz/map/map_servers.py:1) module currently contains:

### Components (Lines 1-425):
1. **MapServers class** (lines 35-88): Basic URL provider for different tile servers
2. **Cartopy tile sources** (lines 140-173): StadiaStamen, EsriRelief, EsriTerrain, EsriHydro
3. **Utility functions** (lines 90-138):
   - [`lonlat_to_tile()`](../pyearthviz/map/map_servers.py:90) - coordinate to tile conversion
   - [`extent_to_tile_indices()`](../pyearthviz/map/map_servers.py:105) - extent to tiles
   - [`combine_tiles()`](../pyearthviz/map/map_servers.py:114) - merge tiles into single image
4. **Tile fetching functions** (lines 175-253):
   - [`fetch_stadia_tile()`](../pyearthviz/map/map_servers.py:175)
   - [`fetch_esri_terrain_tile()`](../pyearthviz/map/map_servers.py:195)
   - [`fetch_esri_relif_tile()`](../pyearthviz/map/map_servers.py:213) [typo: should be "relief"]
   - [`fetch_esri_hydro_tile()`](../pyearthviz/map/map_servers.py:228)
5. **Image composition functions** (lines 255-346):
   - [`Stadia_terrain_images()`](../pyearthviz/map/map_servers.py:255)
   - [`Esri_terrain_images()`](../pyearthviz/map/map_servers.py:279)
   - [`Esri_relief_images()`](../pyearthviz/map/map_servers.py:302)
   - [`Esri_hydro_images()`](../pyearthviz/map/map_servers.py:324)
6. **Zoom calculation functions** (lines 348-425):
   - [`calculate_zoom_level()`](../pyearthviz/map/map_servers.py:348)
   - [`calculate_scale_denominator()`](../pyearthviz/map/map_servers.py:386)

### Issues with Current Design:
- **Scattered functionality**: Related operations split across multiple functions
- **Code duplication**: Image composition functions are nearly identical
- **Inconsistent naming**: Mix of snake_case with capital letters (e.g., `Stadia_terrain_images`)
- **Hard to extend**: Adding new providers requires creating multiple functions
- **No unified interface**: Users need to know different function names for each provider
- **API key management**: Handled inconsistently (environment variable, class parameter)

---

## Proposed Architecture

### Design Goals:
1. **Single entry point**: Users access all features through one class
2. **Provider-based**: Easy to add new tile providers
3. **Clean API**: Intuitive method names and consistent interface
4. **Backward compatible**: Maintain existing function signatures
5. **Type safety**: Add type hints for better IDE support

### New Class Structure:

```python
# Single unified RasterTileServer class
class RasterTileServer:
    """
    Unified interface for accessing map tile servers.

    All functionality accessed through a single class - users only need to
    specify the provider name when creating an instance.
    """

    # Instance attributes
    - provider: str              # e.g., 'Esri.Terrain', 'Stadia.StamenTerrain'
    - tile_size: int             # Automatically set based on provider
    - api_key: Optional[str]     # For providers that require it
    - _config: dict              # Internal provider configuration

    # Constructor
    + __init__(provider: str, api_key: Optional[str] = None, **kwargs)

    # Core Methods
    + fetch_tile(z: int, x: int, y: int) → PIL.Image
    + fetch_tiles_for_extent(extent: List[float], zoom_level: int) → PIL.Image
    + get_cartopy_source() → cimgt.GoogleTiles
    + get_url_template() → str

    # Calculation Methods
    + calculate_zoom_level(scale_denominator, projection, dpi=96) → int
    + calculate_scale_denominator(extent, image_size, dpi=96) → float

    # Static/Class Methods (utilities)
    @staticmethod
    + lonlat_to_tile(lon: float, lat: float, zoom: int) → Tuple[int, int]
    @staticmethod
    + extent_to_tile_indices(extent: List[float], zoom: int) → Tuple[int, int, int, int]
    @staticmethod
    + combine_tiles(tiles: List[List[PIL.Image]], tile_size: int) → PIL.Image

    @classmethod
    + get_available_providers() → List[str]

    # Internal provider registry (class-level)
    _PROVIDERS = {
        'Stadia.StamenTerrain': {
            'url_template': 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}@2x.png?api_key={api_key}',
            'tile_size': 512,
            'requires_api_key': True,
            'special_handling': None
        },
        'Esri.Terrain': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None
        },
        'Esri.Hydro': {
            'url_template': 'https://tiles.arcgis.com/tiles/P3ePLMYs2RVChkJx/arcgis/rest/services/Esri_Hydro_Reference_Overlay/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': 'make_black_transparent'
        },
        # ... more providers
    }
```

**Key Design Principle:** All provider-specific behavior is handled through configuration and internal methods, not through inheritance. Users only ever instantiate `RasterTileServer`.

### Usage Examples:

```python
# Simple usage - direct instantiation only
server = RasterTileServer('Stadia.StamenTerrain', api_key='your_key')
image = server.fetch_tiles_for_extent(extent=[minx, maxx, miny, maxy], zoom_level=10)

# Different provider - same class
server = RasterTileServer('Esri.Terrain')
image = server.fetch_tiles_for_extent(extent, zoom_level=12)

# Use with cartopy
server = RasterTileServer('Esri.WorldImagery')
ax.add_image(server.get_cartopy_source(), zoom_level)

# List available providers
providers = RasterTileServer.get_available_providers()
print(providers)  # ['Stadia.StamenTerrain', 'Esri.Terrain', 'Esri.Relief', ...]

# Calculate appropriate zoom level
zoom = server.calculate_zoom_level(
    scale_denominator=50000,
    projection=projection_wkt,
    dpi=300
)
```

---

## Implementation Plan

### Phase 1: Core Infrastructure
1. **Create unified `RasterTileServer` class**
   - Single class with all functionality
   - Internal provider registry as class-level dictionary
   - Support for "Provider.Layer" naming (e.g., "Esri.WorldImagery")

2. **Implement utility methods**
   - Migrate lonlat_to_tile, combine_tiles as static methods
   - Add zoom calculation methods as instance methods
   - All coordinate conversion utilities

### Phase 2: Provider Configuration
3. **Define provider registry**
   - Dictionary of provider configurations
   - Each provider has: url_template, tile_size, requires_api_key, special_handling
   - Support for Stadia (API key required), Esri (multiple layers), Carto

4. **Implement provider-specific behaviors**
   - Handle API key from parameter or environment variable
   - Special handling methods (e.g., make_black_transparent for Esri.Hydro)
   - Dynamic tile size based on provider

### Phase 3: Integration
5. **Add Cartopy integration**
   - Generate dynamic `cimgt.GoogleTiles` subclass for any provider
   - Returns appropriate tile source via `get_cartopy_source()`

6. **Create backward compatibility layer**
   - Keep existing function names as wrappers
   - Add deprecation warnings
   - Maintain identical signatures

### Phase 4: Documentation
7. **Add comprehensive docstrings**
   - Class and method documentation
   - Usage examples in docstrings
   - Type hints throughout

8. **Update module `__init__.py`**
   - Export only `RasterTileServer` class
   - Export backward-compatible functions
   - No subclasses to export

---

## File Structure

```
pyearthviz/map/
├── map_servers.py          # New unified implementation
├── _map_servers_legacy.py  # Backward compatibility (optional)
└── __init__.py             # Expose new API
```

---

## Migration Path

### For End Users:

**Old way (still works):**
```python
from pyearthviz.map.map_servers import Esri_terrain_images

image = Esri_terrain_images(extent, zoom_level=10)
```

**New way (recommended):**
```python
from pyearthviz.map.map_servers import RasterTileServer

server = RasterTileServer('Esri.Terrain')
image = server.fetch_tiles_for_extent(extent, zoom_level=10)
```

### Benefits of New Approach:
- **Simpler**: One class to import instead of many functions
- **Discoverable**: IDE autocomplete shows all available methods
- **Extensible**: Easy to add new providers without changing API
- **Testable**: Easier to mock and test
- **Consistent**: Same interface for all providers

---

## Detailed API Specification

### Constructor
```python
def __init__(provider: str, api_key: Optional[str] = None, **kwargs) -> None
```
**Parameters:**
- `provider`: Provider name (e.g., 'Stadia.StamenTerrain', 'Esri.Terrain', 'Esri.Relief')
- `api_key`: Optional API key for providers that require it (falls back to environment variable)
- `**kwargs`: Reserved for future extensions

**Raises:** `ValueError` if provider name not recognized

**Example:**
```python
# Provider without API key
server = RasterTileServer('Esri.Terrain')

# Provider with API key (parameter)
server = RasterTileServer('Stadia.StamenTerrain', api_key='your_key_here')

# Provider with API key (from environment)
os.environ['STADIA_API_KEY'] = 'your_key'
server = RasterTileServer('Stadia.StamenTerrain')
```

---

### Core Methods

#### `fetch_tile(z: int, x: int, y: int) -> PIL.Image`
Fetch a single tile at the specified zoom level and tile coordinates.

**Parameters:**
- `z`: Zoom level
- `x`: Tile X coordinate
- `y`: Tile Y coordinate

**Returns:** PIL Image object

---

#### `fetch_tiles_for_extent(extent: List[float], zoom_level: int) -> PIL.Image`
Fetch and combine all tiles needed to cover the specified extent.

**Parameters:**
- `extent`: [minx, maxx, miny, maxy] in longitude/latitude
- `zoom_level`: Tile zoom level

**Returns:** Combined PIL Image covering the extent

---

#### `get_cartopy_source() -> cimgt.GoogleTiles`
Get a Cartopy-compatible tile source for use with `ax.add_image()`.

**Returns:** Cartopy tile source object

---

#### `calculate_zoom_level(...) -> int`
Calculate appropriate zoom level based on scale denominator.

**Parameters:**
- `scale_denominator`: Map scale denominator
- `projection`: Projection WKT string
- `dpi`: Display DPI (default: 96)
- `tile_width`: Tile width in pixels (default: provider default)
- `tile_height`: Tile height in pixels (default: provider default)

**Returns:** Calculated zoom level

---

#### `calculate_scale_denominator(...) -> float`
Calculate scale denominator for a given extent and image size.

**Parameters:**
- `extent`: [minx, maxx, miny, maxy] in longitude/latitude
- `image_size`: (width, height) in pixels
- `dpi`: Display DPI (default: 96)

**Returns:** Scale denominator

---

### Utility Methods (Static)

#### `lonlat_to_tile(lon: float, lat: float, zoom: int) -> Tuple[int, int]`
Convert longitude/latitude to tile indices.

#### `extent_to_tile_indices(extent: List[float], zoom: int) -> Tuple[int, int, int, int]`
Convert extent to tile index range.

#### `combine_tiles(tiles: List[List[PIL.Image]], tile_size: int) -> PIL.Image`
Combine 2D array of tiles into single image.

---

## Provider Registry

### Supported Providers:

| Provider Name | Tile Size | Requires API Key | Special Handling |
|--------------|-----------|------------------|------------------|
| `Stadia.StamenTerrain` | 512x512 | Yes | None |
| `Stadia.AlidadeSmooth` | 512x512 | Yes | None |
| `Esri.Terrain` | 256x256 | No | None |
| `Esri.Relief` | 256x256 | No | None |
| `Esri.Hydro` | 256x256 | No | Black → Transparent |
| `Esri.WorldImagery` | 256x256 | No | None |
| `Carto.Positron` | 512x512 | No | None |
| `Carto.DarkMatter` | 512x512 | No | None |

**All providers use the same `RasterTileServer` class.**

---

## Testing Strategy

### Unit Tests:
1. Test coordinate conversion utilities
2. Test tile index calculations
3. Test tile combining logic
4. Mock HTTP requests for tile fetching

### Integration Tests:
1. Test with real tile servers (cached responses)
2. Test Cartopy integration
3. Test zoom level calculations

### Backward Compatibility Tests:
1. Ensure old function signatures still work
2. Verify identical output between old and new APIs

---

## Documentation Updates

### Files to Update:
1. Module docstring in [`map_servers.py`](../pyearthviz/map/map_servers.py:1)
2. Class and method docstrings (with examples)
3. Update README if map servers are mentioned
4. Add examples directory with notebooks showing usage

### Example Notebook Topics:
1. Basic usage with different providers
2. Creating custom maps with tile servers
3. Using zoom level calculations
4. Integrating with existing plotting functions

---

## Timeline & Effort

This reorganization involves:
- Refactoring existing code into class-based structure
- Adding factory pattern and registry
- Maintaining backward compatibility
- Comprehensive documentation
- Testing all functionality

---

## Benefits Summary

### For Users:
✓ **Simpler API**: One class instead of many functions
✓ **Better discoverability**: IDE autocomplete shows all options
✓ **Consistent interface**: Same methods for all providers
✓ **Easier to learn**: Logical organization and clear naming
✓ **Type safety**: Type hints for better IDE support

### For Maintainers:
✓ **Easier to extend**: Add new providers with minimal code
✓ **Less duplication**: Common logic in base class
✓ **Better testing**: Mock-friendly design
✓ **Clear structure**: Related functionality grouped together
✓ **Modern Python**: Class-based, type-hinted design

### For the Project:
✓ **Professional API**: Modern Python design patterns
✓ **Backward compatible**: Existing code continues to work
✓ **Future-proof**: Easy to add features without breaking changes
✓ **Well-documented**: Clear examples and usage patterns

---

## Next Steps

Would you like me to proceed with implementing this reorganization? I can:

1. **Create the new class-based structure** with all providers
2. **Maintain backward compatibility** with existing functions
3. **Add comprehensive documentation** and usage examples
4. **Update the module exports** for easy access

This will make the map_servers module much more user-friendly and maintainable!
