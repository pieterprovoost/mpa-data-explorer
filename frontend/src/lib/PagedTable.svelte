<script>
  let {
    title = '',
    columns = [],
    rows = [],
    total = 0,
    skip = $bindable(0),
    size = 10,
    loading = false,
  } = $props()

  const from = $derived(total === 0 ? 0 : skip + 1)
  const to = $derived(Math.min(skip + rows.length, total))
  const canPrev = $derived(skip > 0)
  const canNext = $derived(skip + size < total)

  function prev() {
    if (canPrev) skip = Math.max(0, skip - size)
  }

  function next() {
    if (canNext) skip = skip + size
  }

  function cell(row, column) {
    const value = row[column.key]
    return column.format ? column.format(value, row) : (value ?? '')
  }
</script>

<section class="table-block">
  <header>
    <h2>{title}</h2>
    {#if !loading && total > 0}
      <span class="meta">{from}–{to} of {total}</span>
    {/if}
  </header>

  {#if loading}
    <p class="status">Loading…</p>
  {:else if total === 0}
    <p class="status">No results</p>
  {:else}
    <div class="scroll">
      <table>
        <thead>
          <tr>
            {#each columns as column}
              <th>{column.label}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each rows as row}
            <tr>
              {#each columns as column}
                <td>{cell(row, column)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="pager">
      <button type="button" class="btn" disabled={!canPrev} onclick={prev}>
        Previous
      </button>
      <button type="button" class="btn" disabled={!canNext} onclick={next}>
        Next
      </button>
    </div>
  {/if}
</section>

<style>
  .table-block {
    min-width: 0;
    padding: 1.1rem 1.15rem;
    background: #fff;
    border: 1px solid rgb(255 255 255 / 0.7);
    border-radius: 14px;
    box-shadow: 0 1px 2px rgb(20 33 43 / 0.04), 0 10px 28px rgb(20 33 43 / 0.08);
  }

  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
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

  .meta,
  .status {
    margin: 0;
    font-size: 0.78rem;
    color: #5b6b78;
  }

  .scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }

  th,
  td {
    text-align: left;
    padding: 0.45rem 0.2rem;
    border-bottom: 1px solid #e6ebef;
    vertical-align: top;
  }

  th {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5b6b78;
    white-space: nowrap;
  }

  td {
    color: #14212b;
    font-weight: 500;
  }

  .pager {
    display: flex;
    gap: 0.45rem;
    margin-top: 0.7rem;
  }

  .btn {
    min-height: 2rem;
    padding: 0.35rem 0.8rem;
    border: 1px solid #d7dee5;
    border-radius: 10px;
    background: #fff;
    color: #14212b;
    font: inherit;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    transition:
      background 120ms ease,
      border-color 120ms ease,
      opacity 120ms ease;
  }

  .btn:hover:not(:disabled) {
    background: #f4f7f8;
    border-color: #c5ced8;
  }

  .btn:disabled {
    opacity: 0.4;
    cursor: default;
  }
</style>
