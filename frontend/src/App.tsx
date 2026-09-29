import { Suspense, lazy } from 'react'
import { NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from './services/api'
import Tour from './components/Tour'

const Upload = lazy(() => import('./pages/Upload'))
const Overview = lazy(() => import('./pages/Overview'))
const Issues = lazy(() => import('./pages/Issues'))
const Cleaning = lazy(() => import('./pages/Cleaning'))
const Reports = lazy(() => import('./pages/Reports'))
const ColumnDetail = lazy(() => import('./pages/ColumnDetail'))
const Settings = lazy(() => import('./pages/Settings'))
const Search = lazy(() => import('./pages/Search'))
const Jobs = lazy(() => import('./pages/Jobs'))
const Webhooks = lazy(() => import('./pages/Webhooks'))
const Drift = lazy(() => import('./pages/Drift'))
const Correlations = lazy(() => import('./pages/Correlations'))
const Contracts = lazy(() => import('./pages/Contracts'))

const items = [
  ['/', 'Overview'], ['/upload', 'Datasets'], ['/issues', 'Issues'],
  ['/cleaning', 'Cleaning'], ['/reports', 'Reports'], ['/drift', 'Drift'],
  ['/correlations', 'Correlations'], ['/contracts', 'Contracts'], ['/jobs', 'Jobs'], ['/webhooks', 'Webhooks'],
  ['/search', 'Search'], ['/settings', 'Settings'],
]

function Skeleton() {
  return (
    <div aria-busy="true" aria-label="Loading">
      <div className="card mt-4 animate-pulse"><div className="h-6 w-1/3 bg-neutral-800 rounded" /></div>
      <div className="card mt-3 animate-pulse"><div className="h-40 bg-neutral-800 rounded" /></div>
    </div>
  )
}

export default function App() {
  const nav = useNavigate()
  const ds = useQuery({ queryKey: ['datasets'], queryFn: () => api('/api/v1/datasets?page_size=5') })
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-neutral-800 bg-[#101012] p-4 hidden md:block" aria-label="Main">
        <h1 className="text-sm font-semibold tracking-wide">DQ OBSERVATORY</h1>
        <p className="text-xs text-neutral-500 mb-4">v0.1 · dq-engine-0.1.0</p>
        <nav className="flex flex-col gap-1">
          {items.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-neutral-800 text-white' : 'text-neutral-400 hover:bg-neutral-900'}`}>{label}</NavLink>
          ))}
        </nav>
        <div className="mt-6 text-xs text-neutral-500">Dataset</div>
        <select aria-label="Dataset selector" className="mt-1 w-full bg-neutral-900 text-xs p-2 rounded"
          value={new URLSearchParams(window.location.search).get('dataset') || ds.data?.items?.[0]?.id || ''}
          onChange={e => nav(`/?dataset=${e.target.value}`)}>
          {(ds.data?.items || []).map((d: any) => (
            <option key={d.id} value={d.id}>{d.name} · {d.rows} rows</option>))}
        </select>
        <div className="mt-4 text-xs text-neutral-500">Recent datasets</div>
        <div className="mt-1 flex flex-col gap-1">
          {(ds.data?.items || []).map((d: any) => (
            <button key={d.id} className="text-left text-xs text-neutral-300 hover:text-white truncate"
              onClick={() => nav(`/?dataset=${d.id}`)}>{d.name} · {d.rows} rows</button>
          ))}
        </div>
      </aside>
      <main className="flex-1 p-4 md:p-8 max-w-6xl w-full">
        <Suspense fallback={<Skeleton />}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/issues" element={<Issues />} />
            <Route path="/cleaning" element={<Cleaning />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/column" element={<ColumnDetail />} />
            <Route path="/search" element={<Search />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/webhooks" element={<Webhooks />} />
            <Route path="/drift" element={<Drift />} />
            <Route path="/correlations" element={<Correlations />} />
            <Route path="/contracts" element={<Contracts />} />
          </Routes>
        </Suspense>
      </main>
      <Tour />
    </div>
  )
}
