"""Base tile server utilities and base class.

This module provides a small base class that centralizes common logic
shared by raster and vector tile server implementations in this package:
- provider registry handling and introspection
- API key resolution
- URL building for templated tile endpoints
- basic zoom-level validation (with optional supersample support)

Subclasses should define a `_PROVIDERS` class attribute describing
available providers and may extend behavior as needed.
"""
from typing import List, Optional, Dict, Any, Tuple
import os
import warnings
import math
import numpy as np
from osgeo import osr

try:
    from PIL import Image
except Exception:
    Image = None

from pyearth.gis.spatialref.convert_between_degree_and_meter import degree_to_meter


class BaseTileServer:
    """Minimal base class for tile server clients.

    Subclasses should set a class-level `_PROVIDERS` dict mapping provider
    names to configuration dictionaries.
    """

    _PROVIDERS: Dict[str, Dict[str, Any]] = {}

    def __init__(self, provider: str, api_key: Optional[str] = None) -> None:
        if provider not in self._PROVIDERS:
            available = ', '.join(self._PROVIDERS.keys())
            raise ValueError(f"Unknown provider '{provider}'. Available providers: {available}")

        self.provider = provider
        self._config = self._PROVIDERS[provider].copy()
        self.tile_size = self._config.get('tile_size')

        # API key resolution
        if self._config.get('requires_api_key'):
            if api_key:
                self.api_key = api_key
            else:
                env_key = self._config.get('api_env') or ("STADIA_API_KEY" if "Stadia" in provider else None)
                if env_key:
                    self.api_key = os.environ.get(env_key)
                    if not self.api_key:
                        warnings.warn(
                            f"Provider '{provider}' requires an API key. Provide it via api_key parameter or {env_key} environment variable.",
                            UserWarning,
                        )
                else:
                    self.api_key = None
        else:
            self.api_key = api_key

    # Instance methods

    def get_url_template(self) -> str:
        """Get the URL template for this provider.

        Returns:
            URL template string with placeholders for {z}, {x}, {y}, and optionally {api_key}
        """
        return self._config.get('url_template', '')

    def _build_tile_url(self, z: int, x: int, y: int) -> str:
        """Format the configured URL template for a tile.

        The provider config is expected to have a `url_template` entry that
        contains `{z}`, `{x}`, `{y}` and optionally `{api_key}` placeholders.
        """
        template = self.get_url_template()
        return template.format(z=z, x=x, y=y, api_key=self.api_key or '')




    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider='{self.provider}', tile_size={self.tile_size})"

    # Class methods

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Return a list of provider keys supported by this server class."""
        return list(cls._PROVIDERS.keys())

    @classmethod
    def get_provider_info(cls, provider: Optional[str] = None) -> Dict[str, Any]:
        """Return info for a single provider or for all providers.

        Raises ValueError if a requested provider is unknown.
        """
        if provider:
            if provider not in cls._PROVIDERS:
                raise ValueError(f"Unknown provider '{provider}'")
            return cls._PROVIDERS[provider].copy()
        return {k: v.copy() for k, v in cls._PROVIDERS.items()}

    # Static methods
    @staticmethod
    def calculate_scale_denominator(domain_boundary, image_size, dpi=96):
        """
        Calculates the scale denominator for a map based on the domain boundary and desired image size.
        """
        min_x, max_x, min_y, max_y = domain_boundary
        domain_width = max_x - min_x
        domain_height = max_y - min_y
        dLatitude_mean = (min_y + max_y) / 2.0
        meters_per_dgree = degree_to_meter(1.0, dLatitude_mean)
        meters_to_inches = 39.3701
        image_width_in_inches = image_size[0] / dpi
        image_height_in_inches = image_size[1] / dpi

        scale_denominator = (
            np.max([domain_width, domain_height])
            * meters_per_dgree
            * meters_to_inches
            / np.max([image_width_in_inches, image_height_in_inches])
        )
        return scale_denominator


