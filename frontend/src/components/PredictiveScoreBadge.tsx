import { useState } from 'react'
import { TrendingUp, TrendingDown, Minus, HelpCircle } from 'lucide-react'
import { useAI } from '../context/AIContext'

interface PredictiveScoreBadgeProps {
  datasetId: string
  versionId?: string
  currentScore: number
  proposedFixes?: any[]
  className?: string
}

export default function PredictiveScoreBadge({ datasetId, versionId, currentScore, proposedFixes = [], className = '' }: PredictiveScoreBadgeProps) {
  const { predictiveScore, isScoreLoading, loadPredictiveScore } = useAI()
  const [showTooltip, setShowTooltip] = useState(false)

  // Load on mount and when fixes change
  const load = () => loadPredictiveScore(datasetId, versionId, proposedFixes)

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      {isScoreLoading && (
        <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
          <span className="w-3 h-3 border-2 border-brass border-t-transparent rounded-full animate-spin" />
          Calculando...
        </span>
      )}

      {predictiveScore && !isScoreLoading && (
        <div className="inline-flex items-center gap-2 px-2 py-1 bg-neutral-900 border border-neutral-700 rounded-lg">
          <div className="text-right">
            <span className="text-2xl font-mono font-bold text-white">{predictiveScore.predictedScore.toFixed(1)}</span>
            <span className="text-xs text-neutral-500">/100</span>
          </div>
          <div className="flex flex-col items-start gap-1">
            <span className={`text-sm font-mono ${
              predictiveScore.delta > 0 ? 'text-green-400' :
              predictiveScore.delta < 0 ? 'text-red-400' : 'text-neutral-500'
            }`}>
              {predictiveScore.delta > 0 ? '+' : ''}{predictiveScore.delta.toFixed(1)}
            </span>
            <span className="text-[10px] text-neutral-500">
              CI: {predictiveScore.confidenceInterval[0].toFixed(0)}–{predictiveScore.confidenceInterval[1].toFixed(0)}
            </span>
          </div>
          <div className="relative" onMouseEnter={() => setShowTooltip(true)} onMouseLeave={() => setShowTooltip(false)}>
            <button className="p-1 text-neutral-500 hover:text-brass transition-colors" aria-label="Ver factores">
              <HelpCircle className="w-4 h-4" />
            </button>
            {showTooltip && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-neutral-900 border border-neutral-700 rounded-lg p-3 text-xs z-50">
                <div className="font-medium text-white mb-2">Factores principales:</div>
                <ul className="space-y-1">
                  {predictiveScore.topFeatures.map((f, i) => (
                    <li key={i} className="flex justify-between text-neutral-300">
                      <span>{f.feature}</span>
                      <span className={`font-mono ${f.impact < 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {f.impact > 0 ? '+' : ''}{f.impact.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}