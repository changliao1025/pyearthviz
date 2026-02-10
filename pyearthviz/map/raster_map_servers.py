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

from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import warnings
import math
import numpy as np
from osgeo import osr
import cartopy.io.img_tiles as cimgt

try:
    import requests
    from PIL import Image
except ImportError:
    requests = None
    Image = None

from .base_tile_server import BaseTileServer


class RasterTileServer(BaseTileServer):
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

        # Delegate provider validation, config and API-key handling to BaseTileServer
        super().__init__(provider, api_key)

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
        x_min, y_min, x_max, y_max = RasterTileServer.extent_to_tile_indices(extent, fetch_zoom)

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
        combined_img = RasterTileServer.combine_tiles(tiles, actual_tile_size)

        # If super-sampling, downsample to target size
        if supersample > 0:
            # Calculate target size (what it would have been at original zoom)
            original_x_min, original_y_min, original_x_max, original_y_max = \
                RasterTileServer.extent_to_tile_indices(extent, zoom_level)
            target_width = (original_x_max - original_x_min + 1) * self.tile_size
            target_height = (original_y_max - original_y_min + 1) * self.tile_size

            # Downsample with high-quality filter (always use LANCZOS for downsampling)
            resample_filter = self._get_resample_filter('lanczos')
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

    def get_cartopy_source(self, supersample: int = 0, resample_method: str = 'lanczos') -> cimgt.GoogleTiles:
        """
        Get a Cartopy-compatible tile source with supersample support for use with ax.add_image().

        This creates a custom tile source that fetches tiles at a higher zoom level and downsamples
        them for better quality and smoother appearance.

        Args:
            supersample: Super-sampling level (0=off, 1=fetch 2x zoom and downsample,
                        2=fetch 4x zoom). Higher values provide better quality.
            resample_method: Resampling method - 'lanczos' (best), 'bicubic', 'bilinear', 'nearest'

        Returns:
            Cartopy GoogleTiles subclass instance with supersample support

        Example:
            >>> import matplotlib.pyplot as plt
            >>> import cartopy.crs as ccrs
            >>>
            >>> fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()})
            >>> server = RasterTileServer('Esri.Terrain')
            >>> # Use supersample for better quality
            >>> ax.add_image(server.get_cartopy_source(supersample=1), 10)
        """
        # Unified cartopy tile source supporting optional supersampling.
        provider = self.provider
        config = self._config
        api_key = self.api_key
        parent_instance = self
        resample_filter = self._get_resample_filter(resample_method)

        class UnifiedTileSource(cimgt.GoogleTiles):
            def _image_url(self, tile):
                x, y, z = tile
                # Determine fetch zoom and tile coords depending on supersample
                fetch_z = z + supersample if supersample and supersample > 0 else z
                max_zoom = config.get('max_zoom', 18)
                if fetch_z > max_zoom:
                    fetch_z = max_zoom

                scale = 2 ** max(0, fetch_z - z)
                fetch_x = x * scale
                fetch_y = y * scale

                return config['url_template'].format(z=fetch_z, x=fetch_x, y=fetch_y, api_key=api_key or '')

            def get_image(self, tile):
                x, y, z = tile

                # If no supersample requested, defer to parent behaviour and apply special handling
                if not supersample or supersample <= 0:
                    result = super().get_image(tile)
                    img, extent, origin = result
                    if config.get('special_handling'):
                        img = parent_instance._apply_special_handling(img)
                    return img, extent, origin

                # Compute actual supersample level respecting provider max_zoom
                fetch_z = z + supersample
                max_zoom = config.get('max_zoom', 18)
                actual_supersample = supersample
                if fetch_z > max_zoom:
                    actual_supersample = max_zoom - z
                    fetch_z = max_zoom

                if actual_supersample <= 0:
                    result = super().get_image(tile)
                    img, extent, origin = result
                    if config.get('special_handling'):
                        img = parent_instance._apply_special_handling(img)
                    return img, extent, origin

                scale = 2 ** actual_supersample

                # Fetch all high-res tiles and ensure RGBA
                tiles = []
                for dy in range(scale):
                    row = []
                    for dx in range(scale):
                        fetch_x = x * scale + dx
                        fetch_y = y * scale + dy
                        try:
                            high_res_tile = parent_instance.fetch_tile(fetch_z, fetch_x, fetch_y)
                            if high_res_tile.mode != 'RGBA':
                                high_res_tile = high_res_tile.convert('RGBA')
                            row.append(high_res_tile)
                        except Exception:
                            blank = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))
                            row.append(blank)
                    tiles.append(row)

                if tiles and tiles[0]:
                    actual_tile_size = tiles[0][0].size[0]
                    combined_img = parent_instance.combine_tiles(tiles, actual_tile_size)
                else:
                    combined_img = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))

                # Downsample to target tile size
                target_size = parent_instance.tile_size
                combined_img = combined_img.resize((target_size, target_size), resample=resample_filter)

                # Try to obtain extent from parent, use base class fallback if needed
                try:
                    _, extent, origin = super().get_image(tile)
                except Exception:
                    extent = BaseTileServer._calculate_tile_extent_web_mercator(x, y, z)
                    origin = 'upper'

                return combined_img, extent, origin

        return UnifiedTileSource()

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


    def suggest_optimal_zoom(
        self,
        extent: List[float],
        output_dpi: int,
        output_size: Tuple[int, int],
        quality_preference: str = 'balanced'
    ) -> int:
        """
        Suggest optimal zoom level based on output requirements and quality preference.
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
            'fast': -1,
            'balanced': 0,
            'quality': +2
        }

        adjustment = quality_adjustments.get(quality_preference.lower(), 0)

        # Account for @2x tiles (512px)
        if self.tile_size >= 512:
            adjustment += 1

        suggested_zoom = base_zoom + adjustment

        # Clamp to provider's zoom range
        min_zoom = self._config.get('min_zoom', 0)
        max_zoom = self._config.get('max_zoom', 18)
        suggested_zoom = max(min_zoom, min(max_zoom, suggested_zoom))

        return suggested_zoom

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

    def _validate_zoom_level(self, zoom_level: int, supersample: int = 0) -> Tuple[int, int]:
        """Validate and adjust zoom + supersample against provider limits.

        Returns (fetch_zoom, adjusted_supersample).
        """
        fetch_zoom = zoom_level + supersample
        min_zoom = self._config.get('min_zoom', 0)
        max_zoom = self._config.get('max_zoom', 18)

        if zoom_level < min_zoom:
            raise ValueError(f"{self.provider} does not support zoom level {zoom_level}. Minimum supported zoom is {min_zoom}.")
        if zoom_level > max_zoom:
            raise ValueError(f"{self.provider} does not support zoom level {zoom_level}. Maximum supported zoom is {max_zoom}.")

        if fetch_zoom > max_zoom:
            original_supersample = supersample
            supersample = max(0, max_zoom - zoom_level)
            warnings.warn(
                f"{self.provider} maximum zoom level is {max_zoom}. Requested zoom {zoom_level} with supersample={original_supersample} would require zoom {fetch_zoom}. Automatically reducing supersample to {supersample}.",
                UserWarning,
            )
            fetch_zoom = zoom_level + supersample

        return fetch_zoom, supersample

    # --- Class methods ---
    @classmethod
    def extent_to_tile_indices(
        cls,
        extent: List[float],
        zoom: int
    ) -> Tuple[int, int, int, int]:
        """
        Convert extent (minx, maxx, miny, maxy) to tile indices at a given zoom level.

        Implemented as a classmethod so subclasses can override `lonlat_to_tile`.
        """
        minx, maxx, miny, maxy = extent
        x_min, y_max = cls.lonlat_to_tile(minx, miny, zoom)
        x_max, y_min = cls.lonlat_to_tile(maxx, maxy, zoom)
        return x_min, y_min, x_max, y_max

    @classmethod
    def lonlat_to_tile(cls, lon: float, lat: float, zoom: int) -> Tuple[int, int]:
        """
        Convert longitude and latitude to tile indices at a given zoom level.
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

    # --- Static / utility methods ---
    @staticmethod
    def combine_tiles(
        tiles: List[List['Image.Image']],
        tile_size: int
    ) -> 'Image.Image':
        """
        Combine a 2D array of tile images into a single image.
        """
        rows = len(tiles)
        cols = len(tiles[0]) if rows > 0 else 0

        if rows == 0 or cols == 0:
            return Image.new('RGBA', (tile_size, tile_size))

        combined_img = Image.new('RGBA', (cols * tile_size, rows * tile_size))

        for row in range(rows):
            for col in range(cols):
                combined_img.paste(tiles[row][col], (col * tile_size, row * tile_size))

        return combined_img

    @staticmethod
    def calculate_zoom_level(
        scale_denominator, pProjection, dpi=96, tile_width=256, tile_height=256
    ):
        """
        Calculates the appropriate zoom level based on the scale denominator, CRS, and DPI.
        """

        pSpatial_reference_target = osr.SpatialReference()
        pSpatial_reference_target.ImportFromWkt(pProjection)
        meters_per_unit = pSpatial_reference_target.GetLinearUnits()

        pixel_size_in_meters = 0.00028
        pixel_span = (
            scale_denominator * pixel_size_in_meters / meters_per_unit / (dpi / 96.0)
        )

        tile_span_x = tile_width * pixel_span
        tile_span_y = tile_height * pixel_span

        zoom_level = int(math.log2(40075016.68557849 / max(tile_span_x, tile_span_y)))

        return zoom_level

    @staticmethod
    def _calculate_tile_extent_web_mercator(x: int, y: int, z: int) -> Tuple[float, float, float, float]:
        """
        Calculate the Web Mercator extent for a tile at given coordinates.

        This is a fallback utility for cartopy tile sources when extent cannot be obtained
        from the parent class. Web Mercator (EPSG:3857) bounds are ±20037508.34 meters.
        """
        world_extent = 20037508.342789244  # Web Mercator world extent
        tile_width = (2 * world_extent) / (2 ** z)

        min_x = -world_extent + (x * tile_width)
        max_x = min_x + tile_width
        max_y = world_extent - (y * tile_width)
        min_y = max_y - tile_width

        return (min_x, max_x, min_y, max_y)

    @staticmethod
    def _get_resample_filter(method: str):
        """Get PIL resampling filter from method name.

        Args:
            method: Resampling method name - 'lanczos', 'bicubic', 'bilinear', 'nearest'

        Returns:
            PIL resampling filter constant
        """
        if Image is None:
            raise ImportError("PIL/Pillow is required for resampling operations")

        filters = {
            'lanczos': Image.LANCZOS,
            'bicubic': Image.BICUBIC,
            'bilinear': Image.BILINEAR,
            'nearest': Image.NEAREST
        }
        return filters.get(method.lower(), Image.LANCZOS)

    @classmethod
    def extent_to_tile_indices(
        cls,
        extent: List[float],
        zoom: int
    ) -> Tuple[int, int, int, int]:
        """
        Convert extent (minx, maxx, miny, maxy) to tile indices at a given zoom level.

        Implemented as a classmethod so subclasses can override `lonlat_to_tile`.
        """
        minx, maxx, miny, maxy = extent
        x_min, y_max = cls.lonlat_to_tile(minx, miny, zoom)
        x_max, y_min = cls.lonlat_to_tile(maxx, maxy, zoom)
        return x_min, y_min, x_max, y_max

    @staticmethod
    def combine_tiles(
        tiles: List[List['Image.Image']],
        tile_size: int
    ) -> 'Image.Image':
        """
        Combine a 2D array of tile images into a single image.
        """
        rows = len(tiles)
        cols = len(tiles[0]) if rows > 0 else 0

        if rows == 0 or cols == 0:
            return Image.new('RGBA', (tile_size, tile_size))

        combined_img = Image.new('RGBA', (cols * tile_size, rows * tile_size))

        for row in range(rows):
            for col in range(cols):
                combined_img.paste(tiles[row][col], (col * tile_size, row * tile_size))

        return combined_img



    def _validate_zoom_level(self, zoom_level: int, supersample: int = 0) -> Tuple[int, int]:
        """Validate and adjust zoom + supersample against provider limits.

        Returns (fetch_zoom, adjusted_supersample).
        """
        fetch_zoom = zoom_level + supersample
        min_zoom = self._config.get('min_zoom', 0)
        max_zoom = self._config.get('max_zoom', 18)

        if zoom_level < min_zoom:
            raise ValueError(f"{self.provider} does not support zoom level {zoom_level}. Minimum supported zoom is {min_zoom}.")
        if zoom_level > max_zoom:
            raise ValueError(f"{self.provider} does not support zoom level {zoom_level}. Maximum supported zoom is {max_zoom}.")

        if fetch_zoom > max_zoom:
            original_supersample = supersample
            supersample = max(0, max_zoom - zoom_level)
            warnings.warn(
                f"{self.provider} maximum zoom level is {max_zoom}. Requested zoom {zoom_level} with supersample={original_supersample} would require zoom {fetch_zoom}. Automatically reducing supersample to {supersample}.",
                UserWarning,
            )
            fetch_zoom = zoom_level + supersample

        return fetch_zoom, supersample

    @staticmethod
    def calculate_zoom_level(
        scale_denominator, pProjection, dpi=96, tile_width=256, tile_height=256
    ):
        """
        Calculates the appropriate zoom level based on the scale denominator, CRS, and DPI.
        """

        pSpatial_reference_target = osr.SpatialReference()
        pSpatial_reference_target.ImportFromWkt(pProjection)
        meters_per_unit = pSpatial_reference_target.GetLinearUnits()

        pixel_size_in_meters = 0.00028
        pixel_span = (
            scale_denominator * pixel_size_in_meters / meters_per_unit / (dpi / 96.0)
        )

        tile_span_x = tile_width * pixel_span
        tile_span_y = tile_height * pixel_span

        zoom_level = int(math.log2(40075016.68557849 / max(tile_span_x, tile_span_y)))

        return zoom_level

    @classmethod
    def lonlat_to_tile(cls, lon: float, lat: float, zoom: int) -> Tuple[int, int]:
        """
        Convert longitude and latitude to tile indices at a given zoom level.
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
    def _calculate_tile_extent_web_mercator(x: int, y: int, z: int) -> Tuple[float, float, float, float]:
        """
        Calculate the Web Mercator extent for a tile at given coordinates.

        This is a fallback utility for cartopy tile sources when extent cannot be obtained
        from the parent class. Web Mercator (EPSG:3857) bounds are ±20037508.34 meters.

        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            z: Zoom level

        Returns:
            Tuple of (min_x, max_x, min_y, max_y) in Web Mercator meters
        """
        world_extent = 20037508.342789244  # Web Mercator world extent
        tile_width = (2 * world_extent) / (2 ** z)

        min_x = -world_extent + (x * tile_width)
        max_x = min_x + tile_width
        max_y = world_extent - (y * tile_width)
        min_y = max_y - tile_width

        return (min_x, max_x, min_y, max_y)

    @staticmethod
    def _get_resample_filter(method: str):
        """Get PIL resampling filter from method name.

        Args:
            method: Resampling method name - 'lanczos', 'bicubic', 'bilinear', 'nearest'

        Returns:
            PIL resampling filter constant
        """
        if Image is None:
            raise ImportError("PIL/Pillow is required for resampling operations")

        filters = {
            'lanczos': Image.LANCZOS,
            'bicubic': Image.BICUBIC,
            'bilinear': Image.BILINEAR,
            'nearest': Image.NEAREST
        }
        return filters.get(method.lower(), Image.LANCZOS)

