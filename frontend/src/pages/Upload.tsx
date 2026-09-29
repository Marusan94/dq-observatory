import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, API } from '../services/api'
import { loadSettings } from './Settings'

export default function Upload() {
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const qc = useQueryClient()
  async function onFile(f: File) {
    setBusy(true)
    setMsg('Uploading…')
    const fd = new FormData()
    fd.append('file', f)
    try {
      const ds = await api('/api/v1/datasets', { method: 'POST', body: fd })
      setMsg(`Dataset uploaded (${ds.rows} rows). Running analysis…`)
      const st = loadSettings()
      const run = await api(`/api/v1/datasets/${ds.id}/quality/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ruleset: `${st.profile}-v1`, config: { country: st.country, dateFormat: st.dateFormat } }) })
      setMsg(`Analysis completed. Score ${run.score.overall}/100 with ${run.issues_count} issues.`)
      qc.invalidateQueries()
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
    finally { setBusy(false) }
  }
  async function demo() {
    setBusy(true)
    setMsg('Loading demo dataset…')
    try {
      const r = await api('/api/v1/datasets/demo/seed', { method: 'POST' })
      setMsg(`Demo ready: ${r.rows} rows, score ${r.score}/100, ${r.issues_count} issues. Open Overview.`)
      qc.invalidateQueries()
    } catch (e: any) { setMsg(`Demo error: ${e.message}. Fallback: upload data/demo/customers_sales.csv manually.`) }
    finally { setBusy(false) }
  }
  return (
    <div>
      <h2 className="text-xl font-semibold">Analyze a dataset</h2>
      <p className="text-sm text-neutral-400">Profile, validate, clean and monitor tabular datasets.</p>
      <div className="card mt-4" onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f && !busy) onFile(f) }}>
        <p className="text-sm">Drag &amp; drop CSV / XLSX / JSON here, or</p>
        <input type="file" accept=".csv,.xlsx,.xls,.json" aria-label="Upload dataset" disabled={busy}
          onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }} className="mt-2 text-sm" />
        <div className="mt-3 flex gap-2">
          <button className="badge" onClick={demo} disabled={busy}>{busy ? 'Working…' : 'Try demo dataset'}</button>
          <a className="badge" href={`${API}/docs`} target="_blank" rel="noreferrer">API docs</a>
        </div>
        {msg && <p className="mt-3 text-sm" role="status" aria-live="polite">{msg}</p>}
      </div>
    </div>
  )
}
