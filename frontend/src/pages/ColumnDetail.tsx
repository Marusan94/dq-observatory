import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

export default function ColumnDetail() {
  const [sp] = useSearchParams()
  const dsId = sp.get('dataset')
  const col = sp.get('column')
  const ds = useQuery({ queryKey: ['datasets-list'], queryFn: () => api('/api/v1/datasets?page_size=20') })
  const id = dsId || ds.data?.items?.[0]?.id
  const det = useQuery({ queryKey: ['col', id, col],
    queryFn: () => api(`/api/v1/datasets/${id}/columns/${encodeURIComponent(col || '')}`),
    enabled: !!(id && col) })
  const c = det.data?.column
  return (
    <div>
      <Link to="/" className="text-xs underline text-neutral-400">← Overview</Link>
      <h2 className="text-xl font-semibold mt-1">Column: {col || '—'}</h2>
      {!col ? <div className="card mt-4 text-sm">Pick a column from the Overview health table.</div>
        : !c ? <div className="card mt-4 text-sm">Loading…</div> : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
              <div className="card"><div className="text-xs text-neutral-400">Semantic type</div><div>{c.semantic_type} ({c.confidence})</div>
                <div className="text-xs text-neutral-500">physical: {c.physical_type}</div></div>
              <div className="card"><div className="text-xs text-neutral-400">Missing</div><div>{c.missing} ({(c.missing_rate * 100).toFixed(2)}%)</div></div>
              <div className="card"><div className="text-xs text-neutral-400">Unique</div><div>{c.unique} ({(c.unique_rate * 100).toFixed(1)}%)</div></div>
              <div className="card"><div className="text-xs text-neutral-400">Flags</div>
                <div className="text-xs">{[c.constant && 'constant', c.high_cardinality && 'high-cardinality', c.potential_identifier && 'potential-identifier'].filter(Boolean).join(' · ') || '—'}</div></div>
            </div>
            <div className="card mt-3"><h3 className="text-sm font-medium mb-2">Top values</h3>
              <pre className="text-xs bg-neutral-900 p-2 rounded overflow-x-auto">{JSON.stringify(c.top_values, null, 1).slice(0, 800)}</pre></div>
            <div className="card mt-3"><h3 className="text-sm font-medium mb-2">Issues ({(det.data?.issues || []).length})</h3>
              {(det.data?.issues || []).map((i: any, k: number) => (
                <p key={k} className="text-sm"><span className="badge">{i.severity}</span> {i.description}</p>))}
              {!(det.data?.issues || []).length && <p className="text-sm text-neutral-400">No issues for this column.</p>}</div>
          </>
        )}
    </div>
  )
}
