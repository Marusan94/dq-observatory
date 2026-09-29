import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
export default function Drift() {
    const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=20') });
    const [dataset, setDataset] = useState('');
    const [fromV, setFromV] = useState('');
    const [toV, setToV] = useState('');
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const id = dataset || ds.data?.items?.[0]?.id || '';
    async function run() {
        setError('');
        setResult(null);
        if (!id || !fromV || !toV) {
            setError('Pick a dataset and both version IDs.');
            return;
        }
        try {
            const r = await api(`/api/v1/${id}/drift?from_version=${encodeURIComponent(fromV)}&to_version=${encodeURIComponent(toV)}`);
            setResult(r);
        }
        catch (e) {
            setError(e.message);
        }
    }
    const issues = result?.issues || [];
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Drift detection" }), _jsx("p", { className: "text-sm text-neutral-400", children: "Schema + distribution drift between two versions (KS, PSI, KL, \u03C7\u00B2)." }), _jsxs("div", { className: "card mt-3 flex flex-wrap gap-2 items-end max-w-3xl", children: [_jsxs("label", { className: "text-sm", children: ["Dataset", _jsx("select", { value: id, onChange: e => setDataset(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Dataset", children: (ds.data?.items || []).map((d) => _jsx("option", { value: d.id, children: d.name }, d.id)) })] }), _jsxs("label", { className: "text-sm", children: ["From version", _jsx("input", { value: fromV, onChange: e => setFromV(e.target.value), placeholder: "version id", className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-56", "aria-label": "From version" })] }), _jsxs("label", { className: "text-sm", children: ["To version", _jsx("input", { value: toV, onChange: e => setToV(e.target.value), placeholder: "version id", className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-56", "aria-label": "To version" })] }), _jsx("button", { className: "badge", onClick: run, children: "Detect drift" })] }), error && _jsx("p", { className: "text-sm mt-2 text-red-400", role: "alert", children: error }), result && (_jsxs("div", { className: "card mt-3", children: [_jsxs("h3", { className: "text-sm font-medium", children: ["Issues (", issues.length, ")"] }), issues.length === 0 && _jsx("p", { className: "text-sm text-neutral-500", children: "No drift issues." }), _jsx("ul", { className: "text-sm flex flex-col gap-1 mt-1", children: issues.map((i, k) => (_jsxs("li", { children: [_jsx("span", { className: "badge", children: i.severity || 'INFO' }), " ", _jsx("span", { className: "text-neutral-500", children: i.column || '' }), " ", i.description || JSON.stringify(i)] }, k))) }), _jsxs("details", { className: "mt-2", children: [_jsx("summary", { className: "text-xs text-neutral-400 cursor-pointer", children: "Raw metrics" }), _jsx("pre", { className: "text-xs overflow-auto max-h-96 mt-1", children: JSON.stringify(result.drift ?? result, null, 2) })] })] }))] }));
}
