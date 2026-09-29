import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'
import { aiApi } from '../services/api'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  tokensUsed?: number
  latencyMs?: number
}

interface FixSuggestion {
  operation: string
  column?: string
  params: Record<string, any>
  previewRows?: any[]
  estimatedFixed: number
  confidence: number
  reasoning: string
}

interface PredictiveScore {
  predictedScore: number
  delta: number
  confidenceInterval: [number, number]
  topFeatures: { feature: string; impact: number }[]
}

interface AIContextType {
  // Chat
  messages: ChatMessage[]
  isLoading: boolean
  streamError: string | null
  sendMessage: (question: string, datasetId?: string) => Promise<void>
  clearChat: () => void

  // Fix Suggestions
  fixSuggestions: FixSuggestion[]
  isFixLoading: boolean
  loadFixSuggestions: (issueId: string, issue?: any) => Promise<void>
  previewFix: (datasetId: string, versionId: string | undefined, operation: string, column: string, params: any) => Promise<any>
  acceptFix: (suggestionId: string) => Promise<void>

  // Predictive Score
  predictiveScore: PredictiveScore | null
  isScoreLoading: boolean
  loadPredictiveScore: (datasetId: string, versionId?: string, proposedFixes?: any[]) => Promise<void>

  // Model Status
  modelStatus: any
  loadModelStatus: () => Promise<void>
}

const AIContext = createContext<AIContextType | null>(null)

export function AIProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)

  const [fixSuggestions, setFixSuggestions] = useState<any[]>([])
  const [isFixLoading, setIsFixLoading] = useState(false)

  const [predictiveScore, setPredictiveScore] = useState<PredictiveScore | null>(null)
  const [isScoreLoading, setIsScoreLoading] = useState(false)

  const [modelStatus, setModelStatus] = useState<any>(null)

  const sendMessage = useCallback(async (question: string, datasetId?: string) => {
    setIsLoading(true)
    setStreamError(null)
    const userMsg = { role: 'user' as const, content: question, timestamp: Date.now() }
    setMessages(prev => [...prev, userMsg])

    try {
      const res = await fetch(`/api/v1/ai/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, dataset_id: datasetId, stream: true }),
      })

      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''
      let tokensUsed = 0
      let latencyMs = 0

      // Add placeholder for assistant message
      const assistantIndex = setMessages.length
      setMessages(prev => [...prev, { role: 'assistant', content: '', timestamp: Date.now() }])

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = new TextDecoder().decode(value)
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '))
        for (const line of lines) {
          const data = line.slice(6).trim()
          if (data === '[DONE]') continue
          try {
            const parsed = JSON.parse(data)
            if (parsed.token) {
              assistantContent += parsed.token
              setMessages(prev => {
                const next = [...prev]
                next[assistantIndex] = { ...next[assistantIndex], content: assistantContent }
                return next
              })
            }
            if (parsed.error) setStreamError(parsed.error)
          } catch { /* ignore */ }
        }
      }
      // Update final message with metadata (inside try)
      setMessages(prev => {
        const next = [...prev]
        next[assistantIndex] = { ...next[assistantIndex], content: assistantContent }
        return next
      })
    } catch (e: any) {
      setStreamError(e.message)
      // Remove empty assistant message on error
      setMessages(prev => prev.filter((_, i) => i !== setMessages.length - 1))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const clearChat = useCallback(() => {
    setMessages([])
    setStreamError(null)
  }, [])

  const loadFixSuggestions = useCallback(async (issueId: string, issue?: any) => {
    setIsFixLoading(true)
    try {
      const res = await fetch('/api/v1/ai/suggest-fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issue_id: issueId, issue }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setFixSuggestions(data.suggestions || [])
    } catch (e: any) {
      console.error('Fix suggestions error:', e)
      setFixSuggestions([])
    } finally {
      setIsFixLoading(false)
    }
  }, [])

  const previewFix = useCallback(async (datasetId: string, versionId: string | undefined, operation: string, column: string, params: any) => {
    const res = await fetch('/api/v1/ai/preview-fix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, operation, column, params }),
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }, [])

  const acceptFix = useCallback(async (suggestionId: string) => {
    const res = await fetch(`/api/v1/ai/fix-suggestions/${suggestionId}/accept`, { method: 'PATCH' })
    if (!res.ok) throw new Error(await res.text())
    // Optionally refresh fix suggestions
  }, [])

  const loadPredictiveScore = useCallback(async (datasetId: string, versionId?: string, proposedFixes: any[] = []) => {
    setIsScoreLoading(true)
    try {
      const res = await fetch('/api/v1/ai/predict-score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, proposed_fixes: proposedFixes }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setPredictiveScore({
        predictedScore: data.predicted_score,
        delta: data.delta,
        confidenceInterval: data.confidence_interval,
        topFeatures: data.top_features || [],
      })
    } catch (e: any) {
      console.error('Predictive score error:', e)
      setPredictiveScore(null)
    } finally {
      setIsScoreLoading(false)
    }
  }, [])

  const loadModelStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/ai/model-status')
      if (res.ok) setModelStatus(await res.json())
    } catch { /* ignore */ }
  }, [])

  // Load model status on mount
  useEffect(() => { loadModelStatus() }, [loadModelStatus])

  return (
    <AIContext.Provider value={{
      messages,
      isLoading,
      streamError,
      sendMessage,
      clearChat,
      fixSuggestions,
      isFixLoading,
      loadFixSuggestions,
      previewFix,
      acceptFix,
      predictiveScore,
      isScoreLoading,
      loadPredictiveScore,
      modelStatus,
      loadModelStatus,
    }}>
      {children}
    </AIContext.Provider>
  )
}

export function useAI() {
  const ctx = useContext(AIContext)
  if (!ctx) throw new Error('useAI must be used within AIProvider')
  return ctx
}