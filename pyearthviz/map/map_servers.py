"""
Map Tile Server Module

This module provides a unified interface for accessing various map tile servers
through a single RasterTileServer class.

Updated Server URLs:
- Stadia Maps (formerly Stamen): Requires API key, uses @2x tiles (512x512)
- Esri Services: Stable HTTPS URLs from ArcGIS Online
- Carto: High-quality basemaps for data visualization

Main Class:
    RasterTileServer: Unified interface for all tile server providers

Example:
    >>> # Create a tile server instance
    >>> server = RasterTileServer('Esri.Terrain')
    >>>
    >>> # Fetch tiles for an extent
    >>> extent = [minx, maxx, miny, maxy]
    >>> image = server.fetch_tiles_for_extent(extent, zoom_level=10)
    >>>
    >>> # Use with Cartopy
    >>> ax.add_image(server.get_cartopy_source(), zoom_level)
    >>>
    >>> # List available providers
    >>> providers = RasterTileServer.get_available_providers()
"""

import os
import math
import warnings
from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

import numpy as np
from osgeo import osr
import cartopy.io.img_tiles as cimgt


try:
    import requests
    from PIL import Image
except ImportError:
    requests = None
    Image = None

from pyearth.gis.spatialref.convert_between_degree_and_meter import degree_to_meter


class RasterTileServer:
    """
    Unified interface for accessing map tile servers.

    All tile server providers are accessed through this single class. Users
    specify the provider name when creating an instance, and all methods
    work consistently across different providers.

    Attributes:
        provider (str): Provider name (e.g., 'Esri.Terrain', 'Stadia.StamenTerrain')
        tile_size (int): Tile size in pixels (automatically set based on provider)
        api_key (Optional[str]): API key for providers that require it

    Example:
        >>> # Simple usage
        >>> server = RasterTileServer('Esri.Terrain')
        >>> image = server.fetch_tiles_for_extent([minx, maxx, miny, maxy], zoom_level=10)
        >>>
        >>> # With API key
        >>> server = RasterTileServer('Stadia.StamenTerrain', api_key='your_key')
        >>> tile = server.fetch_tile(z=10, x=163, y=395)
    """

    # Provider registry with configuration for each tile server
    _PROVIDERS = {
        'Stadia.StamenTerrain': {
            'url_template': 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}@2x.png?api_key={api_key}',
            'tile_size': 512,
            'requires_api_key': True,
            'special_handling': None,
            'description': 'Stadia Maps terrain tiles (formerly Stamen)',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Stadia Maps, © Stamen Design, © OpenMapTiles, © OpenStreetMap contributors',
            'license_url': 'https://stadiamaps.com/terms-of-service/',
            'data_source': 'OpenStreetMap'
        },
        'Stadia.AlidadeSmooth': {
            'url_template': 'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}@2x.png?api_key={api_key}',
            'tile_size': 512,
            'requires_api_key': True,
            'special_handling': None,
            'description': 'Stadia Maps smooth basemap',
            'min_zoom': 0,
            'max_zoom': 20,
            'attribution': '© Stadia Maps, © OpenMapTiles, © OpenStreetMap contributors',
            'license_url': 'https://stadiamaps.com/terms-of-service/',
            'data_source': 'OpenStreetMap'
        },
        'Esri.Terrain': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Terrain Base',
            'min_zoom': 0,
            'max_zoom': 13,
            'attribution': 'Source: Esri, Earthstar Geographics',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        'Esri.Relief': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}.jpg',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Shaded Relief',
            'min_zoom': 0,
            'max_zoom': 13,
            'attribution': 'Source: Esri',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        #https://tiles.arcgis.com/tiles/P3ePLMYs2RVChkJx/arcgis/rest/services/Esri_Hydro_Reference_Overlay/MapServer
        'Esri.Hydro': {
            'url_template': 'https://tiles.arcgis.com/tiles/P3ePLMYs2RVChkJx/arcgis/rest/services/Esri_Hydro_Reference_Overlay/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': 'make_black_transparent',
            'description': 'Esri Hydro Reference Overlay',
            'min_zoom': 0,
            'max_zoom': 19,
            'attribution': 'Source: Esri',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        'Esri.WorldImagery': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Imagery (satellite)',
            'min_zoom': 0,
            'max_zoom': 19,
            'attribution': 'Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri/Maxar'
        },
        'Esri.WorldTopo': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Topographic Map',
            'min_zoom': 0,
            'max_zoom': 19,
            'attribution': 'Source: Esri, HERE, Garmin, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), © OpenStreetMap contributors, GIS User Community',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        'Esri.NatGeo': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri National Geographic World Map',
            'min_zoom': 0,
            'max_zoom': 16,
            'attribution': 'Source: National Geographic, Esri, Garmin, HERE, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, increment P Corp.',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'National Geographic/Esri'
        },
        'Esri.WorldStreet': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Street Map',
            'min_zoom': 0,
            'max_zoom': 19,
            'attribution': 'Source: Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, © OpenStreetMap contributors, GIS User Community',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        'Esri.GrayCanvasBase': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Gray_Canvas/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Gray Canvas Base',
            'min_zoom': 0,
            'max_zoom': 16,
            'attribution': 'Source: Esri, HERE, Garmin, © OpenStreetMap contributors, GIS User Community',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        'Esri.GrayCanvasLabels': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Gray_Canvas_Reference/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Gray Canvas Labels',
            'min_zoom': 0,
            'max_zoom': 16,
            'attribution': 'Source: Esri, HERE, Garmin, © OpenStreetMap contributors, GIS User Community',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        'Esri.WorldOceanBase': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Ocean Base',
            'min_zoom': 0,
            'max_zoom': 10,
            'attribution': 'Source: Esri, GEBCO, NOAA, National Geographic, Garmin, HERE, Geonames.org',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri/GEBCO'
        },
        'Carto.Positron': {
            'url_template': 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png',
            'tile_size': 512,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Carto Positron (light basemap)',
            'min_zoom': 0,
            'max_zoom': 20,
            'attribution': '© CARTO, © OpenStreetMap contributors',
            'license_url': 'https://carto.com/legal/',
            'data_source': 'OpenStreetMap'
        },
        'Carto.DarkMatter': {
            'url_template': 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png',
            'tile_size': 512,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Carto Dark Matter (dark basemap)',
            'min_zoom': 0,
            'max_zoom': 20,
            'attribution': '© CARTO, © OpenStreetMap contributors',
            'license_url': 'https://carto.com/legal/',
            'data_source': 'OpenStreetMap'
        },
        'OSM.Standard': {
            'url_template': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'OpenStreetMap Standard tiles',
            'min_zoom': 0,
            'max_zoom': 19,
            'attribution': '© OpenStreetMap contributors',
            'license_url': 'https://www.openstreetmap.org/copyright',
            'data_source': 'OpenStreetMap'
        }
    }

    def __init__(self, provider: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize a RasterTileServer instance.

        Args:
            provider: Provider name (e.g., 'Esri.Terrain', 'Stadia.StamenTerrain')
            api_key: Optional API key for providers that require authentication.
                    Falls back to environment variable if not provided.
            **kwargs: Reserved for future extensions

        Raises:
            ValueError: If provider name is not recognized
            ImportError: If required packages (requests, PIL) are not installed

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> server = RasterTileServer('Stadia.StamenTerrain', api_key='your_key')
        """
        if requests is None or Image is None:
            raise ImportError(
                "The packages 'requests' and 'Pillow' are required for tile fetching. "
                "Install them with: pip install requests Pillow"
            )

        if provider not in self._PROVIDERS:
            available = ', '.join(self._PROVIDERS.keys())
            raise ValueError(
                f"Unknown provider '{provider}'. Available providers: {available}"
            )

        self.provider = provider
        self._config = self._PROVIDERS[provider].copy()
        self.tile_size = self._config['tile_size']

        # Handle API key
        if self._config['requires_api_key']:
            if api_key:
                self.api_key = api_key
            else:
                # Try to get from environment
                env_key = 'STADIA_API_KEY' if 'Stadia' in provider else None
                if env_key:
                    self.api_key = os.environ.get(env_key)
                    if not self.api_key:
                        warnings.warn(
                            f"Provider '{provider}' requires an API key. "
                            f"Provide it via api_key parameter or {env_key} environment variable."
                        )
                else:
                    self.api_key = None
        else:
            self.api_key = api_key

    def _validate_zoom_level(self, zoom_level: int, supersample: int = 0) -> Tuple[int, int]:
        """
        Validate zoom level against provider constraints and adjust if needed.

        Args:
            zoom_level: Base zoom level
            supersample: Super-sampling level

        Returns:
            Tuple of (validated_fetch_zoom, adjusted_supersample)

        Raises:
            ValueError: If even the base zoom level exceeds provider limits
        """
        fetch_zoom = zoom_level + supersample
        min_zoom = self._config.get('min_zoom', 0)
        max_zoom = self._config.get('max_zoom', 18)

        # Check minimum
        if zoom_level < min_zoom:
            raise ValueError(
                f"{self.provider} does not support zoom level {zoom_level}. "
                f"Minimum supported zoom is {min_zoom}."
            )

        # Check maximum for base zoom
        if zoom_level > max_zoom:
            raise ValueError(
                f"{self.provider} does not support zoom level {zoom_level}. "
                f"Maximum supported zoom is {max_zoom}."
            )

        # Check if supersample pushes beyond max_zoom
        if fetch_zoom > max_zoom:
            original_supersample = supersample
            supersample = max(0, max_zoom - zoom_level)
            warnings.warn(
                f"{self.provider} maximum zoom level is {max_zoom}. "
                f"Requested zoom {zoom_level} with supersample={original_supersample} "
                f"would require zoom {fetch_zoom}. "
                f"Automatically reducing supersample to {supersample} (fetch zoom={zoom_level + supersample}).",
                UserWarning
            )
            fetch_zoom = zoom_level + supersample

        return fetch_zoom, supersample

    def get_url_template(self) -> str:
        """
        Get the URL template for this provider.

        Returns:
            URL template string with placeholders for {z}, {x}, {y}, and optionally {api_key}

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> print(server.get_url_template())
        """
        return self._config['url_template']

    def _build_tile_url(self, z: int, x: int, y: int) -> str:
        """Build the complete URL for a specific tile."""
        url = self._config['url_template'].format(
            z=z, x=x, y=y, api_key=self.api_key or ''
        )
        return url

    def _apply_special_handling(self, img: 'Image.Image') -> 'Image.Image':
        """Apply provider-specific image processing."""
        handling = self._config.get('special_handling')

        if handling == 'make_black_transparent':
            # Convert black pixels to transparent (used for Esri.Hydro)
            img = img.convert('RGBA')
            datas = img.getdata()
            new_data = []
            for item in datas:
                # Change all black pixels to transparent
                if item[0] == 0 and item[1] == 0 and item[2] == 0:
                    new_data.append((0, 0, 0, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)

        return img

    def fetch_tile(self, z: int, x: int, y: int) -> 'Image.Image':
        """
        Fetch a single tile at the specified zoom level and tile coordinates.

        Args:
            z: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate

        Returns:
            PIL Image object

        Raises:
            Exception: If tile fetch fails

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> tile = server.fetch_tile(z=10, x=163, y=395)
        """
        url = self._build_tile_url(z, x, y)
        response = requests.get(url)

        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))

            # Apply special handling if needed
            if self._config['special_handling']:
                img = self._apply_special_handling(img)

            return img
        else:
            raise Exception(
                f"Failed to fetch tile from {self.provider}: "
                f"HTTP {response.status_code} - {url}"
            )

    def fetch_tiles_for_extent(
        self,
        extent: List[float],
        zoom_level: int,
        supersample: int = 0,
        resample: bool = True,
        resample_method: str = 'lanczos'
    ) -> np.ndarray:
        """
        Fetch and combine all tiles needed to cover the specified extent.

        Args:
            extent: [minx, maxx, miny, maxy] in longitude/latitude (degrees)
            zoom_level: Tile zoom level (typically 1-18)
            supersample: Super-sampling level (0=off, 1=fetch 2x zoom and downsample,
                        2=fetch 4x zoom). Higher values provide better quality but
                        require downloading 4^supersample more tiles.
            resample: Apply high-quality resampling filter for smooth appearance
            resample_method: Resampling method - 'lanczos' (best), 'bicubic', 'bilinear', 'nearest'

        Returns:
            NumPy array of the combined image (RGBA format)

        Note:
            Super-sampling + LANCZOS downsampling naturally eliminates tile boundaries
            through proper signal processing. No artificial edge blending is needed.

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> extent = [-122.5, -122.3, 37.7, 37.8]  # San Francisco area
            >>> # Standard quality
            >>> image_array = server.fetch_tiles_for_extent(extent, zoom_level=12)
            >>> # High quality with super-sampling (recommended)
            >>> image_array = server.fetch_tiles_for_extent(
            ...     extent, zoom_level=12, supersample=1, resample=True
            ... )
        """
        # Validate and adjust zoom levels if needed
        fetch_zoom, supersample = self._validate_zoom_level(zoom_level, supersample)

        minx, maxx, miny, maxy = extent
        x_min, y_min, x_max, y_max = self.extent_to_tile_indices(
            extent, fetch_zoom
        )

        # Fetch tiles
        tiles = []
        for y in range(y_min, y_max + 1):
            row = []
            for x in range(x_min, x_max + 1):
                tile = self.fetch_tile(fetch_zoom, x, y)
                row.append(tile)
            tiles.append(row)

        # Determine tile size for combining (actual tile size, may be 512 for @2x)
        actual_tile_size = tiles[0][0].size[0] if tiles and tiles[0] else self.tile_size

        # Combine the tiles into a single image
        combined_img = self.combine_tiles(tiles, actual_tile_size)

        # If super-sampling, downsample to target size
        if supersample > 0:
            # Calculate target size (what it would have been at original zoom)
            original_x_min, original_y_min, original_x_max, original_y_max = \
                self.extent_to_tile_indices(extent, zoom_level)
            target_width = (original_x_max - original_x_min + 1) * self.tile_size
            target_height = (original_y_max - original_y_min + 1) * self.tile_size

            # Downsample with high-quality filter
            resample_filter = self._get_resample_filter('lanczos')  # Always use LANCZOS for downsampling
            combined_img = combined_img.resize(
                (target_width, target_height),
                resample=resample_filter
            )

        # Apply resampling filter if requested and not already done
        if resample and supersample == 0:
            # Apply gentle smoothing to remove tile artifacts
            current_size = combined_img.size
            resample_filter = self._get_resample_filter(resample_method)
            # Slightly upsample then downsample for smoothing effect
            temp_size = (int(current_size[0] * 1.02), int(current_size[1] * 1.02))
            combined_img = combined_img.resize(temp_size, resample=Image.BICUBIC)
            combined_img = combined_img.resize(current_size, resample=resample_filter)

        # Convert to NumPy array
        img_array = np.array(combined_img)
        return img_array

    def _get_resample_filter(self, method: str):
        """Get PIL resampling filter from method name."""
        filters = {
            'lanczos': Image.LANCZOS,
            'bicubic': Image.BICUBIC,
            'bilinear': Image.BILINEAR,
            'nearest': Image.NEAREST
        }
        return filters.get(method.lower(), Image.LANCZOS)

    def get_cartopy_source(self) -> cimgt.GoogleTiles:
        """
        Get a Cartopy-compatible tile source for use with ax.add_image().

        Returns:
            Cartopy GoogleTiles subclass instance

        Example:
            >>> import matplotlib.pyplot as plt
            >>> import cartopy.crs as ccrs
            >>>
            >>> fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
            >>> server = RasterTileServer('Esri.Terrain')
            >>> ax.add_image(server.get_cartopy_source(), 10)
        """
        # Create a dynamic GoogleTiles subclass for this provider
        provider = self.provider
        config = self._config
        api_key = self.api_key

        class DynamicTileSource(cimgt.GoogleTiles):
            def _image_url(self, tile):
                x, y, z = tile
                url = config['url_template'].format(
                    z=z, x=x, y=y, api_key=api_key or ''
                )
                return url

        return DynamicTileSource()

    def suggest_optimal_zoom(
        self,
        extent: List[float],
        output_dpi: int,
        output_size: Tuple[int, int],
        quality_preference: str = 'balanced'
    ) -> int:
        """
        Suggest optimal zoom level based on output requirements and quality preference.

        This method calculates the best zoom level to achieve good quality output
        considering the extent size, output DPI, image dimensions, and tile size.

        Args:
            extent: [minx, maxx, miny, maxy] in longitude/latitude (degrees)
            output_dpi: Output DPI (e.g., 150 for screen, 300 for print)
            output_size: (width, height) in pixels
            quality_preference: 'fast' (lower zoom), 'balanced', or 'quality' (higher zoom)

        Returns:
            Recommended zoom level (integer)

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> extent = [115, 119, 36, 38]  # 4° × 2° area
            >>> zoom = server.suggest_optimal_zoom(
            ...     extent, output_dpi=150, output_size=(1200, 1200), quality_preference='quality'
            ... )
            >>> print(f"Recommended zoom: {zoom}")
        """
        # Calculate base zoom using existing method
        scale_denominator = self.calculate_scale_denominator(extent, output_size, output_dpi)
        pSrc = osr.SpatialReference()
        pSrc.ImportFromEPSG(3857)  # Web Mercator
        projection_wkt = pSrc.ExportToWkt()

        base_zoom = self.calculate_zoom_level(
            scale_denominator,
            projection_wkt,
            dpi=output_dpi,
            tile_width=self.tile_size,
            tile_height=self.tile_size
        )

        # Adjust based on quality preference
        quality_adjustments = {
            'fast': -1,      # One level lower for faster loading
            'balanced': 0,   # Use calculated zoom
            'quality': +2    # Two levels higher for best quality
        }

        adjustment = quality_adjustments.get(quality_preference.lower(), 0)

        # Account for @2x tiles (512px) - they effectively provide one zoom level higher
        if self.tile_size >= 512:
            adjustment += 1

        suggested_zoom = base_zoom + adjustment

        # Clamp to reasonable range
        suggested_zoom = max(1, min(18, suggested_zoom))

        return suggested_zoom

    def get_projected_extent(
        self,
        extent: List[float],
        zoom_level: int,
        source_crs=None
    ) -> Tuple[List[float], Any]:
        """
        Get the projected extent for tile fetching from a lat/lon extent.

        This method projects the extent into the tile server's CRS (Web Mercator)
        and returns the extent bounds needed for image_for_domain().

        Args:
            extent: [minx, maxx, miny, maxy] in source CRS (default: lat/lon degrees)
            zoom_level: Zoom level for tile fetching
            source_crs: Source coordinate reference system (default: PlateCarree/WGS84)

        Returns:
            Tuple of (projected_extent, target_domain_geometry)
            - projected_extent: [minx, maxx, miny, maxy] in Web Mercator
            - target_domain_geometry: Shapely geometry in Web Mercator

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> extent = [-122.5, -122.3, 37.7, 37.8]
            >>> proj_extent, geom = server.get_projected_extent(extent, zoom_level=10)
            >>> # Use with image_for_domain
            >>> tile_source = server.get_cartopy_source()
            >>> _, img_extent, _ = tile_source.image_for_domain(geom, zoom_level)
        """
        import shapely.geometry as sgeom
        import cartopy.crs as ccrs

        # Default to PlateCarree (lat/lon) if not specified
        if source_crs is None:
            source_crs = ccrs.PlateCarree()

        minx, maxx, miny, maxy = extent

        # Create bounding box in source CRS
        ll_target_domain = sgeom.box(minx, miny, maxx, maxy)

        # Get the tile source which uses Web Mercator
        tile_source = self.get_cartopy_source()

        # Project geometry from source CRS to tile CRS (Web Mercator)
        multi_poly = tile_source.crs.project_geometry(ll_target_domain, source_crs)
        target_domain = multi_poly.geoms[0] if hasattr(multi_poly, 'geoms') else multi_poly

        # Get the extent in the projected CRS
        _, projected_extent, _ = tile_source.image_for_domain(target_domain, zoom_level)

        return projected_extent, target_domain

    @staticmethod
    def lonlat_to_tile(lon: float, lat: float, zoom: int) -> Tuple[int, int]:
        """
        Convert longitude and latitude to tile indices at a given zoom level.

        Args:
            lon: Longitude in degrees
            lat: Latitude in degrees
            zoom: Zoom level

        Returns:
            Tuple of (x_tile, y_tile) indices

        Example:
            >>> x, y = RasterTileServer.lonlat_to_tile(-122.4, 37.8, zoom=10)
        """
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x_tile = int((lon + 180.0) / 360.0 * n)
        y_tile = int(
            (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
            / 2.0
            * n
        )
        return x_tile, y_tile

    @staticmethod
    def extent_to_tile_indices(
        extent: List[float],
        zoom: int
    ) -> Tuple[int, int, int, int]:
        """
        Convert extent (minx, miny, maxx, maxy) to tile indices at a given zoom level.

        Args:
            extent: [minx, maxx, miny, maxy] in longitude/latitude (degrees)
            zoom: Zoom level

        Returns:
            Tuple of (x_min, y_min, x_max, y_max) tile indices

        Example:
            >>> extent = [-122.5, -122.3, 37.7, 37.8]
            >>> x_min, y_min, x_max, y_max = RasterTileServer.extent_to_tile_indices(extent, 10)
        """
        minx, maxx, miny, maxy = extent
        x_min, y_max = RasterTileServer.lonlat_to_tile(minx, miny, zoom)
        x_max, y_min = RasterTileServer.lonlat_to_tile(maxx, maxy, zoom)
        return x_min, y_min, x_max, y_max

    @staticmethod
    def combine_tiles(
        tiles: List[List['Image.Image']],
        tile_size: int
    ) -> 'Image.Image':
        """
        Combine a 2D array of tile images into a single image.

        Args:
            tiles: 2D list of PIL Image objects [row][col]
            tile_size: Size of each tile in pixels

        Returns:
            Combined PIL Image with RGBA mode

        Example:
            >>> tiles = [[tile1, tile2], [tile3, tile4]]
            >>> combined = RasterTileServer.combine_tiles(tiles, tile_size=256)
        """
        rows = len(tiles)
        cols = len(tiles[0]) if rows > 0 else 0

        if rows == 0 or cols == 0:
            # Return empty image if no tiles
            return Image.new('RGBA', (tile_size, tile_size))

        combined_img = Image.new('RGBA', (cols * tile_size, rows * tile_size))

        # Simple paste - super-sampling with LANCZOS downsampling eliminates tile boundaries naturally
        for row in range(rows):
            for col in range(cols):
                combined_img.paste(tiles[row][col], (col * tile_size, row * tile_size))

        return combined_img

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Get a list of all available tile server providers.

        Returns:
            List of provider names

        Example:
            >>> providers = RasterTileServer.get_available_providers()
            >>> print(providers)
            ['Stadia.StamenTerrain', 'Esri.Terrain', 'Esri.Relief', ...]
        """
        return list(cls._PROVIDERS.keys())

    @classmethod
    def get_provider_info(cls, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a provider or all providers.

        Args:
            provider: Optional provider name. If None, returns info for all providers.

        Returns:
            Dictionary with provider information

        Example:
            >>> info = RasterTileServer.get_provider_info('Esri.Terrain')
            >>> print(info['description'])
        """
        if provider:
            if provider not in cls._PROVIDERS:
                raise ValueError(f"Unknown provider '{provider}'")
            return cls._PROVIDERS[provider].copy()
        else:
            return {k: v.copy() for k, v in cls._PROVIDERS.items()}

    def get_license_info(self, year: Optional[str] = None, include_url: bool = False) -> str:
        """
        Get the license/attribution information for the tile provider.

        This information should be included when displaying maps using these tiles
        to comply with the provider's terms of service and properly credit data sources.

        Args:
            year: Optional year to include in attribution (default: current year)
            include_url: If True, includes the license URL in the attribution string

        Returns:
            Formatted attribution/license string

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> license_info = server.get_license_info()
            >>> print(license_info)
            'Source: Esri, Earthstar Geographics (2026)'

            >>> # With license URL
            >>> license_info = server.get_license_info(include_url=True)
            >>> print(license_info)
            'Source: Esri, Earthstar Geographics (2026). License: https://www.esri.com/...'

            >>> # For OpenStreetMap-based tiles
            >>> server = RasterTileServer('Stadia.StamenTerrain', api_key='key')
            >>> license_info = server.get_license_info()
            >>> print(license_info)
            '© Stadia Maps, © Stamen Design, © OpenMapTiles, © OpenStreetMap contributors (2026)'
        """
        if year is None:
            year = str(datetime.now().year)

        attribution = self._config.get('attribution', 'Map tiles')
        license_url = self._config.get('license_url', '')

        # Add year to attribution
        license_info = f"{attribution} ({year})"

        # Optionally include license URL
        if include_url and license_url:
            license_info += f". License: {license_url}"

        return license_info

    def __repr__(self) -> str:
        """String representation of RasterTileServer instance."""
        return f"RasterTileServer(provider='{self.provider}', tile_size={self.tile_size})"

class VectorTileServer:
    """
    Lightweight client for vector tile services.

    This class exposes URLs and basic fetch helpers for vector tiles and
    style JSON. It does not render vector tiles to raster images.
    """

    _PROVIDERS = {
        'Esri.Hydro.Vector': {
            'service_url': 'https://basemaps.arcgis.com/arcgis/rest/services/World_Basemap_v2/VectorTileServer',
            'style_url': 'https://www.arcgis.com/sharing/rest/content/items/6d188135dc814d4ea254440a3dd844df/resources/styles/root.json',
            'tile_url_template': 'https://basemaps.arcgis.com/arcgis/rest/services/World_Basemap_v2/VectorTileServer/tile/{z}/{y}/{x}.pbf',
            'requires_api_key': False,
            'description': 'Esri Environment Surface Water and Label (vector tiles)',
            'min_zoom': 0,
            'max_zoom': 23
        }
    }

    def __init__(self, provider: str, api_key: Optional[str] = None, **kwargs):
        if requests is None:
            raise ImportError(
                "The package 'requests' is required for vector tile fetching. "
                "Install it with: pip install requests"
            )

        if provider not in self._PROVIDERS:
            available = ', '.join(self._PROVIDERS.keys())
            raise ValueError(
                f"Unknown provider '{provider}'. Available providers: {available}"
            )

        self.provider = provider
        self._config = self._PROVIDERS[provider].copy()

        if self._config['requires_api_key']:
            self.api_key = api_key
            if not self.api_key:
                warnings.warn(
                    f"Provider '{provider}' requires an API key. "
                    "Provide it via api_key parameter.",
                    UserWarning
                )
        else:
            self.api_key = api_key

    def _validate_zoom_level(self, zoom_level: int) -> None:
        min_zoom = self._config.get('min_zoom')
        max_zoom = self._config.get('max_zoom')

        if min_zoom is not None and zoom_level < min_zoom:
            raise ValueError(
                f"{self.provider} does not support zoom level {zoom_level}. "
                f"Minimum supported zoom is {min_zoom}."
            )

        if max_zoom is not None and zoom_level > max_zoom:
            raise ValueError(
                f"{self.provider} does not support zoom level {zoom_level}. "
                f"Maximum supported zoom is {max_zoom}."
            )

    def get_style_url(self) -> str:
        return self._config['style_url']

    def get_tile_url_template(self) -> str:
        return self._config['tile_url_template']

    def _build_tile_url(self, z: int, x: int, y: int) -> str:
        self._validate_zoom_level(z)
        url = self._config['tile_url_template'].format(z=z, x=x, y=y)
        return url

    def fetch_tile(self, z: int, x: int, y: int) -> bytes:
        """
        Fetch a vector tile as raw PBF bytes.
        """
        url = self._build_tile_url(z, x, y)
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        raise Exception(
            f"Failed to fetch tile from {self.provider}: "
            f"HTTP {response.status_code} - {url}"
        )

    def fetch_style_json(self) -> Dict[str, Any]:
        """
        Fetch the style JSON for this vector tile layer.
        """
        url = self.get_style_url()
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        raise Exception(
            f"Failed to fetch style JSON from {self.provider}: "
            f"HTTP {response.status_code} - {url}"
        )

    def fetch_tilejson(self) -> Dict[str, Any]:
        """
        Fetch the VectorTileServer metadata (TileJSON-like) payload.
        """
        url = f"{self._config['service_url']}?f=pjson"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        raise Exception(
            f"Failed to fetch tile metadata from {self.provider}: "
            f"HTTP {response.status_code} - {url}"
        )

    @classmethod
    def get_available_providers(cls) -> List[str]:
        return list(cls._PROVIDERS.keys())

    @classmethod
    def get_provider_info(cls, provider: Optional[str] = None) -> Dict[str, Any]:
        if provider:
            if provider not in cls._PROVIDERS:
                raise ValueError(f"Unknown provider '{provider}'")
            return cls._PROVIDERS[provider].copy()
        return {k: v.copy() for k, v in cls._PROVIDERS.items()}

    def __repr__(self) -> str:
        return f"VectorTileServer(provider='{self.provider}')"

