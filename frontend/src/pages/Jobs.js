import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
export default function Jobs() {
    const qc = useQueryClient();
    const [role, setRole] = useState('admin');
    const [name, setName] = useState('nightly quality');
    const [cron, setCron] = useState('0 2 * * *');
    const [msg, setMsg] = useState('');
    const jobs = useQuery({ queryKey: ['jobs'], queryFn: () => api('/api/v1/jobs') });
    async function create() {
        setMsg('');
        try {
            await api('/api/v1/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Role': role },
                body: JSON.stringify({ name, cron_expression: cron }),
            });
            setMsg('Job created.');
            qc.invalidateQueries({ queryKey: ['jobs'] });
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    async function trigger(id) {
        setMsg('');
        try {
            await api(`/api/v1/jobs/${id}/run`, { method: 'POST', headers: { 'X-Role': role } });
            setMsg('Run triggered.');
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    async function pause(id) {
        setMsg('');
        try {
            await api(`/api/v1/jobs/${id}/pause`, { method: 'POST', headers: { 'X-Role': role } });
            setMsg('Job paused.');
            qc.invalidateQueries({ queryKey: ['jobs'] });
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    async function resume(id) {
        setMsg('');
        try {
            await api(`/api/v1/jobs/${id}/resume`, { method: 'POST', headers: { 'X-Role': role } });
            setMsg('Job resumed.');
            qc.invalidateQueries({ queryKey: ['jobs'] });
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Scheduled jobs" }), _jsxs("p", { className: "text-sm text-neutral-400", children: ["Cron-based quality runs. Mutations need ", _jsx("span", { className: "badge", children: "schedule:manage" }), " (owner/admin)."] }), _jsxs("div", { className: "card mt-3 flex flex-wrap gap-2 items-end max-w-2xl", children: [_jsxs("label", { className: "text-sm", children: ["Role", _jsx("select", { value: role, onChange: e => setRole(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Role", children: ['viewer', 'editor', 'admin', 'owner'].map(r => _jsx("option", { children: r }, r)) })] }), _jsxs("label", { className: "text-sm", children: ["Name", _jsx("input", { value: name, onChange: e => setName(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Job name" })] }), _jsxs("label", { className: "text-sm", children: ["Cron", _jsx("input", { value: cron, onChange: e => setCron(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-32", "aria-label": "Cron expression" })] }), _jsx("button", { className: "badge", onClick: create, children: "Create job" })] }), msg && _jsx("p", { className: "text-sm mt-2", role: "status", children: msg }), _jsxs("div", { className: "card mt-3", children: [jobs.isLoading && _jsx("p", { className: "text-sm text-neutral-500", children: "Loading\u2026" }), (jobs.data || []).map((j) => (_jsxs("div", { className: "flex items-center justify-between border-b border-neutral-800 py-2 text-sm", children: [_jsxs("div", { children: [_jsx("span", { className: "font-medium", children: j.name }), _jsxs("span", { className: "text-neutral-500", children: [" \u00B7 ", j.cron, " \u00B7 ", j.status, " \u00B7 next ", j.next_run || '—'] })] }), _jsxs("div", { className: "flex gap-1", children: [_jsx("button", { className: "badge", onClick: () => trigger(j.id), children: "Run now" }), j.status === 'PAUSED' ? (_jsx("button", { className: "badge", onClick: () => resume(j.id), children: "Resume" })) : (_jsx("button", { className: "badge", onClick: () => pause(j.id), children: "Pause" }))] })] }, j.id))), jobs.data?.length === 0 && _jsx("p", { className: "text-sm text-neutral-500", children: "No jobs yet." })] })] }));
}
