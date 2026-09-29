import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

export default function Search() {
  const [q, setQ] = useState('')
  const [debounced, setDebounced] = useState('')
  const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') })
  const id = ds.data?.items?.[0]?.id

  const search = useQuery({
    queryKey: ['search', debounced],
    queryFn: () => api(`/api/v1/search?q=${encodeURIComponent(debounced)}&limit=10`),
    enabled: !!debounced && debounced.length >= 2,
  })

  return (
    <div>
      <h2 className="text-xl font-semibold">Search</h2>
      <p className="text-sm text-neutral-400">Find datasets, columns, issues, rules (2+ chars).</p>
      <div className="card mt-3">
        <input
          value={q}
          onChange={e => { setQ(e.target.value); if (e.target.value.length >= 2) setDebounced(e.target.value); else setDebounced('') }}
          placeholder="Search…" aria-label="Global search"
          className="bg-neutral-900 text-sm p-2 rounded w-full"
          autoFocus />
        {(search.isLoading || debounced) && <p className="text-xs text-neutral-500 mt-1">Searching…</p>}
        {search.data && !search.isLoading && (
          <>
            {(search.data.datasets?.length > 0) && (
              <div className="mt-3"><h3 className="text-xs text-neutral-400">Datasets</h3>
                <ul className="text-sm flex flex-col gap-1">
                  {search.data.datasets.map((d: any) => (
                    <li key={d.id}><a className="underline" href={`/?dataset=${d.id}`}>{d.name} ({d.rows} rows)</a></li>))}
                </ul></div>)}
            {(search.data.columns?.length > 0) && (
              <div className="mt-3"><h3 className="text-xs text-neutral-400">Columns</h3>
                <ul className="text-sm flex flex-col gap-1">
                  {search.data.columns.map((c: any) => (
                    <li key={c}><a className="underline" href={`/column?dataset=${id}&column=${encodeURIComponent(c)}`}>{c}</a></li>))}
                </ul></div>)}
            {(search.data.issues?.length > 0) && (
              <div className="mt-3"><h3 className="text-xs text-neutral-400">Issues</h3>
                <ul className="text-sm flex flex-col gap-1">
                  {search.data.issues.map((i: any) => (
                    <li key={i.id}><span className="badge">{i.severity}</span> {i.description}</li>))}
                </ul></div>)}
            {(search.data.rules?.length > 0) && (
              <div className="mt-3"><h3 className="text-xs text-neutral-400">Rules</h3>
                <ul className="text-sm flex flex-col gap-1">
                  {search.data.rules.map((r: any) => (
                    <li key={r.id}>{r.name} on {r.column}</li>))}
                </ul></div>)}
            {(!search.data?.datasets?.length && !search.data?.columns?.length && !search.data?.issues?.length && !search.data?.rules?.length) &&
              <p className="mt-2 text-sm text-neutral-400">No results for "{debounced}"</p>}
          </>
        )}
      </div>
    </div>
  )
}