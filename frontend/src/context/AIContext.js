import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useContext, useState, useCallback, useEffect } from 'react';
const AIContext = createContext(null);
export function AIProvider({ children }) {
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [streamError, setStreamError] = useState(null);
    const [fixSuggestions, setFixSuggestions] = useState([]);
    const [isFixLoading, setIsFixLoading] = useState(false);
    const [predictiveScore, setPredictiveScore] = useState(null);
    const [isScoreLoading, setIsScoreLoading] = useState(false);
    const [modelStatus, setModelStatus] = useState(null);
    const sendMessage = useCallback(async (question, datasetId) => {
        setIsLoading(true);
        setStreamError(null);
        const userMsg = { role: 'user', content: question, timestamp: Date.now() };
        setMessages(prev => [...prev, userMsg]);
        try {
            const res = await fetch(`/api/v1/ai/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, dataset_id: datasetId, stream: true }),
            });
            if (!res.ok)
                throw new Error(`${res.status} ${await res.text()}`);
            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            let assistantContent = '';
            let tokensUsed = 0;
            let latencyMs = 0;
            // Add placeholder for assistant message
            const assistantIndex = setMessages.length;
            setMessages(prev => [...prev, { role: 'assistant', content: '', timestamp: Date.now() }]);
            while (reader) {
                const { done, value } = await reader.read();
                if (done)
                    break;
                const chunk = new TextDecoder().decode(value);
                const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
                for (const line of lines) {
                    const data = line.slice(6).trim();
                    if (data === '[DONE]')
                        continue;
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.token) {
                            assistantContent += parsed.token;
                            setMessages(prev => {
                                const next = [...prev];
                                next[assistantIndex] = { ...next[assistantIndex], content: assistantContent };
                                return next;
                            });
                        }
                        if (parsed.error)
                            setStreamError(parsed.error);
                    }
                    catch { /* ignore */ }
                }
            }
            // Update final message with metadata (inside try)
            setMessages(prev => {
                const next = [...prev];
                next[assistantIndex] = { ...next[assistantIndex], content: assistantContent };
                return next;
            });
        }
        catch (e) {
            setStreamError(e.message);
            // Remove empty assistant message on error
            setMessages(prev => prev.filter((_, i) => i !== setMessages.length - 1));
        }
        finally {
            setIsLoading(false);
        }
    }, []);
    const clearChat = useCallback(() => {
        setMessages([]);
        setStreamError(null);
    }, []);
    const loadFixSuggestions = useCallback(async (issueId, issue) => {
        setIsFixLoading(true);
        try {
            const res = await fetch('/api/v1/ai/suggest-fix', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ issue_id: issueId, issue }),
            });
            if (!res.ok)
                throw new Error(await res.text());
            const data = await res.json();
            setFixSuggestions(data.suggestions || []);
        }
        catch (e) {
            console.error('Fix suggestions error:', e);
            setFixSuggestions([]);
        }
        finally {
            setIsFixLoading(false);
        }
    }, []);
    const previewFix = useCallback(async (datasetId, versionId, operation, column, params) => {
        const res = await fetch('/api/v1/ai/preview-fix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, operation, column, params }),
        });
        if (!res.ok)
            throw new Error(await res.text());
        return res.json();
    }, []);
    const acceptFix = useCallback(async (suggestionId) => {
        const res = await fetch(`/api/v1/ai/fix-suggestions/${suggestionId}/accept`, { method: 'PATCH' });
        if (!res.ok)
            throw new Error(await res.text());
        // Optionally refresh fix suggestions
    }, []);
    const loadPredictiveScore = useCallback(async (datasetId, versionId, proposedFixes = []) => {
        setIsScoreLoading(true);
        try {
            const res = await fetch('/api/v1/ai/predict-score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_id: datasetId, version_id: versionId, proposed_fixes: proposedFixes }),
            });
            if (!res.ok)
                throw new Error(await res.text());
            const data = await res.json();
            setPredictiveScore({
                predictedScore: data.predicted_score,
                delta: data.delta,
                confidenceInterval: data.confidence_interval,
                topFeatures: data.top_features || [],
            });
        }
        catch (e) {
            console.error('Predictive score error:', e);
            setPredictiveScore(null);
        }
        finally {
            setIsScoreLoading(false);
        }
    }, []);
    const loadModelStatus = useCallback(async () => {
        try {
            const res = await fetch('/api/v1/ai/model-status');
            if (res.ok)
                setModelStatus(await res.json());
        }
        catch { /* ignore */ }
    }, []);
    // Load model status on mount
    useEffect(() => { loadModelStatus(); }, [loadModelStatus]);
    return (_jsx(AIContext.Provider, { value: {
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
        }, children: children }));
}
export function useAI() {
    const ctx = useContext(AIContext);
    if (!ctx)
        throw new Error('useAI must be used within AIProvider');
    return ctx;
}
