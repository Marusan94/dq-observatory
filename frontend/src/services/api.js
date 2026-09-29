export const API = import.meta.env?.VITE_API_URL || 'http://localhost:8000';
export async function api(path, opts = {}) {
    const r = await fetch(`${API}${path}`, opts);
    if (!r.ok)
        throw new Error(`${r.status} ${await r.text()}`);
    const ct = r.headers.get('content-type') || '';
    return ct.includes('json') ? r.json() : r.blob();
}
// ---- AI Endpoints ----
export const aiApi = {
    // Chat
    ask: (question, datasetId, stream = false) => api('/api/v1/ai/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, dataset_id: datasetId, stream }),
    }),
    // Streaming chat - returns ReadableStream
    askStream: (question, datasetId) => {
        return fetch(`${API}/api/v1/ai/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, dataset_id: datasetId, stream: true }),
        });
    },
    // NL to Filter
    nlToFilter: (question, datasetId, versionId) => api('/api/v1/ai/nl-to-filter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, dataset_id: datasetId, version_id: versionId }),
    }),
    // Fix Suggestions
    suggestFix: (issueId, issue) => api('/api/v1/ai/suggest-fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ issue_id: issueId, issue }),
    }),
    // Preview Fix
    previewFix: (datasetId, versionId, operation, column, params) => api('/api/v1/ai/preview-fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, operation, column, params }),
    }),
    // Predict Score
    predictScore: (datasetId, versionId, proposedFixes) => api('/api/v1/ai/predict-score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, proposed_fixes: proposedFixes }),
    }),
    // Model Status
    modelStatus: () => api('/api/v1/ai/model-status'),
    // Chat Logs
    chatLogs: (datasetId, limit = 50) => api(`/api/v1/ai/chat-logs${datasetId ? `?dataset_id=${datasetId}` : ''}&limit=50`),
    // Fix Suggestions
    fixSuggestions: (issueId) => api(`/api/v1/ai/fix-suggestions/${issueId}`),
    acceptFixSuggestion: (suggestionId) => api(`/api/v1/ai/fix-suggestions/${suggestionId}/accept`, { method: 'PATCH' }),
    // Train Model
    trainModel: () => api('/api/v1/ai/train-model', { method: 'POST' }),
};
export default aiApi;
