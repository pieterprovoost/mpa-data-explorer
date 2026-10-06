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

  // See Vite installation at https://maplibre.org/maplibre-gl-js/docs
  setWorkerUrl(maplibreWorkerUrl)

  let mapEl
  let map
  let geojson = $state(null)
  let selected = $state('')
  let mapReady = $state(false)

  const names = $derived(
    geojson?.features?.map((f) => f.properties.name).sort() ?? [],
  )

  const selectedFeature = $derived(
    geojson?.features?.find((f) => f.properties.name === selected) ?? null,
  )

  function fitAll() {
    const bounds = new LngLatBounds()
    const walk = (coords) => {
      if (typeof coords[0] === 'number') bounds.extend(coords)
      else for (const c of coords) walk(c)
    }
    for (const f of geojson.features) walk(f.geometry.coordinates)
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, {
        padding: { top: 40, bottom: 40, left: 280, right: 40 },
        maxZoom: 6,
        duration: 0,
      })
    }
  }

  function applyPaint() {
    if (!map?.getLayer('mpas-fill')) return
    const match = ['==', ['get', 'name'], selected || '']
    map.setPaintProperty('mpas-fill', 'fill-color', ['case', match, '#c45c26', '#0f7c86'])
    map.setPaintProperty('mpas-fill', 'fill-opacity', 0.25)
    map.setPaintProperty('mpas-line', 'line-color', ['case', match, '#c45c26', '#0f7c86'])
    map.setPaintProperty('mpas-line', 'line-width', ['case', match, 2.5, 1.5])
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
    fitAll()
  }

  $effect(() => {
    selected
    applyPaint()
  })

  $effect(() => {
    if (mapReady && geojson && !map.getSource('mpas')) addMpaLayers()
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
    width: min(20rem, calc(100% - 2rem));
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
