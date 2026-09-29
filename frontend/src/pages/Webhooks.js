import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
export default function Webhooks() {
    const qc = useQueryClient();
    const [role, setRole] = useState('admin');
    const [name, setName] = useState('alerts');
    const [url, setUrl] = useState('https://hooks.example.com/dq');
    const [events, setEvents] = useState('job_failed, drift_detected');
    const [msg, setMsg] = useState('');
    const whs = useQuery({ queryKey: ['webhooks'], queryFn: () => api('/api/v1/webhooks') });
    async function create() {
        setMsg('');
        try {
            await api('/api/v1/webhooks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Role': role },
                body: JSON.stringify({ name, url, events: events.split(',').map(s => s.trim()).filter(Boolean) }),
            });
            setMsg('Webhook created.');
            qc.invalidateQueries({ queryKey: ['webhooks'] });
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    async function remove(id) {
        setMsg('');
        try {
            await api(`/api/v1/webhooks/${id}`, { method: 'DELETE', headers: { 'X-Role': role } });
            setMsg('Webhook deleted.');
            qc.invalidateQueries({ queryKey: ['webhooks'] });
        }
        catch (e) {
            setMsg(`Error: ${e.message}`);
        }
    }
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Webhooks" }), _jsxs("p", { className: "text-sm text-neutral-400", children: ["HMAC-signed alerts. Mutations need ", _jsx("span", { className: "badge", children: "webhook:manage" }), " (owner/admin)."] }), _jsxs("div", { className: "card mt-3 flex flex-wrap gap-2 items-end max-w-2xl", children: [_jsxs("label", { className: "text-sm", children: ["Role", _jsx("select", { value: role, onChange: e => setRole(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Role", children: ['viewer', 'editor', 'admin', 'owner'].map(r => _jsx("option", { children: r }, r)) })] }), _jsxs("label", { className: "text-sm", children: ["Name", _jsx("input", { value: name, onChange: e => setName(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", "aria-label": "Webhook name" })] }), _jsxs("label", { className: "text-sm", children: ["URL", _jsx("input", { value: url, onChange: e => setUrl(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-64", "aria-label": "Webhook URL" })] }), _jsxs("label", { className: "text-sm", children: ["Events (comma-separated)", _jsx("input", { value: events, onChange: e => setEvents(e.target.value), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-64", "aria-label": "Events" })] }), _jsx("button", { className: "badge", onClick: create, children: "Create webhook" })] }), msg && _jsx("p", { className: "text-sm mt-2", role: "status", children: msg }), _jsxs("div", { className: "card mt-3", children: [whs.isLoading && _jsx("p", { className: "text-sm text-neutral-500", children: "Loading\u2026" }), (whs.data || []).map((w) => (_jsxs("div", { className: "flex items-center justify-between border-b border-neutral-800 py-2 text-sm", children: [_jsxs("div", { children: [_jsx("span", { className: "font-medium", children: w.name }), _jsxs("span", { className: "text-neutral-500", children: [" \u00B7 ", w.url, " \u00B7 ", (w.events || []).join(', ')] })] }), _jsx("button", { className: "badge", onClick: () => remove(w.id), children: "Delete" })] }, w.id))), whs.data?.length === 0 && _jsx("p", { className: "text-sm text-neutral-500", children: "No webhooks yet." })] })] }));
}
