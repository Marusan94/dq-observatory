import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, API } from '../services/api';
import AIFixCard from '../components/AIFixCard';
const SEVS = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
const CATS = ['', 'COMPLETENESS', 'VALIDITY', 'CONSISTENCY', 'UNIQUENESS', 'INTEGRITY', 'TYPE', 'FORMAT', 'ANOMALY', 'SEMANTIC'];
const STATUSES = ['', 'OPEN', 'IGNORED', 'REVIEWED', 'FIXED'];
export default function Issues() {
    const qc = useQueryClient();
    const [sev, setSev] = useState('');
    const [cat, setCat] = useState('');
    const [col, setCol] = useState('');
    const [st, setSt] = useState('');
    const [auto, setAuto] = useState('');
    const [search, setSearch] = useState('');
    const [sel, setSel] = useState(null);
    const [toast, setToast] = useState('');
    const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') });
    const id = ds.data?.items?.[0]?.id;
    const qs = new URLSearchParams({ page_size: '100' });
    if (sev)
        qs.set('severity', sev);
    if (cat)
        qs.set('category', cat);
    if (col)
        qs.set('column', col);
    if (st)
        qs.set('status', st);
    if (auto)
        qs.set('auto_fix', auto === 'auto' ? 'true' : 'false');
    if (search)
        qs.set('search', search);
    const iss = useQuery({ queryKey: ['issues', id, qs.toString()],
        queryFn: () => api(`/api/v1/datasets/${id}/issues?${qs}`), enabled: !!id });
    async function applyFix(issue) {
        try {
            const r = await api(`/api/v1/issues/${issue.id}/fix`, { method: 'POST' });
            setToast(`Fix applied: ${r.operation} (${r.affected_rows} rows). New version created.`);
            qc.invalidateQueries();
        }
        catch (e) {
            setToast(`Cannot auto-fix: ${e.message}`);
        }
    }
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Issues" }), _jsx("p", { className: "text-sm text-neutral-400", children: "What is wrong? Combine severity \u00B7 category \u00B7 column \u00B7 status \u00B7 auto-fix \u00B7 search." }), _jsxs("div", { className: "mt-3 flex flex-wrap gap-2 items-center", children: [_jsx("select", { value: sev, onChange: e => setSev(e.target.value), "aria-label": "Severity", className: "bg-neutral-900 text-sm p-2 rounded", children: SEVS.map(s => _jsx("option", { value: s, children: s || 'Severity: all' }, s)) }), _jsx("select", { value: cat, onChange: e => setCat(e.target.value), "aria-label": "Category", className: "bg-neutral-900 text-sm p-2 rounded", children: CATS.map(s => _jsx("option", { value: s, children: s || 'Category: all' }, s)) }), _jsx("input", { value: col, onChange: e => setCol(e.target.value), placeholder: "Column", "aria-label": "Column", className: "bg-neutral-900 text-sm p-2 rounded w-32" }), _jsx("select", { value: st, onChange: e => setSt(e.target.value), "aria-label": "Status", className: "bg-neutral-900 text-sm p-2 rounded", children: STATUSES.map(s => _jsx("option", { value: s, children: s || 'Status: all' }, s)) }), _jsxs("select", { value: auto, onChange: e => setAuto(e.target.value), "aria-label": "Auto-fix", className: "bg-neutral-900 text-sm p-2 rounded", children: [_jsx("option", { value: "", children: "Fix: all" }), _jsx("option", { value: "auto", children: "Auto-fix available" }), _jsx("option", { value: "manual", children: "Review required" })] }), _jsx("input", { value: search, onChange: e => setSearch(e.target.value), placeholder: "Search\u2026", "aria-label": "Search issues", className: "bg-neutral-900 text-sm p-2 rounded w-36" })] }), toast && _jsx("p", { className: "mt-2 text-sm", role: "status", "aria-live": "polite", children: toast }), _jsxs("div", { className: "flex gap-3 mt-3", children: [_jsxs("div", { className: "card overflow-x-auto flex-1", children: [_jsxs("table", { className: "dq", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "Severity" }), _jsx("th", { children: "Column" }), _jsx("th", { children: "Description" }), _jsx("th", { children: "Rows" }), _jsx("th", { children: "%" }), _jsx("th", { children: "Fix" })] }) }), _jsx("tbody", { children: (iss.data?.items || []).map((i) => (_jsxs("tr", { onClick: () => setSel(i), className: "cursor-pointer hover:bg-neutral-900", children: [_jsx("td", { children: _jsx("span", { className: "badge", children: i.severity }) }), _jsx("td", { children: i.column || '—' }), _jsx("td", { className: "max-w-md truncate", title: i.description, children: i.description }), _jsx("td", { children: i.row_count }), _jsx("td", { children: i.percentage }), _jsx("td", { children: i.auto_fix_available ? 'Auto' : 'Review' })] }, i.id))) })] }), _jsxs("p", { className: "text-xs text-neutral-500 mt-2", children: ["Total: ", iss.data?.total ?? 0, ". Click a row for detail."] }), !iss.data?.items?.length && _jsx("p", { className: "text-sm text-neutral-400 mt-2", children: "No issues detected \u2014 passes all configured rules." })] }), sel && (_jsxs("aside", { className: "card w-80 shrink-0", "aria-label": "Issue detail", children: [_jsxs("h3", { className: "font-medium text-sm", children: [sel.severity, " \u00B7 ", sel.category] }), _jsx("p", { className: "text-sm mt-1", children: sel.description }), _jsxs("dl", { className: "text-xs text-neutral-400 mt-2 flex flex-col gap-1", children: [_jsxs("div", { children: ["Column: ", _jsx("span", { className: "text-neutral-200", children: sel.column || '—' })] }), _jsxs("div", { children: ["Affected: ", _jsxs("span", { className: "text-neutral-200", children: [sel.row_count, " rows (", sel.percentage, "%)"] })] }), _jsxs("div", { children: ["Rule: ", _jsx("span", { className: "text-neutral-200", children: sel.rule })] }), _jsxs("div", { children: ["Status: ", _jsx("span", { className: "text-neutral-200", children: sel.status })] })] }), (sel.examples?.length > 0) && (_jsxs("div", { className: "mt-2", children: [_jsx("div", { className: "text-xs text-neutral-500", children: "Examples" }), _jsx("pre", { className: "text-xs bg-neutral-900 p-2 rounded overflow-x-auto", children: JSON.stringify(sel.examples.slice(0, 5), null, 1).slice(0, 600) })] })), _jsxs("div", { className: "mt-3 flex gap-2", children: [sel.auto_fix_available
                                        ? _jsx("button", { className: "badge", onClick: () => applyFix(sel), children: "Apply auto-fix" })
                                        : _jsx("span", { className: "badge", children: "Review required \u2014 no safe auto-fix" }), _jsx(AIFixCard, { issueId: sel.id, issue: sel, datasetId: id, versionId: sel.version_id }), _jsx("button", { className: "badge", onClick: () => setSel(null), children: "Close" })] }), _jsx("a", { className: "text-xs underline mt-2 inline-block", href: `${API}/docs`, target: "_blank", rel: "noreferrer", children: "Configure rule via API" })] }))] })] }));
}
