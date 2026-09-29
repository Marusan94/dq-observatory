import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
export default function Contracts() {
    const qc = useQueryClient();
    const [role, setRole] = useState('editor');
    const [dataset, setDataset] = useState('');
    const [name, setName] = useState('brooklyn-events');
    const [cols, setCols] = useState('id,email,age');
    const [minScore, setMinScore] = useState('60');
    const [msg, setMsg] = useState('');
    const [check, setCheck] = useState(null);
    const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=20') });
    const id = dataset || ds.data?.items?.[0]?.id || '';
    const list = useQuery({ queryKey: ['contracts', id], queryFn: () => api(`/api/v1/contracts?dataset_id=${id}`), enabled: !!id });
    async function create() {
        setMsg('');
        setCheck(null);
        try {
            const schema = {};
            cols.split(',').map(s => s.trim()).filter(Boolean).forEach(c => { schema[c] = { physical_type: 'object', required: true }; });
            const r = await api('/api/v1/contracts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Role': role },
                body: JSON.stringify({ dataset_id: id, name, schema, rules: [], sla: { min_score: Number(minScore) || 0 } }),
            });
            setMsg(`Contract ${r.id.slice(0, 8)}… created (v${r.version}).`);
            qc.invalidateQueries({ queryKey: ['contracts'] });
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    async function runCheck(cid) {
        setMsg('');
        setCheck(null);
        try {
            const r = await api(`/api/v1/contracts/${cid}/check`, { method: 'POST' });
            setCheck(r);
            setMsg(r.passed ? 'Check passed — no breaking changes.' : `Check failed — ${r.violations.length} violation(s).`);
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Data contracts" }), _jsx("p", { className: "text-sm text-neutral-400", children: "Schema + SLA per dataset. Breaking-change checks on latest version. Writes need editor+." }), _jsxs("div", { className: "card mt-3 flex flex-wrap gap-2 items-end max-w-3xl", children: [_jsxs("label", { className: "text-sm", children: ["Role", _jsx("select", { value: role, onChange: e => setRole(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Role", children: ['viewer', 'editor', 'admin', 'owner'].map(r => _jsx("option", { children: r }, r)) })] }), _jsxs("label", { className: "text-sm", children: ["Dataset", _jsx("select", { value: id, onChange: e => setDataset(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Dataset", children: (ds.data?.items || []).map((d) => _jsx("option", { value: d.id, children: d.name }, d.id)) })] }), _jsxs("label", { className: "text-sm", children: ["Name", _jsx("input", { value: name, onChange: e => setName(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Contract name" })] }), _jsxs("label", { className: "text-sm", children: ["Columns", _jsx("input", { value: cols, onChange: e => setCols(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-48", "aria-label": "Contract columns" })] }), _jsxs("label", { className: "text-sm", children: ["Min score", _jsx("input", { value: minScore, onChange: e => setMinScore(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-20", "aria-label": "Min score" })] }), _jsx("button", { className: "badge", onClick: create, children: "Create contract" })] }), msg && _jsx("p", { className: "text-sm mt-2", role: "status", children: msg }), _jsxs("div", { className: "card mt-3", children: [(list.data || []).map((c) => (_jsxs("div", { className: "flex items-center justify-between border-b border-neutral-800 py-2 text-sm", children: [_jsxs("div", { children: [_jsx("span", { className: "font-medium", children: c.name }), _jsxs("span", { className: "text-neutral-500", children: [" \u00B7 v", c.version, " \u00B7 ", c.status, " \u00B7 ", Object.keys(c.schema || {}).length, " cols"] })] }), _jsx("button", { className: "badge", onClick: () => runCheck(c.id), children: "Run check" })] }, c.id))), list.data?.length === 0 && _jsx("p", { className: "text-sm text-neutral-500", children: "No contracts yet." })] }), check && (_jsxs("div", { className: "card mt-3", children: [_jsxs("h3", { className: "text-sm font-medium", children: ["Check: ", check.passed ? 'PASSED' : 'FAILED'] }), _jsx("ul", { className: "text-sm flex flex-col gap-1 mt-1", children: (check.violations || []).map((v, k) => (_jsxs("li", { children: [_jsx("span", { className: "badge", children: v.severity || 'INFO' }), " ", v.type, " ", v.column ? `(${v.column})` : ''] }, k))) })] }))] }));
}
