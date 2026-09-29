import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

export default function Contracts() {
  const qc = useQueryClient()
  const [role, setRole] = useState('editor')
  const [dataset, setDataset] = useState('')
  const [name, setName] = useState('brooklyn-events')
  const [cols, setCols] = useState('id,email,age')
  const [minScore, setMinScore] = useState('60')
  const [msg, setMsg] = useState('')
  const [check, setCheck] = useState<any>(null)

  const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=20') })
  const id = dataset || ds.data?.items?.[0]?.id || ''
  const list = useQuery({ queryKey: ['contracts', id], queryFn: () => api(`/api/v1/contracts?dataset_id=${id}`), enabled: !!id })

  async function create() {
    setMsg(''); setCheck(null)
    try {
      const schema: any = {}
      cols.split(',').map(s => s.trim()).filter(Boolean).forEach(c => { schema[c] = { physical_type: 'object', required: true } })
      const r = await api('/api/v1/contracts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Role': role },
        body: JSON.stringify({ dataset_id: id, name, schema, rules: [], sla: { min_score: Number(minScore) || 0 } }),
      })
      setMsg(`Contract ${r.id.slice(0, 8)}… created (v${r.version}).`)
      qc.invalidateQueries({ queryKey: ['contracts'] })
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  async function runCheck(cid: string) {
    setMsg(''); setCheck(null)
    try {
      const r = await api(`/api/v1/contracts/${cid}/check`, { method: 'POST' })
      setCheck(r)
      setMsg(r.passed ? 'Check passed — no breaking changes.' : `Check failed — ${r.violations.length} violation(s).`)
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  return (
    <div><h2 className="text-xl font-semibold">Data contracts</h2>
      <p className="text-sm text-neutral-400">Schema + SLA per dataset. Breaking-change checks on latest version. Writes need editor+.</p>
      <div className="card mt-3 flex flex-wrap gap-2 items-end max-w-3xl">
        <label className="text-sm">Role
          <select value={role} onChange={e => setRole(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Role">
            {['viewer', 'editor', 'admin', 'owner'].map(r => <option key={r}>{r}</option>)}
          </select></label>
        <label className="text-sm">Dataset
          <select value={id} onChange={e => setDataset(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Dataset">
            {(ds.data?.items || []).map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select></label>
        <label className="text-sm">Name
          <input value={name} onChange={e => setName(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Contract name" /></label>
        <label className="text-sm">Columns
          <input value={cols} onChange={e => setCols(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-48" aria-label="Contract columns" /></label>
        <label className="text-sm">Min score
          <input value={minScore} onChange={e => setMinScore(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-20" aria-label="Min score" /></label>
        <button className="badge" onClick={create}>Create contract</button>
      </div>
      {msg && <p className="text-sm mt-2" role="status">{msg}</p>}
      <div className="card mt-3">
        {(list.data || []).map((c: any) => (
          <div key={c.id} className="flex items-center justify-between border-b border-neutral-800 py-2 text-sm">
            <div><span className="font-medium">{c.name}</span>
              <span className="text-neutral-500"> · v{c.version} · {c.status} · {Object.keys(c.schema || {}).length} cols</span></div>
            <button className="badge" onClick={() => runCheck(c.id)}>Run check</button>
          </div>
        ))}
        {list.data?.length === 0 && <p className="text-sm text-neutral-500">No contracts yet.</p>}
      </div>
      {check && (
        <div className="card mt-3">
          <h3 className="text-sm font-medium">Check: {check.passed ? 'PASSED' : 'FAILED'}</h3>
          <ul className="text-sm flex flex-col gap-1 mt-1">
            {(check.violations || []).map((v: any, k: number) => (
              <li key={k}><span className="badge">{v.severity || 'INFO'}</span> {v.type} {v.column ? `(${v.column})` : ''}</li>
            ))}
          </ul>
        </div>
      )}</div>
  )
}
