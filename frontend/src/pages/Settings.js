import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
const KEY = 'dq-settings';
export function loadSettings() {
    try {
        return { profile: 'general', country: 'US', dateFormat: 'ISO', missingTokens: 'N/A,NA,null,unknown,-,?', ...JSON.parse(localStorage.getItem(KEY) || '{}') };
    }
    catch {
        return { profile: 'general', country: 'US', dateFormat: 'ISO', missingTokens: 'N/A,NA,null,unknown,-,?' };
    }
}
export default function Settings() {
    const [s, setS] = useState(loadSettings());
    const [msg, setMsg] = useState('');
    function save() {
        localStorage.setItem(KEY, JSON.stringify(s));
        setMsg('Settings saved. They apply to the next analysis run.');
    }
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Settings" }), _jsx("p", { className: "text-sm text-neutral-400", children: "Quality profile, phone country, date format, missing-value tokens." }), _jsxs("div", { className: "card mt-3 flex flex-col gap-3 max-w-md", children: [_jsxs("label", { className: "text-sm", children: ["Quality profile", _jsx("select", { value: s.profile, onChange: e => setS({ ...s, profile: e.target.value }), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", children: ['general', 'crm', 'sales', 'education', 'custom'].map(p => _jsx("option", { children: p }, p)) })] }), _jsxs("label", { className: "text-sm", children: ["Phone country", _jsx("input", { value: s.country, onChange: e => setS({ ...s, country: e.target.value.toUpperCase().slice(0, 2) }), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-20", "aria-label": "Phone country" })] }), _jsxs("label", { className: "text-sm", children: ["Date format", _jsx("select", { value: s.dateFormat, onChange: e => setS({ ...s, dateFormat: e.target.value }), className: "ml-2 bg-neutral-900 p-2 rounded text-sm", children: ['ISO', 'DD/MM/YYYY', 'MM/DD/YYYY'].map(p => _jsx("option", { children: p }, p)) })] }), _jsxs("label", { className: "text-sm", children: ["Missing tokens (comma-separated)", _jsx("input", { value: s.missingTokens, onChange: e => setS({ ...s, missingTokens: e.target.value }), className: "ml-2 bg-neutral-900 p-2 rounded text-sm w-full", "aria-label": "Missing tokens" })] }), _jsx("div", { children: _jsx("button", { className: "badge", onClick: save, children: "Save" }) }), msg && _jsx("p", { className: "text-sm", role: "status", children: msg })] })] }));
}
