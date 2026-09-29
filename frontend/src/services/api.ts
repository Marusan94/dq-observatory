export const API = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

export async function api(path: string, opts: RequestInit = {}) {
  const r = await fetch(`${API}${path}`, opts)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  const ct = r.headers.get('content-type') || ''
  return ct.includes('json') ? r.json() : r.blob()
}

// ---- AI Endpoints ----
export const aiApi = {
  // Chat
  ask: (question: string, datasetId?: string, stream = false) =>
    api('/api/v1/ai/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, dataset_id: datasetId, stream }),
    }),

  // Streaming chat - returns ReadableStream
  askStream: (question: string, datasetId?: string) => {
    return fetch(`${API}/api/v1/ai/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, dataset_id: datasetId, stream: true }),
    })
  },

  // NL to Filter
  nlToFilter: (question: string, datasetId: string, versionId?: string) =>
    api('/api/v1/ai/nl-to-filter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, dataset_id: datasetId, version_id: versionId }),
    }),

  // Fix Suggestions
  suggestFix: (issueId?: string, issue?: any) =>
    api('/api/v1/ai/suggest-fix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ issue_id: issueId, issue }),
    }),

  // Preview Fix
  previewFix: (datasetId: string, versionId: string | undefined, operation: string, column: string, params: any) =>
    api('/api/v1/ai/preview-fix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, operation, column, params }),
    }),

  // Predict Score
  predictScore: (datasetId: string, versionId: string | undefined, proposedFixes: any[]) =>
    api('/api/v1/ai/predict-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, proposed_fixes: proposedFixes }),
    }),

  // Model Status
  modelStatus: () => api('/api/v1/ai/model-status'),

  // Chat Logs
  chatLogs: (datasetId?: string, limit = 50) =>
    api(`/api/v1/ai/chat-logs${datasetId ? `?dataset_id=${datasetId}` : ''}&limit=50`),

  // Fix Suggestions
  fixSuggestions: (issueId: string) =>
    api(`/api/v1/ai/fix-suggestions/${issueId}`),

  acceptFixSuggestion: (suggestionId: string) =>
    api(`/api/v1/ai/fix-suggestions/${suggestionId}/accept`, { method: 'PATCH' }),

  // Train Model
  trainModel: () =>
    api('/api/v1/ai/train-model', { method: 'POST' }),
}

export default aiApi