import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

export default function Drift() {
  const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=20') })
  const [dataset, setDataset] = useState('')
  const [fromV, setFromV] = useState('')
  const [toV, setToV] = useState('')
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const id = dataset || ds.data?.items?.[0]?.id || ''

  async function run() {
    setError(''); setResult(null)
    if (!id || !fromV || !toV) { setError('Pick a dataset and both version IDs.'); return }
    try {
      const r = await api(`/api/v1/${id}/drift?from_version=${encodeURIComponent(fromV)}&to_version=${encodeURIComponent(toV)}`)
      setResult(r)
    } catch (e: any) { setError(e.message) }
  }

  const issues = result?.issues || []
  return (
    <div><h2 className="text-xl font-semibold">Drift detection</h2>
      <p className="text-sm text-neutral-400">Schema + distribution drift between two versions (KS, PSI, KL, χ²).</p>
      <div className="card mt-3 flex flex-wrap gap-2 items-end max-w-3xl">
        <label className="text-sm">Dataset
          <select value={id} onChange={e => setDataset(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Dataset">
            {(ds.data?.items || []).map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select></label>
        <label className="text-sm">From version
          <input value={fromV} onChange={e => setFromV(e.target.value)} placeholder="version id" className="ml-2 bg-neutral-900 p-2 rounded text-sm w-56" aria-label="From version" /></label>
        <label className="text-sm">To version
          <input value={toV} onChange={e => setToV(e.target.value)} placeholder="version id" className="ml-2 bg-neutral-900 p-2 rounded text-sm w-56" aria-label="To version" /></label>
        <button className="badge" onClick={run}>Detect drift</button>
      </div>
      {error && <p className="text-sm mt-2 text-red-400" role="alert">{error}</p>}
      {result && (
        <div className="card mt-3">
          <h3 className="text-sm font-medium">Issues ({issues.length})</h3>
          {issues.length === 0 && <p className="text-sm text-neutral-500">No drift issues.</p>}
          <ul className="text-sm flex flex-col gap-1 mt-1">
            {issues.map((i: any, k: number) => (
              <li key={k}><span className="badge">{i.severity || 'INFO'}</span> <span className="text-neutral-500">{i.column || ''}</span> {i.description || JSON.stringify(i)}</li>
            ))}
          </ul>
          <details className="mt-2"><summary className="text-xs text-neutral-400 cursor-pointer">Raw metrics</summary>
            <pre className="text-xs overflow-auto max-h-96 mt-1">{JSON.stringify(result.drift ?? result, null, 2)}</pre></details>
        </div>
      )}</div>
  )
}
