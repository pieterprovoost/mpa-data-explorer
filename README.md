# MPA Data Explorer

## Data sources

- UNEP-WCMC and IUCN (2026), Protected Planet: The World Database on Protected Areas (WDPA) and World Database on Other Effective Area-based Conservation Measures (WD-OECM) [Online], October 2026, Cambridge, UK: UNEP-WCMC and IUCN. Available at: www.protectedplanet.net.
- Flanders Marine Institute (2023). Maritime Boundaries Geodatabase: Maritime Boundaries and Exclusive Economic Zones (200NM), version 12. Available online at https://www.marineregions.org/. https://doi.org/10.14284/632

## How to build and run the container

```
docker build -t mpa-data-explorer .
docker run --rm -p 8000:8000 mpa-data-explorer
```

Then open http://localhost:8000.
