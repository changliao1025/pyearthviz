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
from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any, NamedTuple
from datetime import datetime
import warnings
import math
import numpy as np
from osgeo import osr
import cartopy.io.img_tiles as cimgt
import cartopy.crs as ccrs

try:
    import requests
    from PIL import Image
except ImportError:
    requests = None
    Image = None

from .base_tile_server import BaseTileServer

def mercator_y_to_lat(y_metre: float) -> float:
    """Convert Web‑Mercator Y (meters) to latitude in degrees."""
    return math.degrees(2 * math.atan(math.exp(y_metre / 6378137.0)) - math.pi / 2)


class ManualBasemap(NamedTuple):
    """Everything needed to render a manually stitched basemap with ``imshow``.

    Return type of :meth:`RasterTileServer.fetch_manual_basemap` and
    :meth:`RasterTileServer.add_basemap`. It intentionally avoids cartopy's
    ``add_image`` / ``image_for_domain`` merge path (which can shift tiles for some
    providers) by carrying a pre-computed Web Mercator extent that always matches
    the stitched image.

    Attributes:
        image: RGBA numpy array of the stitched tiles (north-at-top).
        extent: ``[left, right, bottom, top]`` in Web Mercator (EPSG:3857).
        crs: cartopy CRS to pass as ``transform`` to ``imshow``.
        origin: imshow origin matching the stitched image (``'upper'``).
        attribution: license/attribution string for the provider.
    """
    image: np.ndarray
    extent: List[float]
    crs: Any
    origin: str
    attribution: str


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
        >>>
        >>> # Register a token once, then call the provider without api_key
        >>> RasterTileServer.register_api_key('Tianditu.Vector', 'your_tk_here')
        >>> server = RasterTileServer('Tianditu.Vector')
    """

    # Registered API keys/tokens, keyed by provider name. Used as a fallback
    # when a provider is instantiated without an explicit api_key.
    _REGISTERED_API_KEYS: Dict[str, str] = {}

    # Backward-compatible provider name aliases resolved in __init__
    # (e.g., the legacy bare 'OSM' maps to the registered 'OSM.Standard').
    _PROVIDER_ALIASES: Dict[str, str] = {
        'OSM': 'OSM.Standard',
    }

    @classmethod
    def register_api_key(cls, provider: str, api_key: str) -> None:
        """
        Register a default API key/token for a provider.

        Once registered, instances of the provider created without an explicit
        api_key argument automatically use the registered key. Useful for
        providers such as 'Tianditu.Vector' that require a tk token on every
        request.

        Args:
            provider: Provider name (e.g., 'Tianditu.Vector')
            api_key: API key/token to register for this provider

        Raises:
            ValueError: If provider name is not recognized

        Example:
            >>> RasterTileServer.register_api_key('Tianditu.Vector', 'your_tk_here')
            >>> server = RasterTileServer('Tianditu.Vector')  # uses registered token
        """
        if provider not in cls._PROVIDERS:
            available = ', '.join(cls._PROVIDERS.keys())
            raise ValueError(f"Unknown provider '{provider}'. Available providers: {available}")
        cls._REGISTERED_API_KEYS[provider] = api_key

    # Provider registry with configuration for each tile server
    _PROVIDERS = {
        'Stadia.StamenTerrain': {
            'url_template': 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}@2x.png?api_key={api_key}',
            'tile_size': 512,
            'requires_api_key': True,
            'api_env': 'STADIA_API_KEY',
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
            'api_env': 'STADIA_API_KEY',
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
            'tms_y_flip': False,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'OpenStreetMap Standard tiles',
            'min_zoom': 0,
            'max_zoom': 19,
            'attribution': '© OpenStreetMap contributors',
            'license_url': 'https://www.openstreetmap.org/copyright',
            'data_source': 'OpenStreetMap'
        },
        'OSM.HOT': {
            'url_template': 'http://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'OpenStreetMap Humanitarian map style',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© OpenStreetMap contributors, Humanitarian OSM Team',
            'license_url': 'https://www.openstreetmap.org/copyright',
            'data_source': 'OpenStreetMap'
        },
        'OpenTopoMap.Contour': {
            'url_template': 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'OpenTopoMap topographic map with contours',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© OpenTopoMap (CC-BY-SA), © OpenStreetMap contributors',
            'license_url': 'https://opentopomap.org/about',
            'data_source': 'OpenStreetMap/SRTM'
        },
        'Esri.Hillshade': {
            'url_template': 'https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Esri World Hillshade',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': 'Source: Esri',
            'license_url': 'https://www.esri.com/en-us/legal/terms/full-master-agreement',
            'data_source': 'Esri'
        },
        'Bing.Aerial': {
            'url_template': 'http://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1',
            'url_type': 'quadkey',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Bing aerial imagery (quadkey tiles)',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Microsoft Bing',
            'license_url': 'https://www.microsoft.com/en-us/maps/product',
            'data_source': 'Bing'
        },
        'Google.Satellite': {
            'url_template': 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Google satellite imagery',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Google',
            'license_url': 'https://www.google.com/permissions/geoguidelines/',
            'data_source': 'Google'
        },
        'Google.Streets': {
            'url_template': 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Google streets map',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Google',
            'license_url': 'https://www.google.com/permissions/geoguidelines/',
            'data_source': 'Google'
        },
        'Amap.Satellite': {
            'url_template': 'https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Amap (Gaode) satellite imagery',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Amap (AutoNavi)',
            'license_url': 'https://lbs.amap.com/pages/terms/',
            'data_source': 'Amap/AutoNavi'
        },
        'Amap.Road': {
            'url_template': 'https://webst01.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Amap (Gaode) road map',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Amap (AutoNavi)',
            'license_url': 'https://lbs.amap.com/pages/terms/',
            'data_source': 'Amap/AutoNavi'
        },
        'Amap.Scene': {
            'url_template': 'http://wprd04.is.autonavi.com/appmaptile?lang=zh_cn&size=1&style=7&x={x}&y={y}&z={z}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Amap (Gaode) scene map (Chinese labels)',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Amap (AutoNavi)',
            'license_url': 'https://lbs.amap.com/pages/terms/',
            'data_source': 'Amap/AutoNavi'
        },
        'Amap.Vector': {
            'url_template': 'https://webrd04.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Amap (Gaode) vector map (Chinese labels)',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Amap (AutoNavi)',
            'license_url': 'https://lbs.amap.com/pages/terms/',
            'data_source': 'Amap/AutoNavi'
        },
        'Tencent.Terrain': {
            'url_template': 'https://rt0.map.gtimg.com/realtimerender?z={z}&x={x}&y={y}&type=vector&style=8',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Tencent terrain map',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Tencent Maps',
            'license_url': 'https://lbs.qq.com/terms.html',
            'data_source': 'Tencent'
        },
        'Tianditu.Vector': {
            'url_template': 'https://t0.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk={api_key}',
            'tile_size': 256,
            'requires_api_key': True,
            'api_env': 'TIANDITU_TOKEN',
            'special_handling': None,
            'description': 'Tianditu vector map (requires a free tk token from https://console.tianditu.gov.cn/api/key)',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Tianditu',
            'license_url': 'https://www.tianditu.gov.cn/',
            'data_source': 'Tianditu',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.tianditu.gov.cn/'
            }
        },
        'MapyCz.Outdoor': {
            'url_template': 'https://mapserver.mapy.cz/turist-m/{z}-{x}-{y}',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Mapy.cz outdoor topographic map',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Mapy.cz, © Seznam.cz',
            'license_url': 'https://mapy.cz/',
            'data_source': 'Mapy.cz'
        },
        'Wikimedia': {
            'url_template': 'https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png',
            'tile_size': 256,
            'requires_api_key': False,
            'special_handling': None,
            'description': 'Wikimedia Maps (OSM international style)',
            'min_zoom': 0,
            'max_zoom': 18,
            'attribution': '© Wikimedia Maps, © OpenStreetMap contributors',
            'license_url': 'https://www.openstreetmap.org/copyright',
            'data_source': 'OpenStreetMap'
        }
    }

    def __init__(
        self,
        provider: str,
        api_key: Optional[str] = None,
        check_accessibility: bool = False,
        **kwargs,
    ):
        """
        Initialize a RasterTileServer instance.

        Args:
            provider: Provider name (e.g., 'Esri.Terrain', 'Stadia.StamenTerrain')
            api_key: Optional API key for providers that require authentication.
                    Falls back to environment variable if not provided.
                check_accessibility: If True, probe the provider during construction.
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

        # Resolve backward-compatible provider aliases (e.g., 'OSM' -> 'OSM.Standard').
        provider = self._PROVIDER_ALIASES.get(provider, provider)

        requires_api_key = self._PROVIDERS.get(provider, {}).get('requires_api_key', False)

        if requires_api_key:
            if api_key is None:
                api_key = self._REGISTERED_API_KEYS.get(provider)

            if api_key is None:
                env_key = self._PROVIDERS[provider].get('api_env')
                if env_key:
                    api_key = os.environ.get(env_key)

            if api_key is None:
                warnings.warn(
                    f"Provider '{provider}' requires an API key. Provide it via api_key parameter or {self._PROVIDERS[provider].get('api_env')} environment variable.",
                    UserWarning,
                    stacklevel=2,
                )
                super().__init__(provider, api_key=None)
                self.is_accessible = False
                return

        super().__init__(provider, api_key=api_key)

        self.is_accessible = self.check_accessibility() if check_accessibility else True
        if self.is_accessible is False:
            warnings.warn(
                f"Tile server '{self.provider}' is not accessible. The instance was created but tile requests may fail.",
                UserWarning,
                stacklevel=2,
            )

    def check_accessibility(self, timeout: float = 10.0, z: int = 0, x: int = 0, y: int = 0) -> bool:
        """Check whether the configured tile endpoint responds within a timeout."""
        if requests is None:
            warnings.warn(
                "Tile accessibility check could not run because the 'requests' package is unavailable.",
                UserWarning,
            )
            return False

        url = self._build_tile_url(z, x, y)
        try:
            response = requests.get(url, headers=self._get_request_headers(), timeout=timeout)
        except Exception as exc:  # pragma: no cover - depends on network conditions
            warnings.warn(
                f"Tile server '{self.provider}' is not accessible at {url}: {exc}",
                UserWarning,
                stacklevel=2,
            )
            return False

        if response.status_code in (200, 204, 206):
            return True

        warnings.warn(
            f"Tile server '{self.provider}' is not accessible. HTTP {response.status_code} from {url}.",
            UserWarning,
            stacklevel=2,
        )
        return False

    def _build_tile_url(self, z: int, x: int, y: int) -> str:
        """Format the configured URL template for a tile.

        Extends the base implementation to support quadkey-style providers
        (e.g., Bing) whose URL templates use a `{q}` placeholder instead of
        `{z}`/`{x}`/`{y}`.
        """
        if self._config.get('url_type') == 'quadkey':
            quadkey = self._to_quadkey(x, y, z)
            return self.get_url_template().format(q=quadkey)
        return super()._build_tile_url(z, x, y)

    @staticmethod
    def _to_quadkey(x: int, y: int, z: int) -> str:
        """Convert tile coordinates to a Bing Maps quadkey string."""
        digits = []
        for i in range(z, 0, -1):
            digit = 0
            mask = 1 << (i - 1)
            if x & mask:
                digit += 1
            if y & mask:
                digit += 2
            digits.append(str(digit))
        return ''.join(digits)

    def _normalize_tile_image(self, img: 'Image.Image', *, fallback_size: Optional[Tuple[int, int]] = None) -> 'Image.Image':
        """Return a valid image tile even when a provider sends a zero-sized or malformed payload."""
        target_size = fallback_size or (self.tile_size, self.tile_size)

        if img is None:
            warnings.warn(
                "Tile payload was missing; creating a transparent fallback tile at the expected tile size instead of a zero-sized image.",
                UserWarning,
                stacklevel=2,
            )
            return Image.new('RGBA', target_size, (0, 0, 0, 0))

        try:
            width, height = img.size
        except Exception:
            width, height = 0, 0

        if width <= 0 or height <= 0:
            warnings.warn(
                "Tile payload had a non-positive size; creating a transparent fallback tile at the expected tile size instead of a zero-sized image.",
                UserWarning,
                stacklevel=2,
            )
            return Image.new('RGBA', target_size, (0, 0, 0, 0))

        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        if img.size != target_size:
            warnings.warn(
                f"Tile payload size {img.size} did not match the expected tile size {target_size}; resizing to the expected tile dimensions before returning it.",
                UserWarning,
                stacklevel=2,
            )
            img = img.resize(target_size, resample=Image.NEAREST)

        if self._config.get('special_handling'):
            img = self._apply_special_handling(img)

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
        response = requests.get(url, headers=self._get_request_headers())

        if response.status_code == 200:
            try:
                img = Image.open(BytesIO(response.content))
                img.load()
            except Exception:
                warnings.warn(
                    f"Tile fetch from {self.provider} at z={z}, x={x}, y={y} could not be decoded; returning a transparent fallback tile at the expected size.",
                    UserWarning,
                    stacklevel=2,
                )
                return self._normalize_tile_image(None)

            return self._normalize_tile_image(img)
        else:
            raise Exception(
                f"Failed to fetch tile from {self.provider}: "
                f"HTTP {response.status_code} - {url}"
            )
        
    def provider_y(self, tile_y, tile_z):
        tms_y_flip = self._config.get('tms_y_flip', False)
        if tms_y_flip:
            return (1 << tile_z) - 1 - tile_y
        return tile_y
    
    def fetch_tiles_for_extent(
        self,
        extent: List[float],
        zoom_level: Optional[int] = None,
        supersample: int = 0,
        resample: bool = True,
        resample_method: str = 'lanczos',
        output_size: Optional[Tuple[int, int]] = None,
        output_dpi: int = 96,
        quality_preference: str = 'balanced'
    ) -> np.ndarray:
        """
        Fetch and combine all tiles needed to cover the specified extent.

        Args:
            extent: [minx, maxx, miny, maxy] in longitude/latitude (degrees)
            zoom_level: Optional tile zoom level. If omitted, the function chooses
                an appropriate zoom level automatically using the current extent and
                output requirements.
            supersample: Super-sampling level (0=off, 1=fetch 2x zoom and downsample,
                        2=fetch 4x zoom). Higher values provide better quality but
                        require downloading 4^supersample more tiles.
            resample: Apply high-quality resampling filter for smooth appearance
            resample_method: Resampling method - 'lanczos' (best), 'bicubic', 'bilinear', 'nearest'
            output_size: Optional output image size used when deriving a zoom level.
            output_dpi: DPI used when deriving a zoom level.
            quality_preference: 'fast', 'balanced', or 'quality' used when picking a zoom.

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
            >>> # Let the library pick the zoom automatically
            >>> image_array = server.fetch_tiles_for_extent(extent)
            >>> # High quality with super-sampling (recommended)
            >>> image_array = server.fetch_tiles_for_extent(
            ...     extent, zoom_level=12, supersample=1, resample=True
            ... )
        """
        if zoom_level is None:
            if output_size is None:
                output_size = (1200, 1200)
            zoom_level = self.suggest_optimal_zoom(
                extent,
                output_dpi=output_dpi,
                output_size=output_size,
                quality_preference=quality_preference,
            )

        # Validate and adjust zoom levels if needed
        fetch_zoom, supersample = self._validate_zoom_level(zoom_level, supersample)

        minx, maxx, miny, maxy = extent
        x_min, y_min, x_max, y_max = self.extent_to_tile_indices(extent, fetch_zoom)

        # Fetch tiles
        tiles = []
        for y in range(y_min, y_max + 1):
            row = []
            for x in range(x_min, x_max + 1):
                provider_y = self.provider_y(y, fetch_zoom)
                tile = self.fetch_tile(fetch_zoom, x, provider_y)
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
            target_width = max(1, (original_x_max - original_x_min + 1) * self.tile_size)
            target_height = max(1, (original_y_max - original_y_min + 1) * self.tile_size)

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

    def fetch_manual_basemap(
        self,
        extent: List[float],
        zoom_level: Optional[int] = None,
        supersample: int = 0,
        resample: bool = True,
        resample_method: str = 'lanczos',
        output_size: Optional[Tuple[int, int]] = None,
        output_dpi: int = 96,
        quality_preference: str = 'balanced',
    ) -> 'ManualBasemap':
        """Fetch + stitch tiles manually and return everything needed for imshow.

        Fully manual alternative to cartopy's ``add_image`` / ``image_for_domain``.
        Tiles are fetched once and stitched north-at-top, and the Web Mercator extent
        is derived directly from the tile grid so it always lines up with the returned
        image (no tile-shifting artifacts).

        Args:
            extent: ``[minx, maxx, miny, maxy]`` in longitude/latitude (degrees).
            zoom_level: Tile zoom level; auto-selected via ``suggest_optimal_zoom``
                when omitted.
            supersample: Super-sampling level (0=off) forwarded to
                ``fetch_tiles_for_extent``.
            resample: Apply a smoothing filter (forwarded to ``fetch_tiles_for_extent``).
            resample_method: Resampling filter name ('lanczos', 'bicubic', ...).
            output_size: Output size used when auto-selecting a zoom level.
            output_dpi: DPI used when auto-selecting a zoom level.
            quality_preference: 'fast', 'balanced', or 'quality' for auto-zoom.

        Returns:
            ManualBasemap: ``(image, extent, crs, origin, attribution)``.

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> basemap = server.fetch_manual_basemap([minx, maxx, miny, maxy], zoom_level=10)
            >>> ax.imshow(basemap.image, extent=basemap.extent,
            ...           origin=basemap.origin, transform=basemap.crs)
        """
        if zoom_level is None:
            zoom_level = self.suggest_optimal_zoom(
                extent,
                output_dpi=output_dpi,
                output_size=output_size,
                quality_preference=quality_preference,
            )

        # Stitch the tiles manually (single fetch, north-at-top image).
        image = self.fetch_tiles_for_extent(
            extent,
            zoom_level,
            supersample=supersample,
            resample=resample,
            resample_method=resample_method,
        )

        # Derive the Web Mercator extent from the base-zoom tile grid so it matches
        # the stitched image exactly (supersample only changes resolution, not extent).
        x_min, y_min, x_max, y_max = self.extent_to_tile_indices(extent, zoom_level)
        left, _, _, top = self._calculate_tile_extent_web_mercator(x_min, y_min, zoom_level)
        _, right, bottom, _ = self._calculate_tile_extent_web_mercator(x_max, y_max, zoom_level)
        mercator_extent = [left, right, bottom, top]

        return ManualBasemap(
            image=image,
            extent=mercator_extent,
            crs=ccrs.Mercator(),
            origin='upper',
            attribution=self.get_license_info(),
        )

    def add_basemap(
        self,
        ax,
        extent: List[float],
        zoom_level: Optional[int] = None,
        alpha: float = 1.0,
        supersample: int = 0,
        zorder: Optional[int] = None,
        **fetch_kwargs,
    ) -> 'ManualBasemap':
        """Render this provider's tiles on a cartopy axes using manual imshow.

        Friendly wrapper around :meth:`fetch_manual_basemap` that performs the
        ``ax.imshow(...)`` call with the correct extent/transform/origin, avoiding
        cartopy's ``add_image`` (which can introduce tile-shifting artifacts). The
        resulting :class:`ManualBasemap` is returned so callers can read
        ``.attribution`` for license text.

        Args:
            ax: A cartopy GeoAxes to draw on.
            extent: ``[minx, maxx, miny, maxy]`` in longitude/latitude (degrees).
            zoom_level: Tile zoom level; auto-selected when omitted.
            alpha: Opacity for the basemap layer.
            supersample: Super-sampling level for higher quality.
            zorder: Optional matplotlib zorder for the image.
            **fetch_kwargs: Extra keyword arguments forwarded to
                ``fetch_manual_basemap`` (e.g., ``resample_method``).

        Returns:
            ManualBasemap: ``(image, extent, crs, origin, attribution)``.

        Example:
            >>> server = RasterTileServer('Esri.Terrain')
            >>> basemap = server.add_basemap(ax, [minx, maxx, miny, maxy], 10, alpha=0.9)
            >>> print(basemap.attribution)
        """
        result = self.fetch_manual_basemap(
            extent, zoom_level, supersample=supersample, **fetch_kwargs
        )
        imshow_kwargs = {}
        if zorder is not None:
            imshow_kwargs['zorder'] = zorder
        ax.imshow(
            result.image,
            extent=result.extent,
            origin=result.origin,
            transform=result.crs,
            alpha=alpha,
            **imshow_kwargs,
        )
        return result

    def get_cartopy_source(self, supersample: int = 0, 
                           resample_method: str = 'lanczos'
                           ) -> cimgt.GoogleTiles:
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

            def get_image(self, tile):
                x, y, z = tile                
                def _safe_extent_for_tile(tile_x, tile_y, tile_z):
                    # Cartopy's merge uses exact equality for adjacent boundaries.
                    # Quantize the shared grid edges so floating-point roundoff does
                    # not create an extra coordinate column or row.
                    extent = BaseTileServer._calculate_tile_extent_web_mercator(
                        tile_x, tile_y, tile_z
                    )                   
                    return tuple(round(value, 6) for value in extent)

                extent = _safe_extent_for_tile(x, y, z)
                #print('extent before', extent)
                max_zoom = config.get('max_zoom', 18)
                if z > max_zoom:
                    warnings.warn(
                        f"Cartopy requested zoom {z} for {provider}, but the provider maximum is {max_zoom}; using a transparent tile.",
                        UserWarning,
                        stacklevel=2,
                    )
                    return Image.new(
                        'RGBA',
                        (parent_instance.tile_size, parent_instance.tile_size),
                        (0, 0, 0, 0),
                    ), extent, 'lower'

            
                # If no supersample requested, fetch directly with proper headers
                # (the base class fetches via urllib without a User-Agent, which
                # some providers such as Tianditu reject with HTTP 418)
                if not supersample or supersample <= 0:
                    fetch_y = parent_instance.provider_y(y, z)   # apply conditional flip
                    try:
                        img = parent_instance.fetch_tile(z, x, fetch_y)
                    except Exception as exc:
                        warnings.warn(
                            f"Tile fetch failed for {provider} at z={z}, x={x}, y={fetch_y}; using a transparent fallback tile: {exc}",
                            UserWarning,
                            stacklevel=2,
                        )
                        img = Image.new(
                            'RGBA',
                            (parent_instance.tile_size, parent_instance.tile_size),
                            (0, 0, 0, 0),
                        )
                    img = parent_instance._normalize_tile_image(img)
                    if img.size[0] <= 0 or img.size[1] <= 0:
                        img = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))
                    extent = _safe_extent_for_tile(x, y, z)
                    #print('extent after', extent)
                    return img, extent, 'lower'

                # Compute actual supersample level respecting provider max_zoom
                fetch_z = z + supersample
                max_zoom = config.get('max_zoom', 18)
                actual_supersample = supersample
                if fetch_z > max_zoom:
                    actual_supersample = max_zoom - z
                    fetch_z = max_zoom

                if actual_supersample <= 0:
                    fetch_y = parent_instance.provider_y(y, z)
                    try:
                        img = parent_instance.fetch_tile(z, x, fetch_y)
                    except Exception as exc:
                        warnings.warn(
                            f"Tile fetch failed for {provider} at z={z}, x={x}, y={fetch_y}; using a transparent fallback tile: {exc}",
                            UserWarning,
                            stacklevel=2,
                        )
                        img = Image.new(
                            'RGBA',
                            (parent_instance.tile_size, parent_instance.tile_size),
                            (0, 0, 0, 0),
                        )
                    img = parent_instance._normalize_tile_image(img)
                    if img.size[0] <= 0 or img.size[1] <= 0:
                        img = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))
                    extent = _safe_extent_for_tile(x, y, z)
                    print('extent after', extent)
                    return img, extent, 'lower'

                scale = 2 ** actual_supersample

                # Fetch all high-res tiles and ensure RGBA
                tiles = []
                for dy in range(scale):
                    row = []
                    for dx in range(scale):
                        fetch_x = x * scale + dx
                        fetch_y = parent_instance.provider_y(y * scale + dy, fetch_z)
                        try:
                            high_res_tile = parent_instance.fetch_tile(fetch_z, fetch_x, fetch_y)
                            high_res_tile = parent_instance._normalize_tile_image(high_res_tile)
                            if high_res_tile.size[0] <= 0 or high_res_tile.size[1] <= 0:
                                high_res_tile = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))
                            row.append(high_res_tile)
                        except Exception:
                            warnings.warn(
                                f"Supersample tile fetch failed for {provider} at z={fetch_z}, x={fetch_x}, y={fetch_y}; inserting a transparent fallback tile at the expected size.",
                                UserWarning,
                                stacklevel=2,
                            )
                            blank = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))
                            row.append(blank)
                    tiles.append(row)

                if tiles and tiles[0]:
                    actual_tile_size = tiles[0][0].size[0]
                    combined_img = parent_instance.combine_tiles(tiles, actual_tile_size)
                else:
                    combined_img = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))

                if combined_img.size[0] <= 0 or combined_img.size[1] <= 0:
                    warnings.warn(
                        f"Supersample tile assembly for {provider} at z={z}, x={x}, y={y} produced a zero-sized image; replacing it with a transparent fallback tile.",
                        UserWarning,
                        stacklevel=2,
                    )
                    combined_img = Image.new('RGBA', (parent_instance.tile_size, parent_instance.tile_size), (0, 0, 0, 0))

                # Downsample to target tile size
                target_size = max(1, parent_instance.tile_size)
                combined_img = combined_img.resize((target_size, target_size), resample=resample_filter)

                # Compute tile extent geometrically (no network fetch)
                extent = _safe_extent_for_tile(x, y, z)
                print('extent after', extent)
                return combined_img, extent, 'lower'

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

    def get_default_zoom(
        self,
        extent: List[float],
        output_dpi: int = 150,
        output_size: Optional[Tuple[int, int]] = None,
        quality_preference: str = 'balanced'
    ) -> int:
        """Return the default auto-selected zoom for a given extent.

        This is the convenience method to use when you want the server to choose a
        sensible zoom level with minimal configuration. Only the extent is required;
        the output size, DPI and quality preference fall back to reasonable defaults.
        """
        if output_size is None:
            output_size = (1200, 1200)
        return self.suggest_optimal_zoom(
            extent,
            output_dpi=output_dpi,
            output_size=output_size,
            quality_preference=quality_preference,
        )

    def suggest_optimal_zoom(
        self,
        extent: List[float],
        output_dpi: int = 150,
        output_size: Optional[Tuple[int, int]] = None,
        quality_preference: str = 'balanced'
    ) -> int:
        """
        Suggest optimal zoom level based on output requirements and quality preference.

        If output_size is not provided, a default 1200x1200 output is assumed.
        """
        if output_size is None:
            output_size = (1200, 1200)

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

    def _get_request_headers(self) -> Dict[str, str]:
        """Return HTTP headers used for tile requests.

        Some providers (e.g., Tianditu) reject requests carrying the default
        Python User-Agent with HTTP 418. A browser-like User-Agent is sent by
        default, and providers may supply custom 'headers' in their config.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36'
        }
        headers.update(self._config.get('headers') or {})
        return headers

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
            (1.0 - math.asinh(math.tan(lat_rad)) / math.pi)
            * (n/2.0)
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

        Empty rows or partially missing tiles can occur when a requested tile is
        unavailable or fetch fails. Treat those as transparent placeholders to
        keep the output image dimensions valid and avoid NumPy broadcast errors.
        """
        tile_size = max(1, int(tile_size))
        if not tiles:
            warnings.warn(
                "No valid tiles were available for the requested extent; combining tiles produced an empty grid. "
                "Creating a transparent fallback image at the expected tile size to avoid a zero-dimension Cartopy image.",
                UserWarning,
                stacklevel=2,
            )
            return Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))

        max_cols = max((len(row) for row in tiles), default=0)
        if max_cols <= 0:
            warnings.warn(
                "Tile grid had no columns after filtering empty rows; creating a transparent fallback image at the expected tile size to avoid a zero-dimension Cartopy image.",
                UserWarning,
                stacklevel=2,
            )
            return Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))

        width = max(1, max_cols * tile_size)
        height = max(1, len(tiles) * tile_size)
        if width <= 0 or height <= 0:
            warnings.warn(
                "Tile grid width/height collapsed to zero while combining tiles; creating a transparent fallback image to avoid a zero-dimension Cartopy array.",
                UserWarning,
                stacklevel=2,
            )
            return Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))

        combined_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

        for row_index, row in enumerate(tiles):
            for col_index in range(max_cols):
                tile = row[col_index] if col_index < len(row) else None
                if tile is None:
                    warnings.warn(
                        f"Missing tile at grid position ({row_index}, {col_index}) while combining tiles; inserting a transparent fallback tile of size {tile_size}x{tile_size}.",
                        UserWarning,
                        stacklevel=2,
                    )
                    tile = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
                combined_img.paste(tile, (col_index * tile_size, row_index * tile_size))

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



