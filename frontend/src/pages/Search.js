import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
export default function Search() {
    const [q, setQ] = useState('');
    const [debounced, setDebounced] = useState('');
    const ds = useQuery({ queryKey: ['ds'], queryFn: () => api('/api/v1/datasets?page_size=1') });
    const id = ds.data?.items?.[0]?.id;
    const search = useQuery({
        queryKey: ['search', debounced],
        queryFn: () => api(`/api/v1/search?q=${encodeURIComponent(debounced)}&limit=10`),
        enabled: !!debounced && debounced.length >= 2,
    });
    return (_jsxs("div", { children: [_jsx("h2", { className: "text-xl font-semibold", children: "Search" }), _jsx("p", { className: "text-sm text-neutral-400", children: "Find datasets, columns, issues, rules (2+ chars)." }), _jsxs("div", { className: "card mt-3", children: [_jsx("input", { value: q, onChange: e => { setQ(e.target.value); if (e.target.value.length >= 2)
                            setDebounced(e.target.value);
                        else
                            setDebounced(''); }, placeholder: "Search\u2026", "aria-label": "Global search", className: "bg-neutral-900 text-sm p-2 rounded w-full", autoFocus: true }), (search.isLoading || debounced) && _jsx("p", { className: "text-xs text-neutral-500 mt-1", children: "Searching\u2026" }), search.data && !search.isLoading && (_jsxs(_Fragment, { children: [(search.data.datasets?.length > 0) && (_jsxs("div", { className: "mt-3", children: [_jsx("h3", { className: "text-xs text-neutral-400", children: "Datasets" }), _jsx("ul", { className: "text-sm flex flex-col gap-1", children: search.data.datasets.map((d) => (_jsx("li", { children: _jsxs("a", { className: "underline", href: `/?dataset=${d.id}`, children: [d.name, " (", d.rows, " rows)"] }) }, d.id))) })] })), (search.data.columns?.length > 0) && (_jsxs("div", { className: "mt-3", children: [_jsx("h3", { className: "text-xs text-neutral-400", children: "Columns" }), _jsx("ul", { className: "text-sm flex flex-col gap-1", children: search.data.columns.map((c) => (_jsx("li", { children: _jsx("a", { className: "underline", href: `/column?dataset=${id}&column=${encodeURIComponent(c)}`, children: c }) }, c))) })] })), (search.data.issues?.length > 0) && (_jsxs("div", { className: "mt-3", children: [_jsx("h3", { className: "text-xs text-neutral-400", children: "Issues" }), _jsx("ul", { className: "text-sm flex flex-col gap-1", children: search.data.issues.map((i) => (_jsxs("li", { children: [_jsx("span", { className: "badge", children: i.severity }), " ", i.description] }, i.id))) })] })), (search.data.rules?.length > 0) && (_jsxs("div", { className: "mt-3", children: [_jsx("h3", { className: "text-xs text-neutral-400", children: "Rules" }), _jsx("ul", { className: "text-sm flex flex-col gap-1", children: search.data.rules.map((r) => (_jsxs("li", { children: [r.name, " on ", r.column] }, r.id))) })] })), (!search.data?.datasets?.length && !search.data?.columns?.length && !search.data?.issues?.length && !search.data?.rules?.length) &&
                                _jsxs("p", { className: "mt-2 text-sm text-neutral-400", children: ["No results for \"", debounced, "\""] })] }))] })] }));
}
