<script>
  import * as Plot from '@observablehq/plot'
  import { onDestroy } from 'svelte'

  let {
    title = 'Records over time',
    rows = [],
    loading = false,
    downloadHref = null,
  } = $props()

  let chartEl = $state(null)
  let plotNode = null

  $effect(() => {
    const el = chartEl
    const data = rows
    const isLoading = loading

    if (!el || isLoading || data.length === 0) {
      clearPlot()
      return
    }

    // Only plot data from 1950 to present
    const startYear = 1950
    const endYear = new Date().getFullYear()
    const series = data.filter((d) => d.year >= startYear && d.year <= endYear)

    const plot = Plot.plot({
      width: el.clientWidth || 280,
      height: 140,
      marginTop: 8,
      marginRight: 8,
      marginBottom: 28,
      marginLeft: 40,
      x: {
        label: null,
        domain: [startYear, endYear],
        ticks: 4,
        tickFormat: (d) => String(Math.round(d)),
      },
      y: { label: null, grid: true, nice: true },
      marks: [
        Plot.rectY(series, {
          x: 'year',
          interval: 1,
          y: 'records',
          fill: '#0f7c86',
          title: (d) => `${d.year}: ${d.records.toLocaleString()} records`,
        }),
      ],
      style: {
        fontSize: '10px',
        color: '#555',
        background: 'transparent',
      },
    })

    clearPlot()
    el.replaceChildren(plot)
    plotNode = plot

    return () => clearPlot()
  })

  function clearPlot() {
    plotNode?.remove()
    plotNode = null
    if (chartEl) chartEl.replaceChildren()
  }

  onDestroy(clearPlot)
</script>

<section class="chart-block">
  <header>
    <h2>{title}</h2>
  </header>

  {#if loading}
    <p class="status">Loading...</p>
  {:else if rows.length === 0}
    <p class="status">No results</p>
  {:else}
    <div class="chart" bind:this={chartEl}></div>
  {/if}

  {#if downloadHref}
    <button
      type="button"
      class="download"
      onclick={() => {
        window.location.href = downloadHref
      }}
    >
      Download as CSV
    </button>
    <p>* Downloads can take up to a few minutes, keep this window open.</p>
  {/if}
</section>

<style>
  .chart-block {
    min-width: 0;
    padding: 1rem;
    background: #fff;
    border-radius: 8px;
  }

  header {
    margin-bottom: 0.4rem;
  }

  h2 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
  }

  .status {
    margin: 0;
    font-size: 0.8rem;
    color: #555;
  }

  .chart {
    width: 100%;
  }

  .chart :global(svg) {
    display: block;
    max-width: 100%;
    height: auto;
  }

  .download {
    margin-top: 0.65rem;
    font: inherit;
    font-size: 0.8rem;
    padding: 0.25rem 0.55rem;
    cursor: pointer;
  }
</style>
