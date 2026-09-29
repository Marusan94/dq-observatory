import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Suspense, lazy } from 'react';
import { NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from './services/api';
import Tour from './components/Tour';
const Upload = lazy(() => import('./pages/Upload'));
const Overview = lazy(() => import('./pages/Overview'));
const Issues = lazy(() => import('./pages/Issues'));
const Cleaning = lazy(() => import('./pages/Cleaning'));
const Reports = lazy(() => import('./pages/Reports'));
const ColumnDetail = lazy(() => import('./pages/ColumnDetail'));
const Settings = lazy(() => import('./pages/Settings'));
const Search = lazy(() => import('./pages/Search'));
const Jobs = lazy(() => import('./pages/Jobs'));
const Webhooks = lazy(() => import('./pages/Webhooks'));
const Drift = lazy(() => import('./pages/Drift'));
const Correlations = lazy(() => import('./pages/Correlations'));
const Contracts = lazy(() => import('./pages/Contracts'));
const items = [
    ['/', 'Overview'], ['/upload', 'Datasets'], ['/issues', 'Issues'],
    ['/cleaning', 'Cleaning'], ['/reports', 'Reports'], ['/drift', 'Drift'],
    ['/correlations', 'Correlations'], ['/contracts', 'Contracts'], ['/jobs', 'Jobs'], ['/webhooks', 'Webhooks'],
    ['/search', 'Search'], ['/settings', 'Settings'],
];
function Skeleton() {
    return (_jsxs("div", { "aria-busy": "true", "aria-label": "Loading", children: [_jsx("div", { className: "card mt-4 animate-pulse", children: _jsx("div", { className: "h-6 w-1/3 bg-neutral-800 rounded" }) }), _jsx("div", { className: "card mt-3 animate-pulse", children: _jsx("div", { className: "h-40 bg-neutral-800 rounded" }) })] }));
}
export default function App() {
    const nav = useNavigate();
    const ds = useQuery({ queryKey: ['datasets'], queryFn: () => api('/api/v1/datasets?page_size=5') });
    return (_jsxs("div", { className: "flex min-h-screen", children: [_jsxs("aside", { className: "w-56 shrink-0 border-r border-neutral-800 bg-[#101012] p-4 hidden md:block", "aria-label": "Main", children: [_jsx("h1", { className: "text-sm font-semibold tracking-wide", children: "DQ OBSERVATORY" }), _jsx("p", { className: "text-xs text-neutral-500 mb-4", children: "v0.1 \u00B7 dq-engine-0.1.0" }), _jsx("nav", { className: "flex flex-col gap-1", children: items.map(([to, label]) => (_jsx(NavLink, { to: to, className: ({ isActive }) => `rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-neutral-800 text-white' : 'text-neutral-400 hover:bg-neutral-900'}`, children: label }, to))) }), _jsx("div", { className: "mt-6 text-xs text-neutral-500", children: "Dataset" }), _jsx("select", { "aria-label": "Dataset selector", className: "mt-1 w-full bg-neutral-900 text-xs p-2 rounded", value: new URLSearchParams(window.location.search).get('dataset') || ds.data?.items?.[0]?.id || '', onChange: e => nav(`/?dataset=${e.target.value}`), children: (ds.data?.items || []).map((d) => (_jsxs("option", { value: d.id, children: [d.name, " \u00B7 ", d.rows, " rows"] }, d.id))) }), _jsx("div", { className: "mt-4 text-xs text-neutral-500", children: "Recent datasets" }), _jsx("div", { className: "mt-1 flex flex-col gap-1", children: (ds.data?.items || []).map((d) => (_jsxs("button", { className: "text-left text-xs text-neutral-300 hover:text-white truncate", onClick: () => nav(`/?dataset=${d.id}`), children: [d.name, " \u00B7 ", d.rows, " rows"] }, d.id))) })] }), _jsx("main", { className: "flex-1 p-4 md:p-8 max-w-6xl w-full", children: _jsx(Suspense, { fallback: _jsx(Skeleton, {}), children: _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(Overview, {}) }), _jsx(Route, { path: "/upload", element: _jsx(Upload, {}) }), _jsx(Route, { path: "/issues", element: _jsx(Issues, {}) }), _jsx(Route, { path: "/cleaning", element: _jsx(Cleaning, {}) }), _jsx(Route, { path: "/reports", element: _jsx(Reports, {}) }), _jsx(Route, { path: "/column", element: _jsx(ColumnDetail, {}) }), _jsx(Route, { path: "/search", element: _jsx(Search, {}) }), _jsx(Route, { path: "/settings", element: _jsx(Settings, {}) }), _jsx(Route, { path: "/jobs", element: _jsx(Jobs, {}) }), _jsx(Route, { path: "/webhooks", element: _jsx(Webhooks, {}) }), _jsx(Route, { path: "/drift", element: _jsx(Drift, {}) }), _jsx(Route, { path: "/correlations", element: _jsx(Correlations, {}) }), _jsx(Route, { path: "/contracts", element: _jsx(Contracts, {}) })] }) }) }), _jsx(Tour, {})] }));
}
