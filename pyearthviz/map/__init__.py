"""
PyEarthViz Map Module

Provides tools for creating maps and visualizing geospatial data.

Main Components:
- RasterTileServer: Unified interface for accessing map tile servers
- Map plotting functions for various data types (raster, vector, MPAS mesh, etc.)
"""

from pyearthviz.map.raster_map_servers import RasterTileServer

__all__ = ['RasterTileServer']
