import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
export default function ColumnDetail() {
    const [sp] = useSearchParams();
    const dsId = sp.get('dataset');
    const col = sp.get('column');
    const ds = useQuery({ queryKey: ['datasets-list'], queryFn: () => api('/api/v1/datasets?page_size=20') });
    const id = dsId || ds.data?.items?.[0]?.id;
    const det = useQuery({ queryKey: ['col', id, col],
        queryFn: () => api(`/api/v1/datasets/${id}/columns/${encodeURIComponent(col || '')}`),
        enabled: !!(id && col) });
    const c = det.data?.column;
    return (_jsxs("div", { children: [_jsx(Link, { to: "/", className: "text-xs underline text-neutral-400", children: "\u2190 Overview" }), _jsxs("h2", { className: "text-xl font-semibold mt-1", children: ["Column: ", col || '—'] }), !col ? _jsx("div", { className: "card mt-4 text-sm", children: "Pick a column from the Overview health table." })
                : !c ? _jsx("div", { className: "card mt-4 text-sm", children: "Loading\u2026" }) : (_jsxs(_Fragment, { children: [_jsxs("div", { className: "grid grid-cols-2 md:grid-cols-4 gap-3 mt-4", children: [_jsxs("div", { className: "card", children: [_jsx("div", { className: "text-xs text-neutral-400", children: "Semantic type" }), _jsxs("div", { children: [c.semantic_type, " (", c.confidence, ")"] }), _jsxs("div", { className: "text-xs text-neutral-500", children: ["physical: ", c.physical_type] })] }), _jsxs("div", { className: "card", children: [_jsx("div", { className: "text-xs text-neutral-400", children: "Missing" }), _jsxs("div", { children: [c.missing, " (", (c.missing_rate * 100).toFixed(2), "%)"] })] }), _jsxs("div", { className: "card", children: [_jsx("div", { className: "text-xs text-neutral-400", children: "Unique" }), _jsxs("div", { children: [c.unique, " (", (c.unique_rate * 100).toFixed(1), "%)"] })] }), _jsxs("div", { className: "card", children: [_jsx("div", { className: "text-xs text-neutral-400", children: "Flags" }), _jsx("div", { className: "text-xs", children: [c.constant && 'constant', c.high_cardinality && 'high-cardinality', c.potential_identifier && 'potential-identifier'].filter(Boolean).join(' · ') || '—' })] })] }), _jsxs("div", { className: "card mt-3", children: [_jsx("h3", { className: "text-sm font-medium mb-2", children: "Top values" }), _jsx("pre", { className: "text-xs bg-neutral-900 p-2 rounded overflow-x-auto", children: JSON.stringify(c.top_values, null, 1).slice(0, 800) })] }), _jsxs("div", { className: "card mt-3", children: [_jsxs("h3", { className: "text-sm font-medium mb-2", children: ["Issues (", (det.data?.issues || []).length, ")"] }), (det.data?.issues || []).map((i, k) => (_jsxs("p", { className: "text-sm", children: [_jsx("span", { className: "badge", children: i.severity }), " ", i.description] }, k))), !(det.data?.issues || []).length && _jsx("p", { className: "text-sm text-neutral-400", children: "No issues for this column." })] })] }))] }));
}
