import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

export default function Correlations() {
  const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=20') })
  const [dataset, setDataset] = useState('')
  const [minCorr, setMinCorr] = useState('0.3')
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const id = dataset || ds.data?.items?.[0]?.id || ''

  async function run() {
    setError(''); setResult(null)
    if (!id) { setError('Pick a dataset.'); return }
    try {
      const r = await api(`/api/v1/${id}/correlations?min_correlation=${encodeURIComponent(minCorr)}&max_pairs=100`)
      setResult(r)
    } catch (e: any) { setError(e.message) }
  }

  const pairs = result?.correlation_details || []
  const issues = result?.issues || []
  return (
    <div><h2 className="text-xl font-semibold">Correlations</h2>
      <p className="text-sm text-neutral-400">Pearson/Spearman/Kendall, Cramér's V, Theil's U, correlation ratio.</p>
      <div className="card mt-3 flex flex-wrap gap-2 items-end max-w-3xl">
        <label className="text-sm">Dataset
          <select value={id} onChange={e => setDataset(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Dataset">
            {(ds.data?.items || []).map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select></label>
        <label className="text-sm">Min |correlation|
          <input value={minCorr} onChange={e => setMinCorr(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-20" aria-label="Min correlation" /></label>
        <button className="badge" onClick={run}>Analyze</button>
      </div>
      {error && <p className="text-sm mt-2 text-red-400" role="alert">{error}</p>}
      {result && (
        <div className="card mt-3">
          <h3 className="text-sm font-medium">Top pairs ({pairs.length})</h3>
          {pairs.length === 0 && <p className="text-sm text-neutral-500">No pairs above threshold.</p>}
          <ul className="text-sm flex flex-col gap-1 mt-1">
            {pairs.slice(0, 50).map((p: any, k: number) => <li key={k} className="text-neutral-300">{JSON.stringify(p)}</li>)}
          </ul>
          {issues.length > 0 && (
            <div className="mt-2"><h3 className="text-sm font-medium">Issues ({issues.length})</h3>
              <ul className="text-sm flex flex-col gap-1 mt-1">
                {issues.map((i: any, k: number) => <li key={k}><span className="badge">{i.severity || 'INFO'}</span> {i.description || JSON.stringify(i)}</li>)}
              </ul></div>
          )}
        </div>
      )}</div>
  )
}
