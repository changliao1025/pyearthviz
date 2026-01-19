"""
Setup script for pyearthviz package.

For modern builds, use pyproject.toml.
This setup.py is maintained for backward compatibility.
"""

from setuptools import setup, find_packages

# Read the long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pyearthviz",
    use_scm_version=False,
    version="0.1.0",
    author="Chang Liao",
    author_email="changliao.climate@gmail.com",
    description="2D visualization and plotting tools for geospatial data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/changliao1025/pyearthviz",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "matplotlib>=3.3.0",
        "cartopy>=0.18.0",
        "gdal>=3.0.0",
    ],
    extras_require={
        "scipy": ["scipy>=1.5.0"],
        "all": ["scipy>=1.5.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
