###########################
Frequently Asked Questions
###########################

Installation Issues
===================

1. Why can't conda create my environment?

   Try turning off your VPN or configuring it to bypass conda channels.

2. Why does GDAL import fail?

   GDAL can be challenging to install. We recommend:

   - Use conda instead of pip: ``conda install -c conda-forge gdal``
   - Use the conda-forge channel which has better-maintained builds
   - Install pyearthviz via conda to handle dependencies automatically

3. I'm getting PROJ-related errors (https://github.com/OSGeo/gdal/issues/1546)

   Make sure PROJ_LIB is correctly configured. PyEarthViz depends on GDAL, which uses PROJ.

   On Linux or Mac, set in ``.bash_profile`` or ``.bashrc``::

       # Anaconda
       export PROJ_LIB=$HOME/.conda/envs/pyearthviz-env/share/proj

       # Miniconda
       export PROJ_LIB=/opt/miniconda3/envs/pyearthviz-env/share/proj

Visualization Issues
====================

4. I'm getting errors using plotting functions

   Common issues and solutions:

   - **GeoAxesSubplot errors**: Ensure cartopy version 0.21.0+ is installed
   - **Matplotlib compatibility**: Try matplotlib 3.5.2 if you encounter rendering issues
   - **Missing basemap tiles**: Check your internet connection for online tile services
   - **Projection errors**: Verify your data's CRS matches the map projection

5. My map looks distorted or incorrect

   - Check that your data's coordinate reference system (CRS) is correctly specified
   - Ensure your data bounds are appropriate for the chosen projection
   - Use ``geopandas`` or ``pyearth`` to verify and reproject your data if needed

6. Color schemes don't look right in my plots

   - PyEarthViz provides several color utilities in the ``color`` module
   - Check if your data range matches the colormap normalization
   - Consider using diverging colormaps for data with meaningful center points

7. How do I use online tile servers for basemaps?

   PyEarthViz supports various tile servers through the ``map`` module. See the TileServer_Guide for details on configuring and using online basemaps.

Performance Issues
==================

8. Plots are rendering slowly

   - For large raster datasets, consider downsampling or tiling
   - Use appropriate DPI settings for your output format
   - Consider using simpler projections for faster rendering

9. Memory errors when plotting large datasets

   - Process data in chunks
   - Use appropriate data types (e.g., float32 instead of float64)
   - Consider using dask for out-of-core computation
