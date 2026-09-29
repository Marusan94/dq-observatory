import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { api } from '../services/api';
const OPS = ['trim_whitespace', 'normalize_email', 'normalize_phone', 'remove_exact_duplicates', 'standardize_missing', 'parse_numeric', 'standardize_categories'];
const ROW_HEIGHT = 36;
export default function Cleaning() {
    const [op, setOp] = useState(OPS[0]);
    const [col, setCol] = useState('email');
    const [msg, setMsg] = useState('');
    const [previewData, setPreviewData] = useState(null);
    const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') });
    const id = ds.data?.items?.[0]?.id;
    const previewDataQ = useQuery({
        queryKey: ['clean-preview', id],
        queryFn: () => api(`/api/v1/datasets/${id}/preview`),
        enabled: !!id,
    });
    async function preview() {
        setMsg('Preview…');
        try {
            const r = await api(`/api/v1/datasets/${id}/clean`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ operation: op, column: col, preview_only: true }) });
            setPreviewData(r.preview_data);
            setMsg(`Preview: affected ${r.preview_data?.affected_rows ?? '?'} rows.`);
        }
        catch (e) {
            setMsg(e.message);
        }
    }
    async function apply() {
        try {
            const r = await api(`/api/v1/datasets/${id}/clean`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ operation: op, column: col }) });
            setMsg(`Applied. ${r.before_rows} → ${r.after_rows} rows. New score ${r.new_quality_score}.`);
            setPreviewData(null);
        }
        catch (e) {
            setMsg(e.message);
        }
    }
    const data = previewDataQ.data?.rows || [];
    const parentRef = React.useRef(null);
    const virtualizer = useVirtualizer({
        count: data.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => ROW_HEIGHT,
        overscan: 5,
    });
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Cleaning workspace" }), _jsx("p", { className: "text-sm text-neutral-400", children: "How do I fix it? Preview first, apply creates a new version. Original never destroyed." }), _jsxs("div", { className: "card mt-3 flex flex-wrap gap-2 items-center", children: [_jsx("select", { value: op, onChange: e => setOp(e.target.value), className: "bg-neutral-900 text-sm p-2 rounded", "aria-label": "Operation", children: OPS.map(o => _jsx("option", { children: o }, o)) }), _jsx("input", { value: col, onChange: e => setCol(e.target.value), className: "bg-neutral-900 text-sm p-2 rounded", "aria-label": "Column", placeholder: "column (optional)" }), _jsx("button", { className: "badge", onClick: preview, disabled: !id, children: "Preview" }), _jsx("button", { className: "badge", onClick: apply, disabled: !id, children: "Apply" })] }), msg && _jsx("p", { className: "mt-2 text-sm", role: "status", children: msg }), (previewData || previewDataQ.data) && (_jsxs("div", { className: "card mt-3", children: [_jsx("h3", { className: "text-sm font-medium mb-2", children: "Preview" }), previewData?.before && _jsx("p", { className: "text-xs text-neutral-500", children: "Before (sample)" }), previewData?.before && _jsx("pre", { className: "text-xs bg-neutral-900 p-2 rounded overflow-x-auto", children: JSON.stringify(previewData.before, null, 1).slice(0, 500) }), previewData?.after && _jsx("p", { className: "text-xs text-neutral-500 mt-2", children: "After (sample)" }), previewData?.after && _jsx("pre", { className: "text-xs bg-neutral-900 p-2 rounded overflow-x-auto", children: JSON.stringify(previewData.after, null, 1).slice(0, 500) }), previewData?.affected_rows !== undefined && _jsxs("p", { className: "mt-1 text-sm", children: ["Affected rows: ", previewData.affected_rows] }), data.length > 0 && (_jsxs("div", { className: "mt-2", children: [_jsxs("p", { className: "text-xs text-neutral-500", children: ["Current version sample (virtualized, ", data.length, " rows)"] }), _jsx("div", { ref: parentRef, className: "h-80 overflow-auto border border-neutral-800 rounded bg-neutral-950", style: { width: '100%' }, children: _jsxs("table", { className: "dq", style: { height: data.length * ROW_HEIGHT }, children: [_jsx("thead", { children: _jsx("tr", { style: { position: 'sticky', top: 0, zIndex: 1, background: '#141416' }, children: previewDataQ.data?.columns?.map((c, i) => (_jsx("th", { style: { width: 180 }, children: c }, i))) }) }), _jsx("tbody", { children: virtualizer.getVirtualItems().map((virtualRow) => (_jsx("tr", { style: { transform: `translateY(${virtualRow.start}px)` }, children: data[virtualRow.index] && Object.values(data[virtualRow.index]).map((v, ci) => (_jsx("td", { style: { width: 180, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }, children: v === null || v === undefined ? _jsx("span", { className: "text-neutral-500", children: "\u2014" }) : String(v).slice(0, 60) }, ci))) }, virtualRow.index))) })] }) })] }))] }))] }));
}
