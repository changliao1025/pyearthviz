### PyEarthViz

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6109987.svg)](https://doi.org/10.5281/zenodo.6109987)

A lightweight Python package for 2D visualization and plotting of geospatial and Earth science data.

**Note:** PyEarthViz is part of the **PyEarthSuite** ecosystem. The original PyEarth package has been restructured into several specialized packages to keep each package lightweight and focused:

- **[pyearth](https://github.com/changliao1025/pyearth)** - Core GIS operations, spatial toolbox, and system utilities
- **pyearthviz** (this package) - 2D visualization utilities
- **pyearthviz3d** - 3D visualization with GeoVista
- **pyearthriver** - River network graph algorithms and data structures
- **pyearthmesh** - Mesh generation and manipulation tools (currently not implemented)
- **pyearthhelp** - Helper utilities for data access (NWIS, NLDI, GSIM) and HPC operations

This modular approach allows you to install only what you need while maintaining the ability to use all packages together.

### About PyEarthViz

PyEarthViz is designed to be lightweight, versatile, and reliable for creating publication-quality 2D visualizations of geospatial and scientific data. It provides a comprehensive suite of plotting functions built on top of matplotlib and cartopy, with specialized tools for:

- Geographic mapping and spatial data visualization
- Time series analysis and plotting
- Statistical plots (scatter, histogram, box plots, etc.)
- Advanced plot types (ridge plots, ladder plots, animations)
- Customizable color schemes and styling

If you find this package useful, please cite it in your work.
You can also support it by [buying me a coffee](https://www.buymeacoffee.com/changliao) or sponsoring it on [GitHub](https://github.com/sponsors/changliao1025).

### Dependency

PyEarthViz depends on the following packages:

**Required:**
1. `numpy` - numerical computing
2. `matplotlib` - 2D plotting library
3. `cartopy` - geospatial data processing and mapping
4. `gdal` - geospatial data abstraction library
5. `pandas` - data manipulation and analysis
6. `scipy` - scientific computing
7. `statsmodels` - statistical modeling
8. `pyearth` - core GIS operations and spatial utilities

### Documentation

Please refer to the [documentation](https://pyearthviz.readthedocs.io) for details on how to get started using the PyEarthViz package.

### Installation

`PyEarthViz` depends on several packages, including GDAL and Cartopy, which can be challenging to install through `pip` alone. You are recommended to use `conda` to install dependencies:

```bash
# Install from conda (recommended)
conda install pyearthviz

# Or install from pip (requires GDAL and Cartopy pre-installed)
pip install pyearthviz
```

#### Building from Source

PyEarthViz uses modern `pyproject.toml` configuration. To build from source:

```bash
# Clone the repository
git clone https://github.com/changliao1025/pyearthviz.git
cd pyearthviz

# Install dependencies using conda
conda install numpy matplotlib cartopy gdal pandas scipy statsmodels

# Install pyearth (required dependency)
conda install pyearth

# Build and install (modern way)
pip install -e .

# Or build a distributable package
pip install build
python -m build
```

### Content

PyEarthViz provides specialized visualization functions organized into several categories:

#### 1. Map Module
Comprehensive geospatial visualization tools:
- **Raster mapping**: Visualize GeoTIFF, NetCDF, and other raster formats
- **Vector mapping**: Plot points, lines, and polygons with custom styling
- **Multi-layer maps**: Combine multiple vector datasets
- **Study area visualization**: Create publication-ready maps with custom projections
- **Animation**: Create animated visualizations of temporal geospatial data
- **Zebra frame**: Add professional zebra-striped coordinate frames

#### 2. Time Series Module
Specialized time series plotting functions:
- **Basic time series**: Single and multiple variable plotting
- **Temporal analysis**: Monthly aggregations, multi-resolution displays
- **Two y-axis plots**: Compare variables with different scales
- **Variation plots**: Display mean with confidence intervals or ranges
- **3D time series**: Three-dimensional temporal visualizations with fill
- **Zoom capabilities**: Create inset zoom windows for detailed views

#### 3. Scatter Module
Advanced scatter plot functions:
- **Basic scatter plots**: Single and multiple dataset visualization
- **Density scatter**: Color-coded point density for large datasets
- **LOWESS smoothing**: Local regression trend lines
- **Multi-dataset density**: Compare multiple datasets with density visualization

#### 4. Histogram Module
Statistical distribution visualization:
- **Histogram plots**: Standard and customized histograms
- **CDF plots**: Cumulative distribution functions
- **Combined plots**: Histogram with overlaid CDF
- **Multiple distributions**: Compare multiple datasets

#### 5. Box Plot Module
Distribution comparison tools:
- **Standard box plots**: Single and multiple variable comparisons
- **Reference lines**: Add benchmark or threshold lines
- **Grouped comparisons**: Compare distributions across categories

#### 6. Bar Plot Module
Categorical data visualization:
- **Standard bar plots**: Single and grouped bar charts
- **Stacked bar plots**: Show composition of categories
- **Reference comparisons**: Compare against baseline or target values

#### 7. Ridge Plot Module
Distribution visualization for multiple groups:
- **Density ridge plots**: Overlapping density plots for comparing distributions

#### 8. Ladder Plot Module
Specialized time series visualization:
- **Ladder plots**: Stepped visualization for discrete temporal data

#### 9. Animation Module
Create animated visualizations:
- **Polygon animations**: Animate changes in polygon geometries over time

#### 10. Color Module
Color scheme utilities:
- **Diverging colors**: Create diverging color schemes for highlighting differences
- **Qualitative colors**: Generate distinct colors for categorical data
- **Colormap selection**: Choose appropriate colormaps for different data types
- **N-color selection**: Generate N evenly-spaced colors

#### 11. Utility Functions
Supporting functions for all plot types:
- **Tick spacing**: Calculate optimal tick spacing for axes
- **Line styles**: Create custom line style configurations
- **Formatters**: Custom axis formatters for special data types
- **XY plotting**: General-purpose XY data plotting

### Related Packages in EarthSuite

PyEarthViz works seamlessly with other EarthSuite packages:

- **[pyearth](https://github.com/changliao1025/pyearth)** - Core GIS operations and spatial toolbox
- **[pyearthviz3d](https://github.com/changliao1025/pyearthviz3d)** - 3D globe visualization with GeoVista
- **[pyearthriver](https://github.com/changliao1025/pyearthriver)** - River network topology and graph algorithms
- **[pyearthmesh](https://github.com/changliao1025/pyearthmesh)** - Advanced mesh generation tools
- **[pyearthhelp](https://github.com/changliao1025/pyearthhelp)** - Data retrieval and HPC job management

### Acknowledgment

This research was supported as part of the Next Generation Ecosystem Experiments-Tropics, funded by the U.S. Department of Energy, Office of Science, Office of Biological and Environmental Research at Pacific Northwest National Laboratory. The study was also partly supported by U.S. Department of Energy Office of Science Biological and Environmental Research through the Earth and Environmental System Modeling program as part of the Energy Exascale Earth System Model (E3SM) project.

### License

Copyright © 2022, Battelle Memorial Institute

1. Battelle Memorial Institute (hereinafter Battelle) hereby grants permission to any person or entity lawfully obtaining a copy of this software and associated documentation files (hereinafter "the Software") to redistribute and use the Software in source and binary forms, with or without modification. Such person or entity may use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software and may permit others to do so, subject to the following conditions:

* Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimers.

* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

* Other than as used herein, neither the name Battelle Memorial Institute or Battelle may be used in any form whatsoever without the express written consent of Battelle.

2. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL BATTELLE OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

### References

If you make use of `PyEarthViz` in your work, please consider including a reference to the following:

* Chang Liao. (2022). PyEarth: A lightweight Python package for Earth science (Software). Zenodo. https://doi.org/10.5281/zenodo.6109987

PyEarthViz is supporting several research projects and publications, including:

* Liao et al., (2023). pyflowline: a mesh-independent river network generator for hydrologic models. Journal of Open Source Software, 8(91), 5446, https://doi.org/10.21105/joss.05446

* Liao. C. (2022). HexWatershed: a mesh independent flow direction model for hydrologic models (0.1.1). Zenodo. https://doi.org/10.5281/zenodo.6425881
