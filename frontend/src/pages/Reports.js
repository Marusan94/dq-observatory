import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api, API } from '../services/api';
export default function Reports() {
    const qc = useQueryClient();
    const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') });
    const id = ds.data?.items?.[0]?.id;
    const rep = useQuery({ queryKey: ['rep', id], queryFn: () => api(`/api/v1/datasets/${id}/report`), enabled: !!id });
    const vers = useQuery({ queryKey: ['vers', id], queryFn: () => api(`/api/v1/datasets/${id}/versions`), enabled: !!id });
    const ba = rep.data?.before_after;
    // Export options state
    const [fmt, setFmt] = useState('csv');
    const [columns, setColumns] = useState('');
    const [filterCol, setFilterCol] = useState('');
    const [filterOp, setFilterOp] = useState('eq');
    const [filterVal, setFilterVal] = useState('');
    const [dateCol, setDateCol] = useState('');
    const [dateStart, setDateStart] = useState('');
    const [dateEnd, setDateEnd] = useState('');
    const [msg, setMsg] = useState('');
    const formats = ['csv', 'xlsx', 'json', 'parquet', 'delta', 'avro', 'zip'];
    const operators = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'contains'];
    function buildExportUrl() {
        const params = new URLSearchParams();
        params.set('format', fmt);
        if (columns)
            params.set('columns', columns);
        if (filterCol && filterOp && filterVal) {
            params.set('filter_col', filterCol);
            params.set('filter_op', filterOp);
            params.set('filter_val', filterVal);
        }
        if (dateStart && dateEnd && dateCol) {
            params.set('date_start', dateStart);
            params.set('date_end', dateEnd);
            params.set('date_column', dateCol);
        }
        return `${API}/api/v1/datasets/${id}/export?${params.toString()}`;
    }
    async function download() {
        setMsg('');
        try {
            const res = await fetch(buildExportUrl(), { headers: { 'X-Role': 'owner' } });
            if (!res.ok)
                throw new Error(`${res.status} ${await res.text()}`);
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${id}_export.${fmt === 'delta' ? 'zip' : fmt}`;
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);
            document.body.removeChild(a);
            setMsg('Descarga iniciada.');
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    function Lineage({ versions, operations }) {
        if (!versions?.length)
            return null;
        const items = [...versions].reverse();
        return (_jsx("div", { className: "relative pl-4 border-l border-neutral-800", children: items.map((v, i) => {
                const ops = operations?.filter((o) => o.to === v.id) || [];
                return (_jsxs("div", { className: "relative mb-4", children: [_jsx("div", { className: "absolute left-[-10px] top-1 w-3 h-3 rounded-full bg-neutral-800 border-2 border-[#0b0e1c]" }), _jsxs("div", { className: "ml-4", children: [_jsxs("div", { className: "font-medium", children: [v.label, " ", _jsxs("span", { className: "text-xs text-neutral-500", children: ["(", v.rows, " rows, score ", v.quality_score ?? '—', ")"] })] }), ops.length > 0 && (_jsx("div", { className: "mt-1 ml-2 text-sm text-neutral-400", children: ops.map((o) => _jsxs("div", { className: "flex gap-1", children: [_jsx("span", { className: "badge text-xs", children: o.op }), _jsx("span", { children: o.column ? `(${o.column})` : '' }), _jsxs("span", { children: [o.affected, " rows"] })] }, o.id)) }))] })] }, v.id));
            }) }));
    }
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Reports & Export" }), _jsx("p", { className: "text-sm text-neutral-400", children: "Can I communicate and take results elsewhere?" }), _jsxs("div", { className: "card mt-3", children: [_jsxs("div", { children: ["Score: ", rep.data?.quality_score?.overall, " \u00B7 Issues: ", rep.data?.summary?.issues] }), ba && (_jsxs("table", { className: "dq mt-2", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", {}), _jsx("th", { children: "Version" }), _jsx("th", { children: "Rows" }), _jsx("th", { children: "Score" })] }) }), _jsxs("tbody", { children: [_jsxs("tr", { children: [_jsx("td", { children: "Before" }), _jsx("td", { children: ba.before_version }), _jsx("td", { children: ba.before_rows }), _jsx("td", { children: ba.before_score ?? '—' })] }), _jsxs("tr", { children: [_jsx("td", { children: "After" }), _jsx("td", { children: ba.after_version }), _jsx("td", { children: ba.after_rows }), _jsx("td", { children: ba.after_score })] })] })] })), _jsxs("details", { className: "mt-3 group", children: [_jsxs("summary", { className: "cursor-pointer flex items-center gap-2 text-sm font-medium text-neutral-300", children: [_jsx("span", { className: "badge", children: "\u2699 Opciones de exportaci\u00F3n" }), _jsx("span", { className: "text-xs text-neutral-500 group-open:rotate-180 transition-transform", children: "\u25BC" })] }), _jsxs("div", { className: "mt-3 space-y-3 p-2 border-t border-neutral-800", children: [_jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Formato" }), _jsx("select", { value: fmt, onChange: e => setFmt(e.target.value), className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm", children: formats.map(f => _jsx("option", { value: f, children: f.toUpperCase() }, f)) })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Columnas (coma-separadas, vac\u00EDo = todas)" }), _jsx("input", { value: columns, onChange: e => setColumns(e.target.value), placeholder: "id,name,email", className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" })] }), _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-2", children: [_jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Filtrar columna" }), _jsx("input", { value: filterCol, onChange: e => setFilterCol(e.target.value), placeholder: "email", className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Operador" }), _jsx("select", { value: filterOp, onChange: e => setFilterOp(e.target.value), className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm", children: operators.map(op => _jsx("option", { value: op, children: op }, op)) })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Valor" }), _jsx("input", { value: filterVal, onChange: e => setFilterVal(e.target.value), placeholder: "valor", className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Columna fecha" }), _jsx("input", { value: dateCol, onChange: e => setDateCol(e.target.value), placeholder: "created_at", className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" })] })] }), _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-2 gap-2", children: [_jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Fecha inicio (ISO)" }), _jsx("input", { type: "date", value: dateStart, onChange: e => setDateStart(e.target.value), className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-xs text-neutral-400 mb-1", children: "Fecha fin (ISO)" }), _jsx("input", { type: "date", value: dateEnd, onChange: e => setDateEnd(e.target.value), className: "w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm" })] })] })] })] }), _jsxs("div", { className: "mt-2 flex flex-wrap gap-2", children: [_jsx("button", { onClick: download, className: "badge bg-brass text-black hover:bg-brass/80", children: "Descargar" }), _jsx("a", { className: "badge", href: `${API}/api/v1/datasets/${id}/report.html`, target: "_blank", rel: "noreferrer", children: "HTML report" })] }), msg && _jsx("p", { className: "mt-2 text-sm text-brass", role: "status", children: msg })] }), (vers.data?.operations?.length > 0) && (_jsxs("div", { className: "card mt-3", children: [_jsx("h3", { className: "text-sm font-medium mb-2", children: "Data lineage" }), _jsx(Lineage, { versions: vers.data?.versions, operations: vers.data?.operations }), _jsxs("details", { className: "mt-2", children: [_jsx("summary", { className: "text-sm text-neutral-400 cursor-pointer", children: "Transformation history (flat)" }), _jsx("ol", { className: "text-sm flex flex-col gap-1 mt-2", children: vers.data.operations.map((o) => (_jsxs("li", { children: [o.op, o.column ? ` (${o.column})` : '', " \u2014 ", o.affected, " rows affected"] }, o.id))) })] })] }))] }));
}
