#############
Visualization
#############

PyEarthViz provides comprehensive 2D visualization tools for geospatial and scientific data.

************
Color
************

Utilities for creating and managing color schemes:

- ``create_diverge_rgb_color_hex`` - Generate diverging color palettes
- ``create_qualitative_rgb_color_hex`` - Generate distinct colors for categories
- ``choose_n_color`` - Select N evenly-spaced colors
- ``pick_colormap`` - Choose appropriate colormaps for data types

************
Formatter
************

Custom formatters for axes and labels to enhance plot readability.

*********
Barplot
*********

Bar chart visualizations:

- ``barplot_data`` - Standard bar plots
- ``barplot_data_stacked`` - Stacked bar charts for composition
- ``barplot_data_with_reference`` - Bar plots with reference lines

************
Boxplot
************

Distribution comparison tools:

- ``boxplot_data`` - Standard box plots
- ``boxplot_data_with_reference`` - Box plots with benchmark lines

************
Histogram
************

Statistical distribution visualization:

- ``histogram_plot`` - Standard histograms
- ``cdf_plot`` - Cumulative distribution functions
- ``cdf_plot_multiple_data`` - Compare multiple distributions
- ``histogram_w_cdf_plot`` - Combined histogram with CDF overlay

************
Ladder plot
************

Stepped visualization for discrete temporal data:

- ``ladder_plot_xy_data`` - Create ladder plots from XY data

************
Map
************

Geospatial visualization tools:

Raster Mapping
==============

- ``map_raster_data`` - Visualize raster arrays
- ``map_raster_file`` - Plot GeoTIFF and other raster files
- ``map_raster_data_dc`` - Raster visualization with datacube support
- ``map_raster_file_dc`` - File-based raster plotting with datacube
- ``map_netcdf_file`` - NetCDF file visualization

Vector Mapping
==============

- ``map_vector_point_file`` - Plot point features
- ``map_vector_polyline_file`` - Visualize line features
- ``map_vector_polygon_file`` - Display polygon features
- ``map_multiple_vector_files`` - Combine multiple vector layers
- ``merge_vector_polygon_files`` - Merge and visualize polygon datasets

Map Utilities
=============

- ``map_study_area`` - Create publication-ready study area maps
- ``zebra_frame`` - Add professional zebra-striped coordinate frames
- ``base_tile_server`` - Base tile server configuration
- ``raster_map_servers`` - Raster basemap services
- ``vector_map_servers`` - Vector basemap services

************
Ridge plot
************

Distribution visualization for multiple groups:

- ``ridgeplot_data_density`` - Overlapping density plots for comparing distributions

************
Scatter plot
************

Advanced scatter plot functions:

- ``scatter_plot_data`` - Basic scatter plots
- ``scatter_plot_multiple_data`` - Multiple dataset visualization
- ``scatter_plot_data_density`` - Color-coded point density
- ``scatter_plot_multiple_data_w_density`` - Multi-dataset with density
- ``scatter_lowess`` - LOWESS smoothing with scatter plots

************
Surface plot
************

Surface visualization tools (under development).

************
Time series
************

Specialized temporal data visualization:

Basic Time Series
=================

- ``plot_time_series_data`` - Standard time series plots
- ``plot_time_series_data_with_two_y_axis`` - Dual y-axis comparisons
- ``plot_time_series_data_w_variation`` - Mean with confidence intervals

Filled Time Series
==================

- ``plot_time_series_data_monthly_fill`` - Monthly aggregated displays
- ``plot_time_series_data_multiple_temporal_resolution_fill`` - Multi-resolution views
- ``plot3d_time_series_data_fill`` - 3D temporal visualizations

Time Series Analysis
====================

- ``plot_time_series_analysis`` - Decomposition and trend analysis

Zoom Features
=============

- ``plot_time_series_data_monthly_fill_with_zoom`` - Inset zoom windows

************
Animation
************

Create animated visualizations:

- ``animate_polygon_file`` - Animate changes in polygon geometries over time

************
XY Plotting
************

General-purpose XY data plotting utilities:

- ``plot_xy_data`` - Flexible XY plotting
- ``calculate_ticks_space`` - Optimal tick spacing
- ``create_line_style`` - Custom line style configurations
