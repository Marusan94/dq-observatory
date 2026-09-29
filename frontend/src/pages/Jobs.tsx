import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

export default function Jobs() {
  const qc = useQueryClient()
  const [role, setRole] = useState('admin')
  const [name, setName] = useState('nightly quality')
  const [cron, setCron] = useState('0 2 * * *')
  const [msg, setMsg] = useState('')
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: () => api('/api/v1/jobs') })

  async function create() {
    setMsg('')
    try {
      await api('/api/v1/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Role': role },
        body: JSON.stringify({ name, cron_expression: cron }),
      })
      setMsg('Job created.')
      qc.invalidateQueries({ queryKey: ['jobs'] })
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  async function trigger(id: string) {
    setMsg('')
    try {
      await api(`/api/v1/jobs/${id}/run`, { method: 'POST', headers: { 'X-Role': role } })
      setMsg('Run triggered.')
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  async function pause(id: string) {
    setMsg('')
    try {
      await api(`/api/v1/jobs/${id}/pause`, { method: 'POST', headers: { 'X-Role': role } })
      setMsg('Job paused.')
      qc.invalidateQueries({ queryKey: ['jobs'] })
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  async function resume(id: string) {
    setMsg('')
    try {
      await api(`/api/v1/jobs/${id}/resume`, { method: 'POST', headers: { 'X-Role': role } })
      setMsg('Job resumed.')
      qc.invalidateQueries({ queryKey: ['jobs'] })
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  return (
    <div><h2 className="text-xl font-semibold">Scheduled jobs</h2>
      <p className="text-sm text-neutral-400">Cron-based quality runs. Mutations need <span className="badge">schedule:manage</span> (owner/admin).</p>
      <div className="card mt-3 flex flex-wrap gap-2 items-end max-w-2xl">
        <label className="text-sm">Role
          <select value={role} onChange={e => setRole(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Role">
            {['viewer', 'editor', 'admin', 'owner'].map(r => <option key={r}>{r}</option>)}
          </select></label>
        <label className="text-sm">Name
          <input value={name} onChange={e => setName(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Job name" /></label>
        <label className="text-sm">Cron
          <input value={cron} onChange={e => setCron(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-32" aria-label="Cron expression" /></label>
        <button className="badge" onClick={create}>Create job</button>
      </div>
      {msg && <p className="text-sm mt-2" role="status">{msg}</p>}
      <div className="card mt-3">
        {jobs.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
        {(jobs.data || []).map((j: any) => (
          <div key={j.id} className="flex items-center justify-between border-b border-neutral-800 py-2 text-sm">
            <div><span className="font-medium">{j.name}</span>
              <span className="text-neutral-500"> · {j.cron} · {j.status} · next {j.next_run || '—'}</span></div>
            <div className="flex gap-1">
              <button className="badge" onClick={() => trigger(j.id)}>Run now</button>
              {j.status === 'PAUSED' ? (
                <button className="badge" onClick={() => resume(j.id)}>Resume</button>
              ) : (
                <button className="badge" onClick={() => pause(j.id)}>Pause</button>
              )}
            </div>
          </div>
        ))}
        {jobs.data?.length === 0 && <p className="text-sm text-neutral-500">No jobs yet.</p>}
      </div></div>
  )
}
