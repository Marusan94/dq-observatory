import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, API } from '../services/api'

export default function Reports() {
  const qc = useQueryClient()
  const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') })
  const id = ds.data?.items?.[0]?.id
  const rep = useQuery({ queryKey: ['rep', id], queryFn: () => api(`/api/v1/datasets/${id}/report`), enabled: !!id })
  const vers = useQuery({ queryKey: ['vers', id], queryFn: () => api(`/api/v1/datasets/${id}/versions`), enabled: !!id })
  const ba = rep.data?.before_after

  // Export options state
  const [fmt, setFmt] = useState('csv')
  const [columns, setColumns] = useState('')
  const [filterCol, setFilterCol] = useState('')
  const [filterOp, setFilterOp] = useState('eq')
  const [filterVal, setFilterVal] = useState('')
  const [dateCol, setDateCol] = useState('')
  const [dateStart, setDateStart] = useState('')
  const [dateEnd, setDateEnd] = useState('')
  const [msg, setMsg] = useState('')

  const formats = ['csv', 'xlsx', 'json', 'parquet', 'delta', 'avro', 'zip']
  const operators = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'contains']

  function buildExportUrl() {
    const params = new URLSearchParams()
    params.set('format', fmt)
    if (columns) params.set('columns', columns)
    if (filterCol && filterOp && filterVal) {
      params.set('filter_col', filterCol)
      params.set('filter_op', filterOp)
      params.set('filter_val', filterVal)
    }
    if (dateStart && dateEnd && dateCol) {
      params.set('date_start', dateStart)
      params.set('date_end', dateEnd)
      params.set('date_column', dateCol)
    }
    return `${API}/api/v1/datasets/${id}/export?${params.toString()}`
  }

  async function download() {
    setMsg('')
    try {
      const res = await fetch(buildExportUrl(), { headers: { 'X-Role': 'owner' } })
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${id}_export.${fmt === 'delta' ? 'zip' : fmt}`
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
      document.body.removeChild(a)
      setMsg('Descarga iniciada.')
    } catch (e: any) {
      setMsg(`Error: ${e.message}`)
    }
  }

  function Lineage({ versions, operations }: any) {
    if (!versions?.length) return null
    const items = [...versions].reverse()
    return (
      <div className="relative pl-4 border-l border-neutral-800">
        {items.map((v: any, i: number) => {
          const ops = operations?.filter((o: any) => o.to === v.id) || []
          return (
            <div key={v.id} className="relative mb-4">
              <div className="absolute left-[-10px] top-1 w-3 h-3 rounded-full bg-neutral-800 border-2 border-[#0b0e1c]" />
              <div className="ml-4">
                <div className="font-medium">{v.label} <span className="text-xs text-neutral-500">({v.rows} rows, score {v.quality_score ?? '—'})</span></div>
                {ops.length > 0 && (
                  <div className="mt-1 ml-2 text-sm text-neutral-400">
                    {ops.map((o: any) => <div key={o.id} className="flex gap-1"><span className="badge text-xs">{o.op}</span><span>{o.column ? `(${o.column})` : ''}</span><span>{o.affected} rows</span></div>)}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div><h2 className="text-xl font-semibold">Reports & Export</h2>
      <p className="text-sm text-neutral-400">Can I communicate and take results elsewhere?</p>
      <div className="card mt-3">
        <div>Score: {rep.data?.quality_score?.overall} · Issues: {rep.data?.summary?.issues}</div>
        {ba && (
          <table className="dq mt-2"><thead><tr><th></th><th>Version</th><th>Rows</th><th>Score</th></tr></thead>
            <tbody>
              <tr><td>Before</td><td>{ba.before_version}</td><td>{ba.before_rows}</td><td>{ba.before_score ?? '—'}</td></tr>
              <tr><td>After</td><td>{ba.after_version}</td><td>{ba.after_rows}</td><td>{ba.after_score}</td></tr>
            </tbody></table>)}
        
        {/* Export Options */}
        <details className="mt-3 group">
          <summary className="cursor-pointer flex items-center gap-2 text-sm font-medium text-neutral-300">
            <span className="badge">⚙ Opciones de exportación</span>
            <span className="text-xs text-neutral-500 group-open:rotate-180 transition-transform">▼</span>
          </summary>
          <div className="mt-3 space-y-3 p-2 border-t border-neutral-800">
            <div>
              <label className="block text-xs text-neutral-400 mb-1">Formato</label>
              <select value={fmt} onChange={e => setFmt(e.target.value)} className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm">
                {formats.map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-neutral-400 mb-1">Columnas (coma-separadas, vacío = todas)</label>
              <input value={columns} onChange={e => setColumns(e.target.value)} placeholder="id,name,email" className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
              <div>
                <label className="block text-xs text-neutral-400 mb-1">Filtrar columna</label>
                <input value={filterCol} onChange={e => setFilterCol(e.target.value)} placeholder="email" className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1">Operador</label>
                <select value={filterOp} onChange={e => setFilterOp(e.target.value)} className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm">
                  {operators.map(op => <option key={op} value={op}>{op}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1">Valor</label>
                <input value={filterVal} onChange={e => setFilterVal(e.target.value)} placeholder="valor" className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1">Columna fecha</label>
                <input value={dateCol} onChange={e => setDateCol(e.target.value)} placeholder="created_at" className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-neutral-400 mb-1">Fecha inicio (ISO)</label>
                <input type="date" value={dateStart} onChange={e => setDateStart(e.target.value)} className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-neutral-400 mb-1">Fecha fin (ISO)</label>
                <input type="date" value={dateEnd} onChange={e => setDateEnd(e.target.value)} className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" />
              </div>
            </div>
          </div>
        </details>

        <div className="mt-2 flex flex-wrap gap-2">
          <button onClick={download} className="badge bg-brass text-black hover:bg-brass/80">Descargar</button>
          <a className="badge" href={`${API}/api/v1/datasets/${id}/report.html`} target="_blank" rel="noreferrer">HTML report</a>
        </div>
        {msg && <p className="mt-2 text-sm text-brass" role="status">{msg}</p>}
      </div>
      
      {(vers.data?.operations?.length > 0) && (
        <div className="card mt-3"><h3 className="text-sm font-medium mb-2">Data lineage</h3>
          <Lineage versions={vers.data?.versions} operations={vers.data?.operations} />
          <details className="mt-2"><summary className="text-sm text-neutral-400 cursor-pointer">Transformation history (flat)</summary>
            <ol className="text-sm flex flex-col gap-1 mt-2">
              {vers.data.operations.map((o: any) => (
                <li key={o.id}>{o.op}{o.column ? ` (${o.column})` : ''} — {o.affected} rows affected</li>))}
            </ol></details></div>)}
    </div>
  )
}