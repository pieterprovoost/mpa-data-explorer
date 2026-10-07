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
    <p class="status">...</p>
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
      <button type="button" disabled={!canPrev} onclick={prev}>Previous</button>
      <button type="button" disabled={!canNext} onclick={next}>Next</button>
    </div>
  {/if}
</section>

<style>
  .table-block {
    min-width: 0;
    padding: 1rem;
    background: #fff;
    border-radius: 8px;
  }

  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.4rem;
  }

  h2 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
  }

  .meta,
  .status {
    margin: 0;
    font-size: 0.8rem;
    color: #555;
  }

  .scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }

  th,
  td {
    text-align: left;
    padding: 0.3rem 0.45rem;
    border-bottom: 1px solid #e5e5e5;
    vertical-align: top;
  }

  th {
    font-weight: 600;
    white-space: nowrap;
  }

  .pager {
    display: flex;
    gap: 0.4rem;
    margin-top: 0.45rem;
  }

  button {
    font: inherit;
    font-size: 0.8rem;
    padding: 0.25rem 0.55rem;
  }

  button:disabled {
    opacity: 0.45;
  }
</style>
