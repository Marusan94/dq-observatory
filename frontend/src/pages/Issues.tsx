import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, API } from '../services/api'
import AIFixCard from '../components/AIFixCard'

const SEVS = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
const CATS = ['', 'COMPLETENESS', 'VALIDITY', 'CONSISTENCY', 'UNIQUENESS', 'INTEGRITY', 'TYPE', 'FORMAT', 'ANOMALY', 'SEMANTIC']
const STATUSES = ['', 'OPEN', 'IGNORED', 'REVIEWED', 'FIXED']

export default function Issues() {
  const qc = useQueryClient()
  const [sev, setSev] = useState('')
  const [cat, setCat] = useState('')
  const [col, setCol] = useState('')
  const [st, setSt] = useState('')
  const [auto, setAuto] = useState('')
  const [search, setSearch] = useState('')
  const [sel, setSel] = useState<any>(null)
  const [toast, setToast] = useState('')
  const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') })
  const id = ds.data?.items?.[0]?.id
  const qs = new URLSearchParams({ page_size: '100' } as any)
  if (sev) qs.set('severity', sev)
  if (cat) qs.set('category', cat)
  if (col) qs.set('column', col)
  if (st) qs.set('status', st)
  if (auto) qs.set('auto_fix', auto === 'auto' ? 'true' : 'false')
  if (search) qs.set('search', search)
  const iss = useQuery({ queryKey: ['issues', id, qs.toString()],
    queryFn: () => api(`/api/v1/datasets/${id}/issues?${qs}`), enabled: !!id })

  async function applyFix(issue: any) {
    try {
      const r = await api(`/api/v1/issues/${issue.id}/fix`, { method: 'POST' })
      setToast(`Fix applied: ${r.operation} (${r.affected_rows} rows). New version created.`)
      qc.invalidateQueries()
    } catch (e: any) { setToast(`Cannot auto-fix: ${e.message}`) }
  }

  return (
    <div>
      <h2 className="text-xl font-semibold">Issues</h2>
      <p className="text-sm text-neutral-400">What is wrong? Combine severity · category · column · status · auto-fix · search.</p>
      <div className="mt-3 flex flex-wrap gap-2 items-center">
        <select value={sev} onChange={e => setSev(e.target.value)} aria-label="Severity" className="bg-neutral-900 text-sm p-2 rounded">
          {SEVS.map(s => <option key={s} value={s}>{s || 'Severity: all'}</option>)}
        </select>
        <select value={cat} onChange={e => setCat(e.target.value)} aria-label="Category" className="bg-neutral-900 text-sm p-2 rounded">
          {CATS.map(s => <option key={s} value={s}>{s || 'Category: all'}</option>)}
        </select>
        <input value={col} onChange={e => setCol(e.target.value)} placeholder="Column" aria-label="Column" className="bg-neutral-900 text-sm p-2 rounded w-32" />
        <select value={st} onChange={e => setSt(e.target.value)} aria-label="Status" className="bg-neutral-900 text-sm p-2 rounded">
          {STATUSES.map(s => <option key={s} value={s}>{s || 'Status: all'}</option>)}
        </select>
        <select value={auto} onChange={e => setAuto(e.target.value)} aria-label="Auto-fix" className="bg-neutral-900 text-sm p-2 rounded">
          <option value="">Fix: all</option><option value="auto">Auto-fix available</option><option value="manual">Review required</option>
        </select>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search…" aria-label="Search issues" className="bg-neutral-900 text-sm p-2 rounded w-36" />
      </div>
      {toast && <p className="mt-2 text-sm" role="status" aria-live="polite">{toast}</p>}
      <div className="flex gap-3 mt-3">
        <div className="card overflow-x-auto flex-1">
          <table className="dq"><thead><tr><th>Severity</th><th>Column</th><th>Description</th><th>Rows</th><th>%</th><th>Fix</th></tr></thead>
            <tbody>{(iss.data?.items || []).map((i: any) => (
              <tr key={i.id} onClick={() => setSel(i)} className="cursor-pointer hover:bg-neutral-900">
                <td><span className="badge">{i.severity}</span></td><td>{i.column || '—'}</td>
                <td className="max-w-md truncate" title={i.description}>{i.description}</td>
                <td>{i.row_count}</td><td>{i.percentage}</td><td>{i.auto_fix_available ? 'Auto' : 'Review'}</td></tr>))}
            </tbody></table>
          <p className="text-xs text-neutral-500 mt-2">Total: {iss.data?.total ?? 0}. Click a row for detail.</p>
          {!iss.data?.items?.length && <p className="text-sm text-neutral-400 mt-2">No issues detected — passes all configured rules.</p>}
        </div>
        {sel && (
          <aside className="card w-80 shrink-0" aria-label="Issue detail">
            <h3 className="font-medium text-sm">{sel.severity} · {sel.category}</h3>
            <p className="text-sm mt-1">{sel.description}</p>
            <dl className="text-xs text-neutral-400 mt-2 flex flex-col gap-1">
              <div>Column: <span className="text-neutral-200">{sel.column || '—'}</span></div>
              <div>Affected: <span className="text-neutral-200">{sel.row_count} rows ({sel.percentage}%)</span></div>
              <div>Rule: <span className="text-neutral-200">{sel.rule}</span></div>
              <div>Status: <span className="text-neutral-200">{sel.status}</span></div>
            </dl>
            {(sel.examples?.length > 0) && (
              <div className="mt-2"><div className="text-xs text-neutral-500">Examples</div>
                <pre className="text-xs bg-neutral-900 p-2 rounded overflow-x-auto">{JSON.stringify(sel.examples.slice(0, 5), null, 1).slice(0, 600)}</pre></div>)}
            <div className="mt-3 flex gap-2">
              {sel.auto_fix_available
                ? <button className="badge" onClick={() => applyFix(sel)}>Apply auto-fix</button>
                : <span className="badge">Review required — no safe auto-fix</span>}
              <AIFixCard issueId={sel.id} issue={sel} datasetId={id} versionId={sel.version_id} />
              <button className="badge" onClick={() => setSel(null)}>Close</button>
            </div>
            <a className="text-xs underline mt-2 inline-block" href={`${API}/docs`} target="_blank" rel="noreferrer">Configure rule via API</a>
          </aside>)}
      </div>
    </div>
  )
}
