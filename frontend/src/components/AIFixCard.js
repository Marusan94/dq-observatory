import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { Loader2, Zap, Check, X, Eye, Zap as ZapIcon } from 'lucide-react';
import { useAI } from '../context/AIContext';
export default function AIFixCard({ issueId, issue, datasetId, versionId }) {
    const { fixSuggestions, isFixLoading, loadFixSuggestions, previewFix, acceptFix, } = useAI();
    const [showModal, setShowModal] = useState(false);
    const [selectedFix, setSelectedFix] = useState(null);
    const [previewData, setPreviewData] = useState(null);
    const [isPreviewLoading, setIsPreviewLoading] = useState(false);
    const handleSuggest = async () => {
        await loadFixSuggestions(issueId, {
            severity: issue.severity,
            category: issue.category,
            column: issue.column,
            description: issue.description,
            examples: issue.examples?.slice(0, 5),
            row_count: issue.row_count,
        });
        setShowModal(true);
    };
    const handlePreview = async (fix) => {
        setSelectedFix(fix);
        setPreviewData(null);
        setIsPreviewLoading(true);
        try {
            const res = await previewFix(datasetId, versionId, fix.operation, fix.column || issue.column || '', fix.params || {});
            setPreviewData(res);
        }
        catch (e) {
            console.error('Preview error:', e);
        }
        finally {
            setIsPreviewLoading(false);
        }
    };
    const handleAccept = async (fixId) => {
        try {
            await acceptFix(fixId);
            alert('Fix marcado como aceptado');
        }
        catch (e) {
            alert('Error: ' + e.message);
        }
    };
    if (!issueId)
        return null;
    return (_jsxs("div", { children: [_jsxs("button", { onClick: handleSuggest, disabled: useAI().isFixLoading, className: "badge bg-brass/20 text-brass hover:bg-brass/30 flex items-center gap-1", "aria-label": "Sugerir fix con IA", children: [_jsx(Zap, { className: "w-3 h-3" }), " Fix IA"] }), showModal && (_jsxs("div", { className: "fixed inset-0 z-50 flex items-center justify-center", role: "dialog", "aria-modal": "true", "aria-label": "Sugerencias de fix IA", children: [_jsx("div", { className: "absolute inset-0 bg-black/60", onClick: () => setShowModal(false) }), _jsxs("div", { className: "relative w-full max-w-2xl max-h-[90vh] bg-[#161618] border border-neutral-700 rounded-xl shadow-2xl overflow-hidden flex flex-col", children: [_jsxs("div", { className: "p-4 border-b border-neutral-700 flex items-center justify-between", children: [_jsxs("h3", { className: "font-semibold text-white", children: ["Sugerencias de fix para: ", issue.column || 'dataset'] }), _jsx("button", { onClick: () => setShowModal(false), className: "p-1 rounded hover:bg-neutral-800", "aria-label": "Cerrar", children: _jsx(X, { className: "w-5 h-5 text-neutral-400" }) })] }), _jsxs("div", { className: "p-4 overflow-y-auto max-h-[60vh]", children: [isPreviewLoading && selectedFix && (_jsxs("div", { className: "mb-4 p-3 bg-brass/10 border border-brass/30 rounded-lg text-sm text-brass flex items-center gap-2", children: [_jsx(Loader2, { className: "w-4 h-4 animate-spin" }), " Generando preview..."] })), fixSuggestions.length === 0 && !isPreviewLoading && (_jsxs("div", { className: "text-center py-8 text-neutral-500", children: [_jsx("p", { children: "No hay sugerencias autom\u00E1ticas para este issue." }), _jsx("p", { className: "text-xs text-neutral-500 mt-1", children: "Intenta revisar el issue manualmente." })] })), fixSuggestions.map((fix, i) => (_jsx("div", { className: "mb-4 p-4 bg-neutral-900/50 border border-neutral-700 rounded-lg", children: _jsxs("div", { className: "flex items-start justify-between gap-2", children: [_jsxs("div", { className: "flex-1", children: [_jsxs("div", { className: "flex items-center gap-2 mb-1", children: [_jsx(ZapIcon, { className: "w-4 h-4 text-brass" }), _jsx("code", { className: "bg-neutral-800 px-2 py-0.5 rounded text-xs font-mono text-brass", children: fix.operation }), _jsx("span", { className: "text-xs px-2 py-0.5 rounded bg-neutral-800 text-neutral-400", children: fix.column || issue.column }), _jsxs("span", { className: "text-xs px-2 py-0.5 rounded bg-brass/20 text-brass", children: [(fix.confidence * 100).toFixed(0), "%"] })] }), _jsx("p", { className: "text-sm text-neutral-300", children: fix.reasoning }), _jsxs("p", { className: "text-xs text-neutral-500 mt-1", children: ["~", fix.estimatedFixed, " filas afectadas"] })] }), _jsxs("div", { className: "flex gap-1", children: [_jsxs("button", { onClick: () => handlePreview(fix), className: "px-3 py-1 text-xs bg-neutral-800 hover:bg-neutral-700 rounded text-neutral-300 flex items-center gap-1", "aria-label": "Ver preview", children: [_jsx(Eye, { className: "w-3 h-3" }), " Preview"] }), _jsxs("button", { onClick: () => handleAccept(`fix-${i}`), className: "px-3 py-1 text-xs bg-brass/20 hover:bg-brass/30 text-brass rounded", "aria-label": "Aceptar fix", children: [_jsx(Check, { className: "w-3 h-3 mr-1" }), " Aceptar"] })] })] }) }, i)))] }), _jsx("div", { className: "p-4 border-t border-neutral-700 flex justify-end gap-2", children: _jsx("button", { onClick: () => setShowModal(false), className: "px-4 py-2 bg-neutral-800 hover:bg-neutral-700 rounded text-neutral-300", children: "Cerrar" }) })] })] }))] }));
}
