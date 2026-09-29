import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useVirtualizer } from '@tanstack/react-virtual'
import { api } from '../services/api'

const OPS = ['trim_whitespace', 'normalize_email', 'normalize_phone', 'remove_exact_duplicates', 'standardize_missing', 'parse_numeric', 'standardize_categories']

const ROW_HEIGHT = 36

export default function Cleaning() {
  const [op, setOp] = useState(OPS[0])
  const [col, setCol] = useState('email')
  const [msg, setMsg] = useState('')
  const [previewData, setPreviewData] = useState<any>(null)
  const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') })
  const id = ds.data?.items?.[0]?.id
  const previewDataQ = useQuery({
    queryKey: ['clean-preview', id],
    queryFn: () => api(`/api/v1/datasets/${id}/preview`),
    enabled: !!id,
  })
  async function preview() {
    setMsg('Preview…')
    try {
      const r = await api(`/api/v1/datasets/${id}/clean`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ operation: op, column: col, preview_only: true }) })
      setPreviewData(r.preview_data)
      setMsg(`Preview: affected ${r.preview_data?.affected_rows ?? '?'} rows.`)
    } catch (e: any) { setMsg(e.message) }
  }
  async function apply() {
    try {
      const r = await api(`/api/v1/datasets/${id}/clean`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ operation: op, column: col }) })
      setMsg(`Applied. ${r.before_rows} → ${r.after_rows} rows. New score ${r.new_quality_score}.`)
      setPreviewData(null)
    } catch (e: any) { setMsg(e.message) }
  }

  const data = previewDataQ.data?.rows || []
  const parentRef = React.useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 5,
  })

  return (
    <div><h2 className="text-xl font-semibold">Cleaning workspace</h2>
      <p className="text-sm text-neutral-400">How do I fix it? Preview first, apply creates a new version. Original never destroyed.</p>
      <div className="card mt-3 flex flex-wrap gap-2 items-center">
        <select value={op} onChange={e => setOp(e.target.value)} className="bg-neutral-900 text-sm p-2 rounded" aria-label="Operation">
          {OPS.map(o => <option key={o}>{o}</option>)}
        </select>
        <input value={col} onChange={e => setCol(e.target.value)} className="bg-neutral-900 text-sm p-2 rounded" aria-label="Column" placeholder="column (optional)" />
        <button className="badge" onClick={preview} disabled={!id}>Preview</button>
        <button className="badge" onClick={apply} disabled={!id}>Apply</button>
      </div>
      {msg && <p className="mt-2 text-sm" role="status">{msg}</p>}
      {(previewData || previewDataQ.data) && (
        <div className="card mt-3"><h3 className="text-sm font-medium mb-2">Preview</h3>
          {previewData?.before && <p className="text-xs text-neutral-500">Before (sample)</p>}
          {previewData?.before && <pre className="text-xs bg-neutral-900 p-2 rounded overflow-x-auto">{JSON.stringify(previewData.before, null, 1).slice(0, 500)}</pre>}
          {previewData?.after && <p className="text-xs text-neutral-500 mt-2">After (sample)</p>}
          {previewData?.after && <pre className="text-xs bg-neutral-900 p-2 rounded overflow-x-auto">{JSON.stringify(previewData.after, null, 1).slice(0, 500)}</pre>}
          {previewData?.affected_rows !== undefined && <p className="mt-1 text-sm">Affected rows: {previewData.affected_rows}</p>}
          {data.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-neutral-500">Current version sample (virtualized, {data.length} rows)</p>
              <div ref={parentRef} className="h-80 overflow-auto border border-neutral-800 rounded bg-neutral-950" style={{ width: '100%' }}>
                <table className="dq" style={{ height: data.length * ROW_HEIGHT }}>
                  <thead>
                    <tr style={{ position: 'sticky', top: 0, zIndex: 1, background: '#141416' }}>
                      {previewDataQ.data?.columns?.map((c: string, i: number) => (
                        <th key={i} style={{ width: 180 }}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {virtualizer.getVirtualItems().map((virtualRow) => (
                      <tr key={virtualRow.index} style={{ transform: `translateY(${virtualRow.start}px)` }}>
                        {data[virtualRow.index] && Object.values(data[virtualRow.index]).map((v, ci) => (
                          <td key={ci} style={{ width: 180, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {v === null || v === undefined ? <span className="text-neutral-500">—</span> : String(v).slice(0, 60)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}