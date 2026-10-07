<script>
  import { onMount } from 'svelte'
  import {
    Map,
    NavigationControl,
    LngLatBounds,
    setWorkerUrl,
  } from 'maplibre-gl'
  import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
  import 'maplibre-gl/dist/maplibre-gl.css'
  import PagedTable from './lib/PagedTable.svelte'
  import YearsChart from './lib/YearsChart.svelte'

  // See Vite installation at https://maplibre.org/maplibre-gl-js/docs
  setWorkerUrl(maplibreWorkerUrl)

  const PAGE_SIZE = 10
  const MAX_WKT_SIZE = 10000

  const formatCount = (value) =>
    value == null ? '' : Number(value).toLocaleString()

  const tableColumns = [
    { key: 'name', label: 'Name' },
    { key: 'records', label: 'Records', format: formatCount },
  ]

  const taxonomyColumns = [
    { key: 'name', label: 'Phylum' },
    { key: 'records', label: 'Records', format: formatCount },
  ]


  let mapEl
  let map
  let geojson = $state(null)
  let selected = $state('')
  let mapReady = $state(false)

  let nodesSkip = $state(0)
  let institutesSkip = $state(0)
  let taxonomySkip = $state(0)
  let nodesTotal = $state(0)
  let institutesTotal = $state(0)
  let taxonomyTotal = $state(0)
  let nodeRows = $state([])
  let instituteRows = $state([])
  let yearRows = $state([])
  let taxonomyRows = $state([])
  let nodesLoading = $state(false)
  let institutesLoading = $state(false)
  let yearsLoading = $state(false)
  let taxonomyLoading = $state(false)

  const names = $derived(
    geojson?.features?.map((f) => f.properties.name).sort() ?? [],
  )

  const selectedFeature = $derived(
    geojson?.features?.find((f) => f.properties.name === selected) ?? null,
  )

  const mapPadding = { top: 40, bottom: 40, left: 300, right: 40 }

  function extendBounds(bounds, coords) {
    if (typeof coords[0] === 'number') bounds.extend(coords)
    else for (const c of coords) extendBounds(bounds, c)
  }

  function fitGeometry(geometry, { maxZoom = 6, duration = 0 } = {}) {
    const bounds = new LngLatBounds()
    extendBounds(bounds, geometry.coordinates)
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: mapPadding, maxZoom, duration })
    }
  }

  function fitAll() {
    const bounds = new LngLatBounds()
    for (const f of geojson.features) extendBounds(bounds, f.geometry.coordinates)
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { padding: mapPadding, maxZoom: 6, duration: 0 })
    }
  }

  function ringWkt(ring) {
    return ring.map(([x, y]) => `${x} ${y}`).join(', ')
  }

  function geometryToWkt(geometry) {
    if (geometry.type === 'Polygon') {
      return `POLYGON (${geometry.coordinates.map((r) => `(${ringWkt(r)})`).join(', ')})`
    }
    if (geometry.type === 'MultiPolygon') {
      const polys = geometry.coordinates.map(
        (poly) => `(${poly.map((r) => `(${ringWkt(r)})`).join(', ')})`,
      )
      return `MULTIPOLYGON (${polys.join(', ')})`
    }
    throw new Error(`Unsupported geometry type: ${geometry.type}`)
  }

  function obisWkt(geometry) {
    const wkt = geometryToWkt(geometry)
    const size = encodeURIComponent(wkt).length
    console.log('WKT size:', size)
    if (size <= MAX_WKT_SIZE) return wkt
    // If the WKT is too large, fall back to bounding box
    const bounds = new LngLatBounds()
    extendBounds(bounds, geometry.coordinates)
    const w = bounds.getWest()
    const s = bounds.getSouth()
    const e = bounds.getEast()
    const n = bounds.getNorth()
    return `POLYGON ((${w} ${s}, ${e} ${s}, ${e} ${n}, ${w} ${n}, ${w} ${s}))`
  }

  const selectedWkt = $derived(
    selectedFeature ? obisWkt(selectedFeature.geometry) : null,
  )

  function applyPaint() {
    if (!map?.getLayer('mpas-fill')) return
    const match = ['==', ['get', 'name'], selected || '']
    map.setPaintProperty('mpas-fill', 'fill-color', ['case', match, '#c45c26', '#0f7c86'])
    map.setPaintProperty('mpas-fill', 'fill-opacity', 0.25)
    map.setPaintProperty('mpas-line', 'line-color', ['case', match, '#c45c26', '#0f7c86'])
    map.setPaintProperty('mpas-line', 'line-width', ['case', match, 2.5, 1.5])
  }

  function clearObisLayers() {
    if (map.getLayer('obis-points')) map.removeLayer('obis-points')
    if (map.getSource('obis')) map.removeSource('obis')
  }

  function syncObisLayers() {
    if (!mapReady || !map?.getSource('mpas')) return
    clearObisLayers()
    if (!selectedFeature) return

    const wkt = obisWkt(selectedFeature.geometry)
    const params = new URLSearchParams({
      geometry: wkt,
      tiletype: 'point',
      cellspertile: '200',
    })
    map.addSource('obis', {
      type: 'vector',
      tiles: [
        `https://api.obis.org/occurrence/tile/{x}/{y}/{z}.mvt?${params}`,
      ],
      minzoom: 0,
      maxzoom: 14,
    })
    map.addLayer(
      {
        id: 'obis-points',
        type: 'circle',
        source: 'obis',
        'source-layer': 'grid',
        paint: {
          'circle-opacity': 0,
          'circle-stroke-color': '#000',
          'circle-stroke-opacity': 0.85,
          'circle-stroke-width': 1,
          'circle-radius': 3,
        },
      },
      'mpas-line',
    )
  }

  function addMpaLayers() {
    map.addSource('mpas', { type: 'geojson', data: geojson })
    map.addLayer({
      id: 'mpas-fill',
      type: 'fill',
      source: 'mpas',
      paint: { 'fill-color': '#0f7c86', 'fill-opacity': 0.25 },
    })
    map.addLayer({
      id: 'mpas-line',
      type: 'line',
      source: 'mpas',
      paint: { 'line-color': '#0f7c86', 'line-width': 1.5 },
    })
    map.on('click', 'mpas-fill', (e) => {
      const name = e.features?.[0]?.properties?.name
      if (name) selected = name === selected ? '' : name
    })
    map.on('mouseenter', 'mpas-fill', () => {
      map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'mpas-fill', () => {
      map.getCanvas().style.cursor = ''
    })
    applyPaint()
    syncObisLayers()
    fitAll()
  }

  // Reset table pagination when the selected MPA changes
  $effect(() => {
    selected
    nodesSkip = 0
    institutesSkip = 0
    taxonomySkip = 0
  })

  // Update map highlight, OBIS tiles, viewport
  $effect(() => {
    selected
    applyPaint()
    syncObisLayers()
    if (selectedFeature) {
      fitGeometry(selectedFeature.geometry, { maxZoom: 10, duration: 400 })
    } else if (mapReady && geojson && map?.getSource('mpas')) {
      fitAll()
    }
  })

  // Add MPA layers
  $effect(() => {
    if (mapReady && geojson && !map.getSource('mpas')) addMpaLayers()
  })

  // Load contributing nodes
  $effect(() => {
    const wkt = selectedWkt
    const skip = nodesSkip
    if (!wkt) {
      nodeRows = []
      nodesTotal = 0
      nodesLoading = false
      return
    }

    const controller = new AbortController()
    nodesLoading = true
    const params = new URLSearchParams({
      geometry: wkt,
      skip: String(skip),
      size: String(PAGE_SIZE),
    })
    fetch(`/api/nodes?${params}`, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`nodes ${r.status}`)
        return r.json()
      })
      .then((data) => {
        nodeRows = data.results ?? []
        nodesTotal = data.total ?? 0
        nodesLoading = false
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        console.error(err)
        nodeRows = []
        nodesTotal = 0
        nodesLoading = false
      })

    return () => controller.abort()
  })

  // Load contributing institutes
  $effect(() => {
    const wkt = selectedWkt
    const skip = institutesSkip
    if (!wkt) {
      instituteRows = []
      institutesTotal = 0
      institutesLoading = false
      return
    }

    const controller = new AbortController()
    institutesLoading = true
    const params = new URLSearchParams({
      geometry: wkt,
      skip: String(skip),
      size: String(PAGE_SIZE),
    })
    fetch(`/api/institutes?${params}`, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`institutes ${r.status}`)
        return r.json()
      })
      .then((data) => {
        instituteRows = data.results ?? []
        institutesTotal = data.total ?? 0
        institutesLoading = false
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        console.error(err)
        instituteRows = []
        institutesTotal = 0
        institutesLoading = false
      })

    return () => controller.abort()
  })

  // Load records per year
  $effect(() => {
    const wkt = selectedWkt
    if (!wkt) {
      yearRows = []
      yearsLoading = false
      return
    }

    const controller = new AbortController()
    yearsLoading = true
    const params = new URLSearchParams({ geometry: wkt })
    fetch(`/api/years?${params}`, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`years ${r.status}`)
        return r.json()
      })
      .then((data) => {
        yearRows = data.results ?? []
        yearsLoading = false
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        console.error(err)
        yearRows = []
        yearsLoading = false
      })

    return () => controller.abort()
  })

  // Load taxonomic groups
  $effect(() => {
    const wkt = selectedWkt
    const skip = taxonomySkip
    if (!wkt) {
      taxonomyRows = []
      taxonomyTotal = 0
      taxonomyLoading = false
      return
    }

    const controller = new AbortController()
    taxonomyLoading = true
    const params = new URLSearchParams({
      geometry: wkt,
      skip: String(skip),
      size: String(PAGE_SIZE),
    })
    fetch(`/api/taxonomy?${params}`, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`taxonomy ${r.status}`)
        return r.json()
      })
      .then((data) => {
        taxonomyRows = data.results ?? []
        taxonomyTotal = data.total ?? 0
        taxonomyLoading = false
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        console.error(err)
        taxonomyRows = []
        taxonomyTotal = 0
        taxonomyLoading = false
      })

    return () => controller.abort()
  })

  onMount(() => {
    map = new Map({
      container: mapEl,
      style: 'https://tiles.openfreemap.org/styles/positron',
      center: [-74, 4.5],
      zoom: 4.5,
    })
    map.addControl(new NavigationControl({ showCompass: false }), 'bottom-right')
    map.on('load', () => {
      mapReady = true
    })

    fetch('/api/mpas')
      .then((r) => r.json())
      .then((data) => {
        geojson = data
      })
      .catch(console.error)

    return () => map?.remove()
  })
</script>

<div class="shell">
  <div class="map" bind:this={mapEl}></div>

  <aside class="panel">
    <section class="card">
      <h1>MPA Data Explorer</h1>

      <label>
        Protected area
        <select bind:value={selected}>
          <option value="">All areas</option>
          {#each names as name}
            <option value={name}>{name}</option>
          {/each}
        </select>
      </label>

      {#if selectedFeature}
        <p>Designation: {selectedFeature.properties.designation}</p>
        <p>WDPA ID: {selectedFeature.properties.wdpa_id}</p>
      {/if}
    </section>

    {#if selectedFeature}
      <YearsChart
        title="Records over time"
        rows={yearRows}
        loading={yearsLoading}
        downloadHref={
          selectedWkt
            ? `/api/occurrences.csv?${new URLSearchParams({ geometry: selectedWkt })}`
            : null
        }
      />
      <PagedTable
        title="Taxonomy"
        columns={taxonomyColumns}
        rows={taxonomyRows}
        total={taxonomyTotal}
        bind:skip={taxonomySkip}
        size={PAGE_SIZE}
        loading={taxonomyLoading}
      />
      <PagedTable
        title="Contributing nodes"
        columns={tableColumns}
        rows={nodeRows}
        total={nodesTotal}
        bind:skip={nodesSkip}
        size={PAGE_SIZE}
        loading={nodesLoading}
      />
      <PagedTable
        title="Contributing institutions"
        columns={tableColumns}
        rows={instituteRows}
        total={institutesTotal}
        bind:skip={institutesSkip}
        size={PAGE_SIZE}
        loading={institutesLoading}
      />
    {/if}
  </aside>
</div>

<style>
  :global(html),
  :global(body),
  :global(#app) {
    margin: 0;
    height: 100%;
    font-family: system-ui, sans-serif;
  }

  :global(*) {
    box-sizing: border-box;
  }

  .shell {
    position: relative;
    height: 100%;
  }

  .map {
    position: absolute;
    inset: 0;
  }

  .panel {
    position: absolute;
    z-index: 2;
    top: 1rem;
    left: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    width: min(25rem, calc(100% - 2rem));
    max-height: calc(100% - 2rem);
    padding-right: 0.85rem;
    overflow-y: auto;
    background: transparent;
  }

  .card {
    padding: 1rem;
    background: #fff;
    border-radius: 8px;
  }

  h1 {
    margin: 0 0 0.75rem;
    font-size: 1.15rem;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  select {
    font: inherit;
    padding: 0.4rem;
  }

  p {
    margin: 0.6rem 0 0;
  }
</style>
