<script>
  import { onMount } from 'svelte'
  import {
    Map,
    NavigationControl,
    LngLatBounds,
    Popup,
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
  // Hardcoded accepted Phylum / Phylum (Division) count from WoRMS.
  const WORMS_PHYLA_TOTAL = 106

  const formatCount = (value) =>
    value == null ? '' : Number(value).toLocaleString()

  const formatDate = (value) => {
    if (!value) return '—'
    const date = new Date(`${value}T00:00:00Z`)
    if (Number.isNaN(date.getTime())) return String(value)
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    })
  }

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
  let hoverPopup
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
  let totalRecords = $state(null)
  let taxonomyRows = $state([])
  let nodesLoading = $state(false)
  let institutesLoading = $state(false)
  let yearsLoading = $state(false)
  let statsLoading = $state(false)
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
    if (!map?.getLayer('mpas-fill') || !map?.getLayer('mpas-line')) return
    const match = ['==', ['get', 'name'], selected || '']
    map.setPaintProperty('mpas-fill', 'fill-color', '#0f7c86')
    map.setPaintProperty('mpas-fill', 'fill-opacity', 0.25)
    map.setPaintProperty('mpas-line', 'line-color', '#0f7c86')
    map.setPaintProperty('mpas-line', 'line-width', 2)
    map.setPaintProperty('mpas-line', 'line-opacity', ['case', match, 1, 0])
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

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
  }

  function hoverPopupHtml(properties) {
    const rows = [
      ['Category', properties.category],
      ['Inscribed', formatDate(properties.inscription_date)],
      ['RUNAP ID', properties.runap_id],
    ]
    const body = rows
      .filter(([, v]) => v != null && v !== '')
      .map(
        ([label, value]) =>
          `<div class="mpa-popup-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`,
      )
      .join('')
    return `<div class="mpa-popup-card"><div class="mpa-popup-title">${escapeHtml(properties.name)}</div>${body}</div>`
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
      paint: {
        'line-color': '#0f7c86',
        'line-width': 2,
        'line-opacity': 0,
      },
    })
    hoverPopup = new Popup({
      closeButton: false,
      closeOnClick: false,
      offset: 14,
      maxWidth: '18rem',
      className: 'mpa-popup',
    })
    map.on('click', 'mpas-fill', (e) => {
      const name = e.features?.[0]?.properties?.name
      if (!name) return
      selected = name === selected ? '' : name
      if (selected === name) hoverPopup?.remove()
    })
    map.on('mousemove', 'mpas-fill', (e) => {
      map.getCanvas().style.cursor = 'pointer'
      const feature = e.features?.[0]
      if (!feature) return
      if (feature.properties?.name === selected) {
        hoverPopup?.remove()
        return
      }
      hoverPopup
        .setLngLat(e.lngLat)
        .setHTML(hoverPopupHtml(feature.properties))
        .addTo(map)
    })
    map.on('mouseleave', 'mpas-fill', () => {
      map.getCanvas().style.cursor = ''
      hoverPopup?.remove()
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

  // Load aggregate statistics (total records)
  $effect(() => {
    const wkt = selectedWkt
    if (!wkt) {
      totalRecords = null
      statsLoading = false
      return
    }

    const controller = new AbortController()
    statsLoading = true
    const params = new URLSearchParams({ geometry: wkt })
    fetch(`/api/statistics?${params}`, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`statistics ${r.status}`)
        return r.json()
      })
      .then((data) => {
        totalRecords = data.records ?? 0
        statsLoading = false
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        console.error(err)
        totalRecords = null
        statsLoading = false
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
      style: 'https://tiles.openfreemap.org/styles/bright',
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

    return () => {
      hoverPopup?.remove()
      map?.remove()
    }
  })
</script>

<div class="shell">
  <div class="map" bind:this={mapEl}></div>

  <aside class="panel">
    <section class="card">
      <p class="eyebrow">Colombia - RUNAP</p>
      <h1>MPA Data Explorer</h1>

      <label>
        <span class="field-label">Protected area</span>
        <select bind:value={selected}>
          <option value="">(Select a protected area)</option>
          {#each names as name}
            <option value={name}>{name}</option>
          {/each}
        </select>
      </label>

      {#if selectedFeature}
        <dl class="attrs">
          <div>
            <dt>Category</dt>
            <dd>{selectedFeature.properties.category || '—'}</dd>
          </div>
          <div>
            <dt>Inscribed</dt>
            <dd>{formatDate(selectedFeature.properties.inscription_date)}</dd>
          </div>
          <div>
            <dt>RUNAP ID</dt>
            <dd>{selectedFeature.properties.runap_id ?? '—'}</dd>
          </div>
        </dl>
        {#if selectedWkt}
          <div class="download">
            <a
              class="btn btn-primary"
              href={`/api/occurrences.csv?${new URLSearchParams({ geometry: selectedWkt })}`}
            >
              Download all records as CSV
            </a>
            <p class="note">Downloads can take a few minutes - do not navigate away.</p>
          </div>
        {/if}
      {/if}
    </section>

    {#if selectedFeature}
      <YearsChart
        title="Records over time"
        rows={yearRows}
        loading={yearsLoading}
        totalRecords={totalRecords}
        statsLoading={statsLoading}
      />
      <PagedTable
        title="Taxonomy"
        columns={taxonomyColumns}
        rows={taxonomyRows}
        total={taxonomyTotal}
        bind:skip={taxonomySkip}
        size={PAGE_SIZE}
        loading={taxonomyLoading}
        summary={!taxonomyLoading && taxonomyTotal > 0
          ? {
              observed: taxonomyTotal,
              expected: WORMS_PHYLA_TOTAL,
              label: 'phyla in WoRMS',
            }
          : null}
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
      <section class="card sources">
        <h2>Data sources</h2>
        <ul>
          <li>
            Protected area boundaries:
            <a href="https://runap.parquesnacionales.gov.co/" target="_blank" rel="noopener noreferrer"
              >Parques Nacionales Naturales de Colombia — RUNAP</a
            >
            (CC BY-SA 4.0).
          </li>
          <li>
            Biodiversity data:
            <a href="https://obis.org" target="_blank" rel="noopener noreferrer"
              >OBIS (Ocean Biodiversity Information System)</a
            >, IOC-UNESCO.
          </li>
          <li>
            Basemap:
            <a href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a>
            Bright style, based on OpenStreetMap data.
          </li>
        </ul>
      </section>
    {/if}
  </aside>
</div>

<style>
  :global(:root) {
    --ink: #14212b;
    --muted: #5b6b78;
    --line: #e6ebef;
    --soft: #f4f7f8;
    --card: #ffffff;
    --accent: #0f7c86;
    --shadow: 0 1px 2px rgb(20 33 43 / 0.04), 0 10px 28px rgb(20 33 43 / 0.08);
    --font-sans: 'DM Sans', system-ui, sans-serif;
    --font-display: 'Fraunces', Georgia, serif;
  }

  :global(html),
  :global(body),
  :global(#app) {
    margin: 0;
    height: 100%;
    font-family: var(--font-sans);
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
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
    gap: 0.7rem;
    width: min(25.5rem, calc(100% - 2rem));
    max-height: calc(100% - 2rem);
    padding-right: 0.85rem;
    overflow-y: auto;
    background: transparent;
  }

  .card {
    padding: 1.1rem 1.15rem;
    background: var(--card);
    border: 1px solid rgb(255 255 255 / 0.7);
    border-radius: 14px;
    box-shadow: var(--shadow);
  }

  .eyebrow {
    margin: 0 0 0.25rem;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
  }

  h1 {
    margin: 0 0 0.95rem;
    font-family: var(--font-display);
    font-size: 1.45rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    line-height: 1.15;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .field-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--muted);
  }

  select {
    appearance: none;
    width: 100%;
    font: inherit;
    font-size: 0.92rem;
    font-weight: 500;
    color: var(--ink);
    padding: 0.65rem 2.2rem 0.65rem 0.75rem;
    border: 1px solid var(--line);
    border-radius: 10px;
    background:
      linear-gradient(45deg, transparent 50%, var(--muted) 50%) calc(100% - 1.05rem) calc(50% - 0.15rem) / 0.35rem 0.35rem
        no-repeat,
      linear-gradient(135deg, var(--muted) 50%, transparent 50%) calc(100% - 0.75rem) calc(50% - 0.15rem) / 0.35rem
        0.35rem no-repeat,
      var(--soft);
    cursor: pointer;
  }

  select:focus {
    outline: 2px solid rgb(15 124 134 / 0.28);
    outline-offset: 1px;
    border-color: var(--accent);
    background-color: #fff;
  }

  .attrs {
    display: grid;
    gap: 0.7rem;
    margin: 1rem 0 0;
    padding-top: 0.95rem;
    border-top: 1px solid var(--line);
  }

  .attrs > div {
    display: grid;
    gap: 0.18rem;
  }

  .attrs dt {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--muted);
  }

  .attrs dd {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    line-height: 1.35;
    color: var(--ink);
  }

  .download {
    display: grid;
    gap: 0.4rem;
    margin-top: 1rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: fit-content;
    min-height: 2.1rem;
    padding: 0.45rem 0.9rem;
    border-radius: 10px;
    border: 1px solid transparent;
    font: inherit;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    text-decoration: none;
    cursor: pointer;
    transition: background 120ms ease;
  }

  .btn-primary {
    color: #fff;
    background: var(--ink);
  }

  .btn-primary:hover {
    background: #243542;
  }

  .note {
    margin: 0;
    font-size: 0.72rem;
    line-height: 1.4;
    color: var(--muted);
  }

  .sources h2 {
    margin: 0 0 0.55rem;
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--ink);
  }

  .sources ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 0.55rem;
  }

  .sources li {
    font-size: 0.82rem;
    line-height: 1.45;
    color: var(--muted);
  }

  .sources a {
    color: var(--ink);
    font-weight: 600;
    text-decoration: underline;
    text-decoration-color: rgb(20 33 43 / 0.25);
    text-underline-offset: 0.15em;
  }

  .sources a:hover {
    color: var(--accent);
    text-decoration-color: rgb(15 124 134 / 0.45);
  }

  :global(.mpa-popup .maplibregl-popup-content) {
    padding: 0;
    border-radius: 12px;
    box-shadow: var(--shadow);
    overflow: hidden;
  }

  :global(.mpa-popup .maplibregl-popup-tip) {
    border-top-color: #fff;
  }

  :global(.mpa-popup-card) {
    padding: 0.8rem 0.9rem;
    background: #fff;
    color: var(--ink);
    font: 13px/1.35 var(--font-sans);
  }

  :global(.mpa-popup-title) {
    margin-bottom: 0.55rem;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.98rem;
    letter-spacing: -0.01em;
  }

  :global(.mpa-popup-row) {
    display: flex;
    justify-content: space-between;
    gap: 0.85rem;
    margin-top: 0.28rem;
    color: var(--muted);
    font-size: 0.78rem;
  }

  :global(.mpa-popup-row span) {
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-weight: 600;
    font-size: 0.66rem;
  }

  :global(.mpa-popup-row strong) {
    color: var(--ink);
    font-weight: 600;
    font-size: 0.8rem;
    text-align: right;
    text-transform: none;
    letter-spacing: 0;
  }
</style>
