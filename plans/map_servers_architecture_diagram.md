# RasterTileServer Architecture Diagram

## Class Structure

```mermaid
classDiagram
    class RasterTileServer {
        -str provider
        -int tile_size
        -Optional[str] api_key
        -dict _config
        +__init__(provider, api_key, **kwargs)
        +fetch_tile(z, x, y) PIL.Image
        +fetch_tiles_for_extent(extent, zoom_level) PIL.Image
        +get_cartopy_source() GoogleTiles
        +get_url_template() str
        +calculate_zoom_level(scale_denominator, projection, dpi) int
        +calculate_scale_denominator(extent, image_size, dpi) float
        +lonlat_to_tile(lon, lat, zoom)$ Tuple[int, int]
        +extent_to_tile_indices(extent, zoom)$ Tuple[int, int, int, int]
        +combine_tiles(tiles, tile_size)$ PIL.Image
        +get_available_providers()$ List[str]
    }

    note for RasterTileServer "Single unified class\nAll providers use this same class\nNo subclasses needed"
```

## Usage Flow

```mermaid
sequenceDiagram
    participant User
    participant RasterTileServer
    participant ProviderRegistry
    participant TileFetcher
    participant ImageCombiner

    User->>RasterTileServer: __init__('Esri.Terrain')
    RasterTileServer->>ProviderRegistry: lookup provider config
    ProviderRegistry-->>RasterTileServer: {url_template, tile_size, ...}
    RasterTileServer-->>User: server instance

    User->>RasterTileServer: fetch_tiles_for_extent(extent, zoom)
    RasterTileServer->>RasterTileServer: extent_to_tile_indices(extent, zoom)
    RasterTileServer->>TileFetcher: fetch_tile(z, x, y) for each tile
    TileFetcher-->>RasterTileServer: tile images
    RasterTileServer->>ImageCombiner: combine_tiles(tiles, tile_size)
    ImageCombiner-->>RasterTileServer: combined image
    RasterTileServer-->>User: final image
```

## Provider Registry Structure

```mermaid
graph TB
    A[RasterTileServer._PROVIDERS] --> B[Stadia.StamenTerrain]
    A --> C[Stadia.AlidadeSmooth]
    A --> D[Esri.Terrain]
    A --> E[Esri.Relief]
    A --> F[Esri.Hydro]
    A --> G[Esri.WorldImagery]
    A --> H[Carto.Positron]
    A --> I[Carto.DarkMatter]

    B --> B1[url_template]
    B --> B2[tile_size: 512]
    B --> B3[requires_api_key: True]
    B --> B4[special_handling: None]

    D --> D1[url_template]
    D --> D2[tile_size: 256]
    D --> D3[requires_api_key: False]
    D --> D4[special_handling: None]

    F --> F1[url_template]
    F --> F2[tile_size: 256]
    F --> F3[requires_api_key: False]
    F --> F4[special_handling: make_black_transparent]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style D fill:#e8f5e9
    style F fill:#f3e5f5
```

## Method Organization

```mermaid
graph LR
    A[RasterTileServer Methods] --> B[Core Methods]
    A --> C[Calculation Methods]
    A --> D[Static Utilities]
    A --> E[Class Methods]

    B --> B1[fetch_tile]
    B --> B2[fetch_tiles_for_extent]
    B --> B3[get_cartopy_source]
    B --> B4[get_url_template]

    C --> C1[calculate_zoom_level]
    C --> C2[calculate_scale_denominator]

    D --> D1[lonlat_to_tile]
    D --> D2[extent_to_tile_indices]
    D --> D3[combine_tiles]

    E --> E1[get_available_providers]

    style B fill:#e3f2fd
    style C fill:#f3e5f5
    style D fill:#e8f5e9
    style E fill:#fff3e0
```

## Backward Compatibility Layer

```mermaid
graph TB
    A[Old Function API] --> B[fetch_stadia_tile]
    A --> C[fetch_esri_terrain_tile]
    A --> D[Esri_terrain_images]
    A --> E[Stadia_terrain_images]

    B --> F[RasterTileServer Instance]
    C --> F
    D --> F
    E --> F

    F --> G[New Unified API]

    style A fill:#ffebee
    style F fill:#e8f5e9
    style G fill:#e1f5ff
```

## Data Flow: Fetching Tiles for Extent

```mermaid
flowchart TD
    A[User calls fetch_tiles_for_extent] --> B[Parse extent: minx, maxx, miny, maxy]
    B --> C[Call extent_to_tile_indices]
    C --> D[Get tile range: x_min, y_min, x_max, y_max]
    D --> E{For each tile in range}
    E --> F[Call fetch_tile z, x, y]
    F --> G[Build URL from template]
    G --> H{Requires special handling?}
    H -->|Yes| I[Apply special processing]
    H -->|No| J[Return raw tile]
    I --> K[Collect all tiles]
    J --> K
    K --> L{All tiles fetched?}
    L -->|No| E
    L -->|Yes| M[Call combine_tiles]
    M --> N[Return combined image]

    style A fill:#e3f2fd
    style N fill:#c8e6c9
```

## Provider Selection Flow

```mermaid
flowchart TD
    A[User creates RasterTileServer] --> B{Provider name valid?}
    B -->|No| C[Raise ValueError]
    B -->|Yes| D[Load provider config]
    D --> E{Requires API key?}
    E -->|Yes| F{API key provided?}
    E -->|No| H[Set tile_size from config]
    F -->|No| G[Try environment variable]
    F -->|Yes| H
    G --> H
    H --> I[Store configuration]
    I --> J[Ready to fetch tiles]

    style A fill:#e3f2fd
    style C fill:#ffcdd2
    style J fill:#c8e6c9
```

## Key Design Benefits

```mermaid
mindmap
  root((RasterTileServer<br/>Unified Class))
    User Experience
      Simple API
      Single import
      Consistent interface
      Easy discovery
    Maintainability
      No code duplication
      Easy to extend
      Configuration driven
      Clear structure
    Flexibility
      Add providers easily
      Override behaviors
      Custom handling
      Future proof
    Integration
      Cartopy compatible
      PIL Image output
      NumPy arrays
      Backward compatible
```

## Example Usage Comparison

### Old API
```python
# Different functions for each provider
from pyearthviz.map.map_servers import (
    fetch_stadia_tile,
    fetch_esri_terrain_tile,
    Stadia_terrain_images,
    Esri_terrain_images
)

# Fetch single tile - different function names
stadia_tile = fetch_stadia_tile(z, x, y)
esri_tile = fetch_esri_terrain_tile(z, x, y)

# Fetch extent - different function names
stadia_img = Stadia_terrain_images(extent, zoom)
esri_img = Esri_terrain_images(extent, zoom)
```

### New API
```python
# Single class for everything
from pyearthviz.map.map_servers import RasterTileServer

# Fetch single tile - same method name
stadia = RasterTileServer('Stadia.StamenTerrain', api_key='key')
stadia_tile = stadia.fetch_tile(z, x, y)

esri = RasterTileServer('Esri.Terrain')
esri_tile = esri.fetch_tile(z, x, y)

# Fetch extent - same method name
stadia_img = stadia.fetch_tiles_for_extent(extent, zoom)
esri_img = esri.fetch_tiles_for_extent(extent, zoom)
```

**Result:** Simpler, more consistent, and easier to discover!
