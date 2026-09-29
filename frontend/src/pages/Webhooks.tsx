import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'

export default function Webhooks() {
  const qc = useQueryClient()
  const [role, setRole] = useState('admin')
  const [name, setName] = useState('alerts')
  const [url, setUrl] = useState('https://hooks.example.com/dq')
  const [events, setEvents] = useState('job_failed, drift_detected')
  const [msg, setMsg] = useState('')
  const whs = useQuery({ queryKey: ['webhooks'], queryFn: () => api('/api/v1/webhooks') })

  async function create() {
    setMsg('')
    try {
      await api('/api/v1/webhooks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Role': role },
        body: JSON.stringify({ name, url, events: events.split(',').map(s => s.trim()).filter(Boolean) }),
      })
      setMsg('Webhook created.')
      qc.invalidateQueries({ queryKey: ['webhooks'] })
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  async function remove(id: string) {
    setMsg('')
    try {
      await api(`/api/v1/webhooks/${id}`, { method: 'DELETE', headers: { 'X-Role': role } })
      setMsg('Webhook deleted.')
      qc.invalidateQueries({ queryKey: ['webhooks'] })
    } catch (e: any) { setMsg(`Error: ${e.message}`) }
  }

  return (
    <div><h2 className="text-xl font-semibold">Webhooks</h2>
      <p className="text-sm text-neutral-400">HMAC-signed alerts. Mutations need <span className="badge">webhook:manage</span> (owner/admin).</p>
      <div className="card mt-3 flex flex-wrap gap-2 items-end max-w-2xl">
        <label className="text-sm">Role
          <select value={role} onChange={e => setRole(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Role">
            {['viewer', 'editor', 'admin', 'owner'].map(r => <option key={r}>{r}</option>)}
          </select></label>
        <label className="text-sm">Name
          <input value={name} onChange={e => setName(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm" aria-label="Webhook name" /></label>
        <label className="text-sm">URL
          <input value={url} onChange={e => setUrl(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-64" aria-label="Webhook URL" /></label>
        <label className="text-sm">Events (comma-separated)
          <input value={events} onChange={e => setEvents(e.target.value)} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-64" aria-label="Events" /></label>
        <button className="badge" onClick={create}>Create webhook</button>
      </div>
      {msg && <p className="text-sm mt-2" role="status">{msg}</p>}
      <div className="card mt-3">
        {whs.isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
        {(whs.data || []).map((w: any) => (
          <div key={w.id} className="flex items-center justify-between border-b border-neutral-800 py-2 text-sm">
            <div><span className="font-medium">{w.name}</span>
              <span className="text-neutral-500"> · {w.url} · {(w.events || []).join(', ')}</span></div>
            <button className="badge" onClick={() => remove(w.id)}>Delete</button>
          </div>
        ))}
        {whs.data?.length === 0 && <p className="text-sm text-neutral-500">No webhooks yet.</p>}
      </div></div>
  )
}
