import { useState } from 'react'

const KEY = 'dq-settings'
export function loadSettings() {
  try { return { profile: 'general', country: 'US', dateFormat: 'ISO', missingTokens: 'N/A,NA,null,unknown,-,?', ...JSON.parse(localStorage.getItem(KEY) || '{}') } }
  catch { return { profile: 'general', country: 'US', dateFormat: 'ISO', missingTokens: 'N/A,NA,null,unknown,-,?' } }
}

export default function Settings() {
  const [s, setS] = useState(loadSettings())
  const [msg, setMsg] = useState('')
  function save() {
    localStorage.setItem(KEY, JSON.stringify(s))
    setMsg('Settings saved. They apply to the next analysis run.')
  }
  return (
    <div><h2 className="text-xl font-semibold">Settings</h2>
      <p className="text-sm text-neutral-400">Quality profile, phone country, date format, missing-value tokens.</p>
      <div className="card mt-3 flex flex-col gap-3 max-w-md">
        <label className="text-sm">Quality profile
          <select value={s.profile} onChange={e => setS({ ...s, profile: e.target.value })} className="ml-2 bg-neutral-900 p-2 rounded text-sm">
            {['general', 'crm', 'sales', 'education', 'custom'].map(p => <option key={p}>{p}</option>)}
          </select></label>
        <label className="text-sm">Phone country
          <input value={s.country} onChange={e => setS({ ...s, country: e.target.value.toUpperCase().slice(0, 2) })} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-20" aria-label="Phone country" /></label>
        <label className="text-sm">Date format
          <select value={s.dateFormat} onChange={e => setS({ ...s, dateFormat: e.target.value })} className="ml-2 bg-neutral-900 p-2 rounded text-sm">
            {['ISO', 'DD/MM/YYYY', 'MM/DD/YYYY'].map(p => <option key={p}>{p}</option>)}
          </select></label>
        <label className="text-sm">Missing tokens (comma-separated)
          <input value={s.missingTokens} onChange={e => setS({ ...s, missingTokens: e.target.value })} className="ml-2 bg-neutral-900 p-2 rounded text-sm w-full" aria-label="Missing tokens" /></label>
        <div><button className="badge" onClick={save}>Save</button></div>
        {msg && <p className="text-sm" role="status">{msg}</p>}
      </div></div>
  )
}
