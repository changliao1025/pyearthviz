Getting started
===============


Installation
============

PyEarthViz depends on several packages, including GDAL and Cartopy, which can be challenging to install through pip alone. We recommend using conda to install dependencies.

You can use the Conda package manager to install pyearthviz::

    conda install -c conda-forge pyearthviz

You can also use the Python package manager pip to install pyearthviz (requires GDAL and Cartopy pre-installed)::

    pip install pyearthviz

Building from Source
=====================

To build from source::

    # Clone the repository
    git clone https://github.com/changliao1025/pyearthviz.git
    cd pyearthviz

    # Install dependencies using conda
    conda install numpy matplotlib cartopy gdal pandas scipy statsmodels

    # Install pyearth (required dependency)
    conda install pyearth

    # Build and install
    pip install -e .

Usage
=====

To use functions from pyearthviz, you need to import the package or the functions directly::

    import pyearthviz

    from pyearthviz.color.create_diverge_rgb_color_hex import create_diverge_rgb_color_hex
    from pyearthviz.map.map_vector_polygon_file import map_vector_polygon_file

Examples
========

For examples and tutorials, please refer to the `examples` directory in the repository or visit the full documentation at https://pyearthviz.readthedocs.io
