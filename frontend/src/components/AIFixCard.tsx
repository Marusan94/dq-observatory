import { useState } from 'react'
import { Loader2, Zap, Check, X, Eye, Zap as ZapIcon } from 'lucide-react'
import { useAI } from '../context/AIContext'

interface AIFixCardProps {
  issueId: string
  issue: {
    severity: string
    category: string
    column?: string
    description: string
    examples?: any[]
    row_count: number
  }
  datasetId: string
  versionId?: string
}

export default function AIFixCard({ issueId, issue, datasetId, versionId }: AIFixCardProps) {
  const {
    fixSuggestions,
    isFixLoading,
    loadFixSuggestions,
    previewFix,
    acceptFix,
  } = useAI()

  const [showModal, setShowModal] = useState(false)
  const [selectedFix, setSelectedFix] = useState<any>(null)
  const [previewData, setPreviewData] = useState<any>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)

  const handleSuggest = async () => {
    await loadFixSuggestions(issueId, {
      severity: issue.severity,
      category: issue.category,
      column: issue.column,
      description: issue.description,
      examples: issue.examples?.slice(0, 5),
      row_count: issue.row_count,
    })
    setShowModal(true)
  }

  const handlePreview = async (fix: any) => {
    setSelectedFix(fix)
    setPreviewData(null)
    setIsPreviewLoading(true)
    try {
      const res = await previewFix(
        datasetId,
        versionId,
        fix.operation,
        fix.column || issue.column || '',
        fix.params || {}
      )
      setPreviewData(res)
    } catch (e: any) {
      console.error('Preview error:', e)
    } finally {
      setIsPreviewLoading(false)
    }
  }

  const handleAccept = async (fixId: string) => {
    try {
      await acceptFix(fixId)
      alert('Fix marcado como aceptado')
    } catch (e: any) {
      alert('Error: ' + e.message)
    }
  }

  if (!issueId) return null

  return (
    <div>
      <button
        onClick={handleSuggest}
        disabled={useAI().isFixLoading}
        className="badge bg-brass/20 text-brass hover:bg-brass/30 flex items-center gap-1"
        aria-label="Sugerir fix con IA"
      >
        <Zap className="w-3 h-3" /> Fix IA
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-label="Sugerencias de fix IA">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowModal(false)} />
          <div className="relative w-full max-w-2xl max-h-[90vh] bg-[#161618] border border-neutral-700 rounded-xl shadow-2xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-neutral-700 flex items-center justify-between">
              <h3 className="font-semibold text-white">Sugerencias de fix para: {issue.column || 'dataset'}</h3>
              <button onClick={() => setShowModal(false)} className="p-1 rounded hover:bg-neutral-800" aria-label="Cerrar"><X className="w-5 h-5 text-neutral-400" /></button>
            </div>

            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {isPreviewLoading && selectedFix && (
                <div className="mb-4 p-3 bg-brass/10 border border-brass/30 rounded-lg text-sm text-brass flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" /> Generando preview...
                </div>
              )}

              {fixSuggestions.length === 0 && !isPreviewLoading && (
                <div className="text-center py-8 text-neutral-500">
                  <p>No hay sugerencias automáticas para este issue.</p>
                  <p className="text-xs text-neutral-500 mt-1">Intenta revisar el issue manualmente.</p>
                </div>
              )}

              {fixSuggestions.map((fix, i) => (
                <div key={i} className="mb-4 p-4 bg-neutral-900/50 border border-neutral-700 rounded-lg">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <ZapIcon className="w-4 h-4 text-brass" />
                        <code className="bg-neutral-800 px-2 py-0.5 rounded text-xs font-mono text-brass">{fix.operation}</code>
                        <span className="text-xs px-2 py-0.5 rounded bg-neutral-800 text-neutral-400">{fix.column || issue.column}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-brass/20 text-brass">{(fix.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-sm text-neutral-300">{fix.reasoning}</p>
                      <p className="text-xs text-neutral-500 mt-1">~{fix.estimatedFixed} filas afectadas</p>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => handlePreview(fix)}
                        className="px-3 py-1 text-xs bg-neutral-800 hover:bg-neutral-700 rounded text-neutral-300 flex items-center gap-1"
                        aria-label="Ver preview"
                      >
                        <Eye className="w-3 h-3" /> Preview
                      </button>
                      <button
                        onClick={() => handleAccept(`fix-${i}`)}
                        className="px-3 py-1 text-xs bg-brass/20 hover:bg-brass/30 text-brass rounded"
                        aria-label="Aceptar fix"
                      >
                        <Check className="w-3 h-3 mr-1" /> Aceptar
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-neutral-700 flex justify-end gap-2">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 rounded text-neutral-300">Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}