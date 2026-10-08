# MPA Data Explorer

## Data sources

- Protected-area boundaries: Parques Nacionales Naturales de Colombia - RUNAP (Registro Único Nacional de Áreas Protegidas). Licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Source: https://runap.parquesnacionales.gov.co/.

## How to build and run the container

```
docker build -t mpa-data-explorer .
docker run --rm -p 8000:8000 mpa-data-explorer
```

Then open http://localhost:8000.
