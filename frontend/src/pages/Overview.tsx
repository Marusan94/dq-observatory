import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import PredictiveScoreBadge from '../components/PredictiveScoreBadge'

function health(c: any): { label: string; score: number } {
  const s = Math.round(100 - (c.missing_rate * 100 * 0.6) - (c.constant ? 15 : 0))
  const score = Math.max(0, Math.min(100, s))
  return { label: score >= 85 ? 'Good' : score >= 60 ? 'Review' : 'Critical', score }
}

export default function Overview() {
  const [sp] = useSearchParams()
  const dsId = sp.get('dataset')
  const ds = useQuery({ queryKey: ['datasets-list'], queryFn: () => api('/api/v1/datasets?page_size=20') })
  const id = dsId || ds.data?.items?.[0]?.id
  const q = useQuery({ queryKey: ['quality', id], queryFn: () => api(`/api/v1/datasets/${id}/quality`), enabled: !!id })
  const trend = useQuery({ queryKey: ['trend', id], queryFn: () => api(`/api/v1/datasets/${id}/quality/trend`), enabled: !!id })
  const prof = useQuery({ queryKey: ['profile', id], queryFn: () => api(`/api/v1/datasets/${id}/profile`), enabled: !!id })
  const dims = q.data?.dimensions?.dimensions || q.data?.dimensions || {}
  const contrib = q.data?.dimensions?.contributions || {}
  const data = Object.entries(dims).filter(([k]) => k !== 'note').map(([k, v]: any) => ({ name: k, v: typeof v === 'object' ? v.score : v }))
  const tdata = (trend.data?.versions || []).map((v: any) => ({ name: `v${v.version_number}`, score: v.quality_score }))
  return (
    <div>
      <h2 className="text-xl font-semibold">Data Quality Overview</h2>
      <p className="text-sm text-neutral-400">What is the quality? Why? Where? What can I do?</p>
      {!id ? <div className="card mt-4">No quality analysis yet. <a className="underline" href="/upload">Run analysis</a></div> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <div className="card"><div className="text-xs text-neutral-400">Quality Score</div>
              <div className="text-3xl font-bold">{q.data?.score ?? q.data?.dimensions?.overall ?? '—'}</div>
              <div className="text-xs text-neutral-500">Calculated per configured rules — not absolute truth.</div></div>
            <div className="card"><div className="text-xs text-neutral-400">Ruleset</div><div>{q.data?.ruleset}</div></div>
            <div className="card"><div className="text-xs text-neutral-400">Status</div><div>{q.data?.status}</div></div>
            <div className="card"><div className="text-xs text-neutral-400">Predicho</div>
              <PredictiveScoreBadge
                datasetId={id}
                currentScore={q.data?.score ?? q.data?.dimensions?.overall ?? 0}
              /></div>
          </div>
          <div className="card mt-3"><h3 className="text-sm font-medium mb-2">Quality dimensions</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data}><XAxis dataKey="name" tick={{ fill: '#aaa', fontSize: 12 }} /><YAxis domain={[0, 100]} tick={{ fill: '#aaa' }} /><Tooltip /><Bar dataKey="v" fill="#7dd3fc" /></BarChart>
            </ResponsiveContainer>
            {Object.keys(contrib).length > 0 && (
              <table className="dq mt-2"><thead><tr><th>Dimension</th><th>Weight</th><th>Score</th><th>Contribution</th></tr></thead>
                <tbody>{Object.entries(contrib).map(([k, v]: any) => (
                  <tr key={k}><td>{k}</td><td>{v.weight}</td><td>{v.score}</td><td>{v.contribution}/{v.weight}</td></tr>))}</tbody></table>)}
          </div>
          {tdata.length > 1 && (
            <div className="card mt-3"><h3 className="text-sm font-medium mb-2">Quality trend</h3>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={tdata}><XAxis dataKey="name" tick={{ fill: '#aaa' }} /><YAxis domain={[0, 100]} tick={{ fill: '#aaa' }} /><Tooltip /><Line type="monotone" dataKey="score" stroke="#a3e635" dot /></LineChart>
              </ResponsiveContainer></div>)}
          {(prof.data?.profile?.columns?.length > 0) && (
            <div className="card mt-3 overflow-x-auto"><h3 className="text-sm font-medium mb-2">Column health</h3>
              <table className="dq"><thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Unique</th><th>PII</th><th>Health</th></tr></thead>
                <tbody>{prof.data.profile.columns.slice(0, 20).map((c: any) => {
                  const h = health(c)
                  const isPii = (prof.data?.profile?.pii || []).some((p: any) => p.column === c.name)
                  return (<tr key={c.name}><td><Link className="underline" to={`/column?dataset=${id}&column=${encodeURIComponent(c.name)}`}>{c.name}</Link></td>
                    <td>{c.semantic_type}</td><td>{(c.missing_rate * 100).toFixed(1)}%</td>
                    <td>{(c.unique_rate * 100).toFixed(1)}%</td>
                    <td>{isPii ? <span className="badge" style={{background:'#374151'}}>PII</span> : <span className="text-neutral-500">—</span>}</td>
                    <td><span className="badge">{h.score} · {h.label}</span></td></tr>)
                })}</tbody></table></div>)}
        </>
      )}
    </div>
  )
}
