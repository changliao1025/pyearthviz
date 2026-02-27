# Plan: Update Documentation from PyEarth to PyEarthViz

## Overview
This plan outlines the necessary changes to update documentation and configuration files that were copied from the pyearth project to properly reflect the pyearthviz project.

## Context
PyEarthViz is part of the PyEarthSuite ecosystem, focusing specifically on 2D visualization utilities. It was extracted from the original PyEarth package to keep packages lightweight and focused. The documentation files were copied from PyEarth and need to be updated to reflect PyEarthViz's specific scope and functionality.

## Key Differences Between PyEarth and PyEarthViz

| Aspect | PyEarth | PyEarthViz |
|--------|---------|------------|
| **Scope** | Core GIS operations, spatial toolbox, system utilities | 2D visualization and plotting only |
| **Dependencies** | GDAL, pyproj, shapely, etc. | matplotlib, cartopy, pandas, scipy, statsmodels |
| **Module Structure** | gis, system, toolbox, visual | map, timeseries, scatter, histogram, color, etc. |
| **GitHub URL** | changliao1025/pyearth | changliao1025/pyearthviz |
| **ReadTheDocs** | pyearth.readthedocs.io | pyearthviz.readthedocs.io |

## Files to Update

### 1. ✅ environment.yml (Already Updated)
**Status:** Already updated to `pyearthviz-env` with correct dependencies

**Current state:**
- Name: `pyearthviz-env`
- Includes: numpy, pandas, scipy, gdal, matplotlib, cartopy, statsmodels, pyearth>=0.2.1

**Note:** The environment.yml correctly reflects pyearthviz dependencies.

---

### 2. docs/source/conf.py
**Priority:** HIGH - Critical for documentation build

**Changes needed:**
- **Line 64:** Change input_dir from `"../../pyearth"` to `"../../pyearthviz"`
- **Line 68:** Change breathe_projects key from `"pyearth"` to `"pyearthviz"`
- **Line 78:** Change breathe_default_project from `"pyearth"` to `"pyearthviz"`
- **Line 93:** Change project name from `"pyearth"` to `"pyearthviz"`
- **Line 94:** Copyright already correct (Pacific Northwest National Laboratory)
- **Line 231:** Change htmlhelp_basename from `"ReadtheDocsTemplatedoc"` to `"pyearthvizdoc"`
- **Lines 248-256:** Update latex_documents tuple to reflect PyEarthViz
- **Lines 283-291:** Update man_pages tuple to reflect PyEarthViz
- **Lines 302-312:** Update texinfo_documents tuple to reflect PyEarthViz

**Impact:** Critical - affects entire documentation build system

---

### 3. docs/source/index.rst
**Priority:** HIGH - Main documentation entry point

**Changes needed:**
- **Line 1:** Change from "pyearth documentation master file" to "pyearthviz documentation master file"
- **Line 6:** Change title from "Welcome to pyearth documentation!" to "Welcome to PyEarthViz documentation!"
- **Lines 9-19:** Rewrite the note section to reflect PyEarthViz's role in the ecosystem:
  - Change from explaining PyEarth's restructuring to explaining PyEarthViz's focus
  - List companion packages without implying they were split from PyEarthViz
- **Lines 23-31:** Update toctree entries:
  - Remove: `story`, `algorithm/gis/gis.rst`, `algorithm/system/system.rst`, `algorithm/toolbox/toolbox.rst`, `algorithm/api`
  - Add: `visual/visual.rst`, proper module documentation structure
  - Keep: `getting-started`, potentially add `faq`, `contribution`, `support`, `authors`

**Suggested new structure:**
```rst
.. pyearthviz documentation master file

Welcome to PyEarthViz documentation!
====================================

.. note::
   PyEarthViz is part of the **PyEarthSuite** ecosystem, focusing on 2D visualization
   and plotting of geospatial and Earth science data.

   Related packages in the suite:

   - **pyearth** - Core GIS operations and spatial toolbox
   - **pyearthviz3d** - 3D visualization with GeoVista
   - **pyearthhelp** - Data retrieval and HPC utilities
   - **pyearthmesh** - Mesh generation tools
   - **pyearthriver** - River network graph algorithms

Contents:

.. toctree::
   :maxdepth: 2

   getting-started
   visual/visual
   faq
   contribution
   authors
   support
```

---

### 4. docs/source/getting-started.rst
**Priority:** HIGH - User-facing installation instructions

**Changes needed:**
- **Line 8:** Change "pyearth" to "pyearthviz"
- **Line 10:** Change command to `pip install pyearthviz`
- **Line 12:** Change "pyearth" to "pyearthviz"
- **Line 14:** Change command to `conda install -c conda-forge pyearthviz`
- **Line 19:** Update text from "pyearth" to "pyearthviz"
- **Line 21:** Change import statement to `import pyearthviz`
- **Line 23:** Update import example to use pyearthviz module structure:
  ```python
  from pyearthviz.color.create_diverge_rgb_color_hex import create_diverge_rgb_color_hex
  from pyearthviz.map.map_vector_polygon_file import map_vector_polygon_file
  ```

**Additional content to add:**
- Mention that GDAL and Cartopy can be challenging to install via pip
- Recommend conda installation for easier dependency management
- Add link to full installation instructions in README.md

---

### 5. docs/source/contribution.rst
**Priority:** MEDIUM - Developer information

**Changes needed:**
- **Line 7:** Change "PyEarth" to "PyEarthViz"

**Suggested expansion:**
```rst
############
Contribution
############

PyEarthViz is developed and maintained by:

* Chang Liao (Pacific Northwest National Laboratory)

How to Contribute
=================

Contributions are welcome! Please follow these steps:

1. Fork the repository at https://github.com/changliao1025/pyearthviz
2. Create a feature branch
3. Make your changes with appropriate tests
4. Submit a pull request

Please report issues at: https://github.com/changliao1025/pyearthviz/issues
```

---

### 6. docs/source/support.rst
**Priority:** HIGH - Contains incorrect link

**Changes needed:**
- **Line 5:** Change GitHub URL from `pyflowline` to `pyearthviz`:
  ```
  Support is provided through Github issues (https://github.com/changliao1025/pyearthviz/issues).
  ```

**Additional content to add:**
```rst
#######
Support
#######

Support is provided through GitHub issues: https://github.com/changliao1025/pyearthviz/issues

Before submitting an issue, please:

1. Check existing issues to avoid duplicates
2. Provide a minimal reproducible example
3. Include your Python version and dependencies
4. Specify your operating system

For general questions about the PyEarthSuite ecosystem, visit the main PyEarth repository.
```

---

### 7. docs/source/faq.rst
**Priority:** MEDIUM - Contains mixed content

**Changes needed:**
- Keep questions 1-3 (conda environment, GDAL import, proj issues) - these are relevant to pyearthviz
- Update question 4 about plot functions - make it more specific to pyearthviz
- Remove question 5 about model output - not relevant to visualization library

**Suggested updates:**

```rst
###########################
Frequently Asked Questions
###########################

Installation Issues
===================

1. Why can't conda create my environment?

   Try turning off your VPN or configuring it to bypass conda channels.

2. Why does GDAL import fail?

   GDAL can be challenging to install. We recommend:
   - Use conda instead of pip: `conda install -c conda-forge gdal`
   - Use the conda-forge channel which has better-maintained builds
   - Install pyearthviz via conda to handle dependencies automatically

3. I'm getting PROJ-related errors (https://github.com/OSGeo/gdal/issues/1546)

   Make sure PROJ_LIB is correctly configured. PyEarthViz depends on GDAL, which uses PROJ.

   On Linux or Mac, set in `.bash_profile` or `.bashrc`:

   Anaconda:
   ```bash
   export PROJ_LIB=$HOME/.conda/envs/pyearthviz-env/share/proj
   ```

   Miniconda:
   ```bash
   export PROJ_LIB=/opt/miniconda3/envs/pyearthviz-env/share/proj
   ```

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
   - Use `geopandas` or `pyearth` to verify and reproject your data if needed

6. Color schemes don't look right in my plots

   - PyEarthViz provides several color utilities in the `color` module
   - Check if your data range matches the colormap normalization
   - Consider using diverging colormaps for data with meaningful center points
```

---

### 8. docs/source/visual/visual.rst
**Priority:** LOW - Already appropriate for pyearthviz

**Current state:** Lists visualization categories (Color, Formatter, Barplot, etc.)

**Recommendation:** Keep current structure but expand with:
- Brief description of each module
- Links to function documentation
- Example usage for each category

**Suggested enhancement:**
```rst
#############
Visualization
#############

PyEarthViz provides comprehensive 2D visualization tools for geospatial and scientific data.

************
Color
************

Utilities for creating and managing color schemes:

- `create_diverge_rgb_color_hex` - Generate diverging color palettes
- `create_qualitative_rgb_color_hex` - Generate distinct colors for categories
- `choose_n_color` - Select N evenly-spaced colors
- `pick_colormap` - Choose appropriate colormaps for data types

************
Map
************

Geospatial visualization tools:

- **Raster mapping**: GeoTIFF, NetCDF visualization
- **Vector mapping**: Points, lines, polygons with custom styling
- **Multi-layer maps**: Combine multiple datasets
- **Study area visualization**: Publication-ready maps
- **Tile servers**: Integration with online basemap services
- **Zebra frames**: Professional coordinate frames

************
Time Series
************

Specialized temporal data visualization:

- Basic time series plots
- Multi-resolution displays
- Two y-axis comparisons
- Variation plots with confidence intervals
- 3D temporal visualizations

[... continue for each module ...]
```

---

## Additional Recommendations

### Create New Documentation Files

Consider adding these files to improve documentation:

1. **docs/source/modules.rst** - Auto-generated module documentation
2. **docs/source/api.rst** - Complete API reference
3. **docs/source/examples.rst** - Gallery of example visualizations
4. **docs/source/installation.rst** - Detailed installation guide

### Update .readthedocs.yml

The current [`.readthedocs.yml`](.readthedocs.yml:1) looks correct but verify:
- Python version (currently 3.11) - matches pyproject.toml requirements
- Sphinx configuration path is correct
- Dependencies in `docs/requirements.txt` are sufficient

### Verify docs/requirements.txt

Current requirements look minimal but adequate:
- `breathe` - For C++ API documentation (may not be needed for pure Python)
- `sphinx` - Documentation generator
- `sphinx_rtd_theme` - ReadTheDocs theme
- `tomli` - For reading pyproject.toml

**Consider adding:**
- `sphinx-autodoc-typehints` - Better type hint documentation
- `nbsphinx` - If adding Jupyter notebook examples
- `sphinx-gallery` - For example gallery

---

## Implementation Priority

### High Priority (Must Fix for Documentation Build)
1. [`docs/source/conf.py`](docs/source/conf.py:1) - Critical paths and project names
2. [`docs/source/index.rst`](docs/source/index.rst:1) - Main entry point
3. [`docs/source/getting-started.rst`](docs/source/getting-started.rst:1) - User onboarding
4. [`docs/source/support.rst`](docs/source/support.rst:1) - Incorrect link

### Medium Priority (Important for Clarity)
5. [`docs/source/contribution.rst`](docs/source/contribution.rst:1) - Package name
6. [`docs/source/faq.rst`](docs/source/faq.rst:1) - Remove irrelevant content

### Low Priority (Enhancement)
7. [`docs/source/visual/visual.rst`](docs/source/visual/visual.rst:1) - Expand documentation
8. Create additional documentation files

---

## Testing Plan

After making changes:

1. **Local build test:**
   ```bash
   cd docs
   make clean
   make html
   ```

2. **Check for errors:**
   - Broken references
   - Missing files
   - Sphinx warnings

3. **Visual inspection:**
   - Open `docs/_build/html/index.html` in browser
   - Verify all links work
   - Check that content makes sense for pyearthviz

4. **ReadTheDocs integration:**
   - Push changes to repository
   - Verify ReadTheDocs builds successfully
   - Check live documentation at pyearthviz.readthedocs.io

---

## Summary

This plan provides a comprehensive roadmap for updating all documentation files from PyEarth to PyEarthViz. The changes ensure:

✅ Correct package names and references throughout
✅ Accurate installation instructions
✅ Proper GitHub and documentation links
✅ Relevant FAQ content for visualization library
✅ Clear explanation of PyEarthViz's role in the ecosystem
✅ Documentation structure that matches the actual codebase

The updates maintain the professional quality of the original documentation while accurately reflecting PyEarthViz's specific scope and functionality.
