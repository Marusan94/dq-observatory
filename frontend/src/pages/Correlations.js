import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
export default function Correlations() {
    const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=20') });
    const [dataset, setDataset] = useState('');
    const [minCorr, setMinCorr] = useState('0.3');
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const id = dataset || ds.data?.items?.[0]?.id || '';
    async function run() {
        setError('');
        setResult(null);
        if (!id) {
            setError('Pick a dataset.');
            return;
        }
        try {
            const r = await api(`/api/v1/${id}/correlations?min_correlation=${encodeURIComponent(minCorr)}&max_pairs=100`);
            setResult(r);
        }
        catch (e) {
            setError(e.message);
        }
    }
    const pairs = result?.correlation_details || [];
    const issues = result?.issues || [];
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Correlations" }), _jsx("p", { className: "text-sm text-neutral-400", children: "Pearson/Spearman/Kendall, Cram\u00E9r's V, Theil's U, correlation ratio." }), _jsxs("div", { className: "card mt-3 flex flex-wrap gap-2 items-end max-w-3xl", children: [_jsxs("label", { className: "text-sm", children: ["Dataset", _jsx("select", { value: id, onChange: e => setDataset(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Dataset", children: (ds.data?.items || []).map((d) => _jsx("option", { value: d.id, children: d.name }, d.id)) })] }), _jsxs("label", { className: "text-sm", children: ["Min |correlation|", _jsx("input", { value: minCorr, onChange: e => setMinCorr(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-20", "aria-label": "Min correlation" })] }), _jsx("button", { className: "badge", onClick: run, children: "Analyze" })] }), error && _jsx("p", { className: "text-sm mt-2 text-red-400", role: "alert", children: error }), result && (_jsxs("div", { className: "card mt-3", children: [_jsxs("h3", { className: "text-sm font-medium", children: ["Top pairs (", pairs.length, ")"] }), pairs.length === 0 && _jsx("p", { className: "text-sm text-neutral-500", children: "No pairs above threshold." }), _jsx("ul", { className: "text-sm flex flex-col gap-1 mt-1", children: pairs.slice(0, 50).map((p, k) => _jsx("li", { className: "text-neutral-300", children: JSON.stringify(p) }, k)) }), issues.length > 0 && (_jsxs("div", { className: "mt-2", children: [_jsxs("h3", { className: "text-sm font-medium", children: ["Issues (", issues.length, ")"] }), _jsx("ul", { className: "text-sm flex flex-col gap-1 mt-1", children: issues.map((i, k) => _jsxs("li", { children: [_jsx("span", { className: "badge", children: i.severity || 'INFO' }), " ", i.description || JSON.stringify(i)] }, k)) })] }))] }))] }));
}
