# Plan: Unified Manual Basemap Interface (imshow, no `add_image`)

## Goal
Render raster basemap tiles **fully manually** (fetch tiles → stitch → `ax.imshow`)
instead of cartopy's `ax.add_image(...)` / `image_for_domain(...)`, which cause
**tile-shifting artifacts** (notably for `@2x` / 512px providers such as Stadia & Carto).
Expose this through a **friendly, unified interface** on `RasterTileServer` so every
provider (including OSM) uses one code path.

## Problem with the current state
- `map_vector_polygon_file.py` still calls `pTiles.image_for_domain(...)` to get the
  extent. That triggers a **second, wasted tile fetch** through cartopy's merge path
  (the very path we are trying to avoid), and mixes cartopy logic back in.
- Two divergent branches exist: a special cartopy `OSM()` branch vs. the
  `RasterTileServer` branch — not unified.
- The manual fetch/stitch/extent logic would be duplicated in every map function if
  inlined, so it belongs on the tile-server class.

## Design: one unified, manual API on `RasterTileServer`

### 1. Result container `ManualBasemap` (NamedTuple)
Lightweight, supports both attribute and tuple access:
```
ManualBasemap(image, extent, crs, origin, attribution)
```
- `image`: `np.ndarray` RGBA, north-at-top.
- `extent`: `[left, right, bottom, top]` in **Web Mercator (EPSG:3857)**, computed from
  the tile grid (no cartopy).
- `crs`: `ccrs.Mercator()` — the `transform` to pass to `imshow`.
- `origin`: `'upper'` (matches the north-at-top stitched image).
- `attribution`: license string from `get_license_info()`.

### 2. `fetch_manual_basemap(extent, zoom_level=None, supersample=0, resample=True, resample_method='lanczos', ...) -> ManualBasemap`
Pure data method (no plotting). Steps:
1. If `zoom_level is None`, auto-pick via existing `suggest_optimal_zoom(extent)`.
2. `image = self.fetch_tiles_for_extent(extent, zoom_level, supersample=..., resample=..., resample_method=...)`
   (reuses the already-tested fetch + stitch + special-handling + `provider_y` flip).
3. Compute the Mercator extent **manually** from the base-zoom tile grid:
   ```
   x_min, y_min, x_max, y_max = self.extent_to_tile_indices(extent, zoom_level)
   left,  _,    _,     top    = self._calculate_tile_extent_web_mercator(x_min, y_min, zoom_level)
   _,     right, bottom, _    = self._calculate_tile_extent_web_mercator(x_max, y_max, zoom_level)
   mercator_extent = [left, right, bottom, top]
   ```
   (Supersample only changes fetch resolution; the downsampled image maps back to the
   base-zoom grid, so this extent stays correct.)
4. Return `ManualBasemap(image, mercator_extent, ccrs.Mercator(), 'upper', self.get_license_info())`.

### 3. `add_basemap(ax, extent, zoom_level=None, alpha=1.0, supersample=0, zorder=None, **fetch_kwargs) -> ManualBasemap`
Friendly one-liner that renders and returns the result (so callers can read `.attribution`):
```
result = self.fetch_manual_basemap(extent, zoom_level, supersample=supersample, **fetch_kwargs)
ax.imshow(result.image, extent=result.extent, origin=result.origin,
          transform=result.crs, alpha=alpha, zorder=zorder)
return result
```
- Does **not** draw attribution text by default (the map function already collects and
  renders a single combined license box).

## File changes

### `pyearthviz/map/raster_map_servers.py`
- Add `import cartopy.crs as ccrs`.
- Define `ManualBasemap` NamedTuple (module level).
- Add `fetch_manual_basemap(...)` and `add_basemap(...)` methods to `RasterTileServer`.
- Keep `fetch_tiles_for_extent`, `get_cartopy_source`, `get_projected_extent` unchanged
  (still used by tests) — the new methods build on top of them.

### `pyearthviz/map/vector/map_vector_polygon_file.py`
- Replace the entire per-provider `if 'OSM' / else` block (currently using
  `image_for_domain` + `add_image`/manual imshow) with a single unified path:
  ```
  for i in range(nTile_provider):
      sBasemap_provider = aBasemap_provider_in[i]
      if sBasemap_provider == 'OSM':          # backward-compatible alias
          sBasemap_provider = 'OSM.Standard'
      pTile_service = RasterTileServer(sBasemap_provider)
      pBasemap = pTile_service.add_basemap(
          ax, aExtent, iBasemap_zoom_level, alpha=dAlpha - i * 0.1)
      aLicense_info_list.append(pBasemap.attribution)
  ```
- Remove the now-unused `from cartopy.io.img_tiles import OSM` import inside the branch
  and (if unused elsewhere) the top-level `OSM` import; drop `sgeom` usage that was only
  added for the cartopy `image_for_domain` path.
- Leave the existing combined-license text box logic (after the loop) as-is.

## Out of scope
- `vector_map_servers.py` and non-basemap map functions (they don't render raster tiles).
- Changing provider registry / URLs.

## Backward compatibility
- `get_cartopy_source()` and `fetch_tiles_for_extent()` remain (tests under
  `tests/tile_service/` keep working).
- `'OSM'` string still accepted via alias to `'OSM.Standard'`.

## Verification
1. Static: `python -c "import pyearthviz.map.vector.map_vector_polygon_file"` (no import errors).
2. Functional (network, key-less provider): render
   `data/lake_boundary_qinghaihu.geojson` with `aBasemap_provider_in=['Esri.Terrain']`
   to a PNG; confirm tiles are aligned (no half-tile shift) and license box shows.
3. Repeat with `['OSM']` to confirm the alias + unified path.

## Assumptions
- Web Mercator extent from `_calculate_tile_extent_web_mercator` is consistent with
  `ccrs.Mercator()` (both use ±20037508.34 m bounds) — matches cartopy tile-source CRS.
- The stitched image from `fetch_tiles_for_extent` is north-at-top → `origin='upper'`.
