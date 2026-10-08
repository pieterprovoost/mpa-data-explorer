<script>
  import * as Plot from '@observablehq/plot'
  import { onDestroy } from 'svelte'

  let {
    title = 'Records over time',
    rows = [],
    loading = false,
    totalRecords = null,
    statsLoading = false,
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
      height: 148,
      marginTop: 10,
      marginRight: 10,
      marginBottom: 28,
      marginLeft: 42,
      x: {
        label: null,
        domain: [startYear, endYear],
        ticks: 4,
        tickFormat: (d) => String(Math.round(d)),
      },
      y: {
        label: null,
        grid: true,
        nice: true,
        tickFormat: (d) =>
          d >= 1000 ? `${Math.round(d / 1000)}k` : String(d),
      },
      marks: [
        Plot.ruleY([0], { stroke: '#e6ebef' }),
        Plot.ruleX(series, {
          x: 'year',
          y1: 0,
          y2: 'records',
          stroke: '#14212b',
          strokeWidth: 1.5,
          strokeLinecap: 'round',
          title: (d) => `${d.year}: ${d.records.toLocaleString()} records`,
        }),
      ],
      style: {
        fontSize: '10px',
        fontFamily: 'DM Sans, system-ui, sans-serif',
        color: '#5b6b78',
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
    {#if !statsLoading && totalRecords != null}
      <p class="total"><strong>{Number(totalRecords).toLocaleString()}</strong> records across all years</p>
    {/if}
  </header>

  {#if loading}
    <p class="status">Loading graph...</p>
  {:else if rows.length === 0}
    <p class="status">No results</p>
  {:else}
    <div class="chart" bind:this={chartEl}></div>
  {/if}
</section>

<style>
  .chart-block {
    min-width: 0;
    padding: 1.1rem 1.15rem;
    background: #fff;
    border: 1px solid rgb(255 255 255 / 0.7);
    border-radius: 14px;
    box-shadow: 0 1px 2px rgb(20 33 43 / 0.04), 0 10px 28px rgb(20 33 43 / 0.08);
  }

  header {
    margin-bottom: 0.55rem;
  }

  h2 {
    margin: 0;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.05rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: #14212b;
  }

  .total {
    margin: 0.3rem 0 0;
    font-size: 0.86rem;
    color: #5b6b78;
  }

  .total strong {
    color: #14212b;
    font-weight: 700;
  }

  .status {
    margin: 0;
    font-size: 0.82rem;
    color: #5b6b78;
  }

  .chart {
    width: 100%;
  }

  .chart :global(svg) {
    display: block;
    max-width: 100%;
    height: auto;
  }
</style>
