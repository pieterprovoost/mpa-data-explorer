# MPA Data Explorer

## Data sources

- Protected area boundaries: Parques Nacionales Naturales de Colombia - RUNAP (Registro Único Nacional de Áreas Protegidas). Licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Source: https://runap.parquesnacionales.gov.co/.
- Biodiversity data: OBIS (2006) Ocean Biodiversity Information System. Intergovernmental Oceanographic Commission of UNESCO. https://obis.org.
- Basemap: [OpenFreeMap](https://openfreemap.org/) Bright style (`https://tiles.openfreemap.org/styles/bright`), based on OpenStreetMap data.

## How to build and run the container

Clone the repository from https://github.com/pieterprovoost/mpa-data-explorer and run the following command to build and run the container:

```sh
docker build -t mpa-data-explorer .
docker run --rm -p 8000:8000 mpa-data-explorer
```

Then open the application at http://localhost:8000.

## What was built

- A selection of Colombian MPA geometries were downloaded from [RUNAP (Registro Único Nacional de Áreas Protegidas)](https://runap.parquesnacionales.gov.co) and converted to GeoJSON. The conversion is done by a Python script that can easily be adjusted to change the MPA selection. RUNAP / PNN geospatial open data is [licensed under CC BY-SA](https://www.parquesnacionales.gov.co/sala-prensa/boletines/datos-espaciales-de-parques-nacionales-adoptan-cc-by-sa-4-0/).
- A backend application was developed using Python and FastAPI to connect to the OBIS API, to handle the CSV data download, and to serve the prebuilt frontend application.
- A frontend application was developed using the Svelte UI framework and the MapLibre GL JS mapping library. The application displays the MPAs on a map and presents information about the selected MPA in five panels: general information, records over time, taxonomic composition at the phylum level, contributing OBIS nodes, and contributing publishing institutions.
- All occurrence points are displayed on the map for the selected MPA. This uses vector tiles served by the OBIS API.
- All occurrence data can be downloaded from the application. The backend will make subsequent paged requests to the OBIS API until all records have been downloaded, and package them in a single CSV. The CSV also contains citation guidelines.

## What was deliberately not built

- A live connection to a database holding up-to-date spatial information for MPAs was not built due to complexity, limited time, and licensing restrictions.
- Continuous Integration and Continuous Delivery (CI/CD) was not built as this is not intended to be an operational system. A test suite is not included for the same reasons.

## Known limitations

- MPA geometries have been simplified. In order to support potentially very complex geometries, a tile server would need to be set up, and the full OBIS dataset would need to be present on the server due to limitations of the OBIS API.
- Downloads are synchronous to keep the application minimal. Asynchronous downloads would make the download process more fault tolerant.

## What would I do with two more days

- More explicitly address the gaps in space, time, and taxonomy.
- Add more interesting data visualizations, such as an overall taxonomy treemap or a gap analysis for major taxonomic groups over time.
- Add a more complete dataset of MPAs, make the selection of MPAs configurable so the application can be easily reused by member states.
- Add a dataset listing and occurrence record browsing.
- Add short TTL caching of OBIS API responses for repeated queries on the same MPA.

## Containerisation

- Base image choice: I'm using a multi-stage build with lightweight images `node:22-alpine` for building the frontend application and `python:3.12-slim` to serve the Python based backend. The Node image is only used for the build and does not end up in the final image.
- How dependencies are pinned: the frontend uses `package-lock.json` for a reproducible install. The backend pins exact versions in `requirements.txt`.
- Build time and image size tradeoffs: the multi-stage build keeps Node out of the runtime image. The build time is quite fast (11 seconds on my system) and the image size is below 200 MB.
- How configuration and secrets would be handled in a real deployment: no secrets are required for this application as it uses a public API for data access. In a production scenario, configuration would be provided via environment variables.