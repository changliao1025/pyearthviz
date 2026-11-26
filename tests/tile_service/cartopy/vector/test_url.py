"""Test Cartopy custom tile URL implementation."""

import os

import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import matplotlib.pyplot as plt

from pyearthviz.map import RasterTileServer

url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
TEST_EXTENT = [97.8125, 101.19193115234378, 36.295833333333356, 38.31723395453561]


class ExactQGISTiles(cimgt.GoogleTiles):
    def _image_url(self, tile):
        x, y, z = tile

        return url.format(x=x, y=y, z=z)


def test_exact_qgis_tiles_url():
    """Verify that ExactQGISTiles formats the URL correctly."""
    tiles = ExactQGISTiles()
    tile = (10, 20, 5)  # x=10, y=20, z=5
    formatted_url = tiles._image_url(tile)
    expected_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/5/20/10"
    assert formatted_url == expected_url


def test_esri_world_topo_url_template():
    """Verify RasterTileServer Esri.WorldTopo URL template matches."""
    server = RasterTileServer("Esri.WorldTopo")
    assert server.get_url_template() == url


if __name__ == "__main__":
    try:
        import geopandas as gpd

        sFilename_basin_boundary = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "data",
                "basin_boundary_qinghaihu.geojson",
            )
        )
        sFilename_lake_boundary = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "data",
                "lake_boundary_qinghaihu.geojson",
            )
        )

        tiles = ExactQGISTiles()

        fig, ax = plt.subplots(
            figsize=(10, 10), subplot_kw={"projection": ccrs.PlateCarree()}
        )

        ax.add_image(tiles, 9)
        boundary = gpd.read_file(sFilename_lake_boundary)

        ax.add_geometries(
            boundary.geometry,
            crs=ccrs.PlateCarree(),
            edgecolor="blue",
            facecolor="none",
            linewidth=2.0,
        )
        boundary = gpd.read_file(sFilename_basin_boundary)
        ax.add_geometries(
            boundary.geometry,
            crs=ccrs.PlateCarree(),
            edgecolor="red",
            facecolor="none",
            linewidth=2.0,
        )
        ax.set_extent(TEST_EXTENT, crs=ccrs.PlateCarree())

        plt.show()
    except ImportError:
        print("geopandas not installed; skipping interactive visual plot.")
