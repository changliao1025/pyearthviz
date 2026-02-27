# PyEarthViz Documentation Structure

## Documentation Architecture

```mermaid
graph TD
    A[index.rst<br/>Main Entry] --> B[getting-started.rst<br/>Installation & Usage]
    A --> C[visual/visual.rst<br/>Module Overview]
    A --> D[faq.rst<br/>Common Issues]
    A --> E[contribution.rst<br/>Developer Info]
    A --> F[authors.rst<br/>Credits]
    A --> G[support.rst<br/>Help Resources]

    C --> C1[Map Module<br/>Geospatial Viz]
    C --> C2[Time Series<br/>Temporal Plots]
    C --> C3[Scatter<br/>Statistical Plots]
    C --> C4[Histogram<br/>Distributions]
    C --> C5[Color<br/>Palettes & Schemes]
    C --> C6[Other Modules<br/>Bar, Box, Ridge, etc.]

    H[conf.py<br/>Sphinx Config] -.->|configures| A
    I[.readthedocs.yml<br/>RTD Config] -.->|builds| H
    J[docs/requirements.txt<br/>Doc Dependencies] -.->|used by| I
```

## File Update Workflow

```mermaid
graph LR
    A[PyEarth Docs<br/>Original] -->|Copy| B[PyEarthViz Docs<br/>Raw Copy]
    B -->|Update| C[Phase 1:<br/>Critical Files]
    C -->|Update| D[Phase 2:<br/>Content Files]
    D -->|Enhance| E[Phase 3:<br/>Improvements]
    E -->|Test| F[Final Docs<br/>Ready]

    style A fill:#f9f,stroke:#333
    style B fill:#ff9,stroke:#333
    style C fill:#9f9,stroke:#333
    style D fill:#9f9,stroke:#333
    style E fill:#99f,stroke:#333
    style F fill:#9f9,stroke:#333
```

## Module Coverage in Documentation

### Current PyEarthViz Modules

| Module | Description | Doc Status |
|--------|-------------|------------|
| **animate** | Polygon animation over time | Listed in visual.rst |
| **barplot** | Bar chart visualizations | Listed in visual.rst |
| **boxplot** | Box plot distributions | Listed in visual.rst |
| **color** | Color scheme utilities | Listed in visual.rst |
| **histogram** | Distribution histograms | Listed in visual.rst |
| **ladder** | Ladder plot for discrete data | Listed in visual.rst |
| **map** | Geospatial mapping (raster/vector) | Listed in visual.rst |
| **ridgeplot** | Ridge plots for distributions | Listed in visual.rst |
| **scatter** | Scatter plots with density | Listed in visual.rst |
| **surface** | Surface plots (placeholder) | Not documented |
| **timeseries** | Temporal data visualization | Listed in visual.rst |

### Recommended Documentation Expansion

1. **API Reference** - Auto-generated from docstrings
2. **Example Gallery** - Visual examples for each module
3. **User Guide** - Step-by-step tutorials
4. **Migration Guide** - For users transitioning from PyEarth

## Build Dependencies

```mermaid
graph TD
    A[docs/requirements.txt] --> B[sphinx]
    A --> C[sphinx_rtd_theme]
    A --> D[breathe]
    A --> E[tomli]

    F[pyproject.toml] --> G[Project Metadata]
    G -.->|read by| H[conf.py]

    B --> I[Documentation Build]
    C --> I
    D --> I
    E --> H
    H --> I

    I --> J[HTML Output]
    I --> K[PDF Output]
    I --> L[EPUB Output]
```

## PyEarthSuite Ecosystem Context

```mermaid
graph TD
    PE[PyEarth<br/>Core GIS & Spatial Toolbox]

    PE --> PV[PyEarthViz<br/>2D Visualization]
    PE --> PV3[PyEarthViz3D<br/>3D Globe Viz]
    PE --> PR[PyEarthRiver<br/>River Networks]
    PE --> PM[PyEarthMesh<br/>Mesh Generation]
    PE --> PH[PyEarthHelp<br/>Data & HPC Utils]

    PV -.->|depends on| PE
    PV3 -.->|depends on| PE
    PR -.->|depends on| PE
    PM -.->|depends on| PE
    PH -.->|used by| PE

    style PE fill:#9cf,stroke:#333,stroke-width:3px
    style PV fill:#f96,stroke:#333,stroke-width:3px
    style PV3 fill:#9f9,stroke:#333
    style PR fill:#9f9,stroke:#333
    style PM fill:#9f9,stroke:#333
    style PH fill:#9f9,stroke:#333
```

## Update Checklist by Priority

### Phase 1: Critical Configuration (Required for Build)
- [ ] `docs/source/conf.py` - Update all pyearth → pyearthviz references
- [ ] `docs/source/index.rst` - Main documentation entry point
- [ ] `docs/source/getting-started.rst` - Installation and import examples

### Phase 2: Content Updates (Required for Accuracy)
- [ ] `docs/source/support.rst` - Fix GitHub issue URL
- [ ] `docs/source/contribution.rst` - Update package name
- [ ] `docs/source/faq.rst` - Update content for visualization focus

### Phase 3: Enhancements (Nice to Have)
- [ ] `docs/source/visual/visual.rst` - Expand module documentation
- [ ] Add `docs/source/api.rst` - API reference
- [ ] Add `docs/source/examples.rst` - Example gallery

## Testing Strategy

1. **Local Build Test**
   ```bash
   cd docs
   make clean && make html
   ```

2. **Link Validation**
   ```bash
   make linkcheck
   ```

3. **Visual Inspection**
   - Open `docs/_build/html/index.html`
   - Check navigation structure
   - Verify all internal links work
   - Confirm external links point to pyearthviz

4. **ReadTheDocs Integration**
   - Push to GitHub
   - Monitor RTD build at https://readthedocs.org/projects/pyearthviz/
   - Review live docs at https://pyearthviz.readthedocs.io

## Key Changes Summary

| File | Old Reference | New Reference |
|------|---------------|---------------|
| conf.py | project = "pyearth" | project = "pyearthviz" |
| conf.py | input_dir = "../../pyearth" | input_dir = "../../pyearthviz" |
| conf.py | breathe_projects["pyearth"] | breathe_projects["pyearthviz"] |
| index.rst | Welcome to pyearth | Welcome to PyEarthViz |
| getting-started.rst | pip install pyearth | pip install pyearthviz |
| getting-started.rst | import pyearth | import pyearthviz |
| support.rst | pyflowline/issues | pyearthviz/issues |
| contribution.rst | PyEarth was developed | PyEarthViz is developed |
| faq.rst | model output questions | visualization questions |

