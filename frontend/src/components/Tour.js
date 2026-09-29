import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
const STEPS = [
    { key: 'nav', route: '/', selector: 'aside nav', title: 'Navegación principal', text: 'Muévete entre Overview, Issues, Cleaning, Reports, Drift, Correlations, Jobs y Webhooks.' },
    { key: 'dataset', route: '/', selector: 'select[aria-label="Dataset selector"]', title: 'Selector de dataset', text: 'El dataset activo se comparte entre páginas: score, issues, limpieza y reportes lo usan.' },
    { key: 'drift', route: '/drift', selector: 'input[aria-label="From version"]', title: 'Detección de drift', text: 'Compara dos versiones: schema drift y distribución (KS, PSI, KL, χ²) por columna.' },
    { key: 'correlations', route: '/correlations', selector: 'input[aria-label="Min correlation"]', title: 'Correlaciones', text: 'Pearson/Spearman/Kendall, Cramér y Theil. Ajusta el umbral mínimo y analiza.' },
    { key: 'jobs', route: '/jobs', selector: 'input[aria-label="Job name"]', title: 'Jobs programados', text: 'Crea jobs con cron. Necesitas rol admin/owner (schedule:manage): pruébalo cambiando el rol.' },
    { key: 'webhooks', route: '/webhooks', selector: 'input[aria-label="Webhook URL"]', title: 'Webhooks', text: 'Alertas firmadas con HMAC. Requieren webhook:manage. Fin del recorrido.' },
];
const DONE_KEY = 'dq-tour-done';
const LAST_SEEN_KEY = 'dq-tour-last-step';
export default function Tour() {
    const nav = useNavigate();
    const loc = useLocation();
    const [idx, setIdx] = useState(null);
    const [rect, setRect] = useState(null);
    const [animating, setAnimating] = useState(false);
    const [done] = useState(() => { try {
        return !!localStorage.getItem(DONE_KEY);
    }
    catch {
        return false;
    } });
    const stop = useCallback(() => {
        setIdx(null);
        setRect(null);
        setAnimating(false);
        try {
            localStorage.setItem(DONE_KEY, '1');
            localStorage.removeItem(LAST_SEEN_KEY);
        }
        catch { /* noop */ }
    }, []);
    const go = useCallback((direction) => {
        if (idx === null)
            return;
        const next = idx + direction;
        if (next >= 0 && next < STEPS.length) {
            setAnimating(true);
            setTimeout(() => { setIdx(next); setAnimating(false); }, 150);
        }
    }, [idx]);
    // resume from last seen step
    useEffect(() => {
        if (idx === null) {
            try {
                const last = localStorage.getItem(LAST_SEEN_KEY);
                if (last) {
                    const n = parseInt(last, 10);
                    if (n >= 0 && n < STEPS.length)
                        setIdx(n);
                }
            }
            catch { /* noop */ }
        }
    }, []);
    // save last seen step
    useEffect(() => {
        if (idx !== null) {
            try {
                localStorage.setItem(LAST_SEEN_KEY, String(idx));
            }
            catch { /* noop */ }
        }
    }, [idx]);
    // resolve + track target element
    useEffect(() => {
        if (idx === null || animating)
            return;
        const step = STEPS[idx];
        if (loc.pathname !== step.route)
            nav(step.route, { replace: false });
        let cancelled = false;
        let tries = 0;
        const find = () => {
            if (cancelled || animating)
                return;
            const el = document.querySelector(step.selector);
            if (el) {
                el.scrollIntoView({ block: 'center', behavior: 'smooth' });
                const update = () => {
                    if (cancelled || animating)
                        return;
                    const r = el.getBoundingClientRect();
                    setRect({ x: r.x, y: r.y, w: r.width, h: r.height });
                };
                update();
                window.addEventListener('scroll', update, true);
                window.addEventListener('resize', update);
                const t = setInterval(update, 500);
                timers.push(t);
                listeners.push(() => { window.removeEventListener('scroll', update, true); window.removeEventListener('resize', update); });
            }
            else if (++tries < 50) {
                timers.push(window.setTimeout(find, 100));
            }
        };
        const timers = [];
        const listeners = [];
        find();
        return () => { cancelled = true; timers.forEach(t => { clearTimeout(t); clearInterval(t); }); listeners.forEach(l => l()); };
    }, [idx, loc.pathname, nav, animating]);
    // Esc ends tour
    useEffect(() => {
        if (idx === null)
            return;
        const onKey = (e) => { if (e.key === 'Escape')
            stop(); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [idx, stop]);
    if (idx === null) {
        return (_jsx("button", { "aria-label": "Iniciar recorrido", title: done ? 'Repetir recorrido guiado' : 'Recorrido guiado', onClick: () => setIdx(0), className: "fixed bottom-4 right-4 z-50 rounded-full bg-neutral-100 px-4 py-2 text-sm font-medium text-black shadow-lg hover:bg-white transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-brass focus:ring-offset-2 focus:ring-offset-[#0b0e14]", children: "\u25B6 Recorrido" }));
    }
    const step = STEPS[idx];
    const last = idx === STEPS.length - 1;
    const pad = 6;
    const progress = ((idx + 1) / STEPS.length) * 100;
    const tipBelow = rect ? rect.y + rect.h + 220 > window.innerHeight : true;
    return (_jsxs("div", { "aria-label": "Recorrido guiado", children: [_jsx("div", { className: "fixed top-0 left-0 right-0 z-60 h-1 bg-neutral-900 border-b border-neutral-800", "aria-hidden": "true", children: _jsx("div", { className: "h-full bg-brass transition-all duration-300 ease-out", style: { width: `${progress}%` }, role: "progressbar", "aria-valuenow": Math.round(progress), "aria-valuemin": 0, "aria-valuemax": 100 }) }), _jsx("div", { className: "fixed inset-0 z-40 bg-black/60 transition-opacity duration-200", onClick: stop, "aria-hidden": "true" }), rect && (_jsx("div", { "aria-hidden": "true", className: "fixed z-40 rounded-lg border-2 border-brass pointer-events-none transition-all duration-300", style: {
                    left: rect.x - pad, top: rect.y - pad,
                    width: rect.w + pad * 2, height: rect.h + pad * 2,
                    boxShadow: '0 0 0 9999px rgba(0,0,0,0.55)',
                    opacity: animating ? 0.5 : 1
                } })), _jsxs("div", { role: "dialog", "aria-label": `Paso ${idx + 1} de ${STEPS.length}: ${step.title}`, className: "fixed z-50 w-80 max-w-[90vw] rounded-xl border border-neutral-700 bg-[#161618] p-4 shadow-2xl transition-all duration-300 ease-out", style: rect ? (tipBelow
                    ? { left: Math.max(8, Math.min(rect.x, window.innerWidth - 336)), top: Math.max(8, rect.y - 218) }
                    : { left: Math.max(8, Math.min(rect.x, window.innerWidth - 336)), top: rect.y + rect.h + 14 }) : { right: 16, bottom: 72 }, children: [_jsx("div", { className: "flex justify-center gap-1 mb-2", role: "status", "aria-label": `Paso ${idx + 1} de ${STEPS.length}`, children: STEPS.map((_, i) => (_jsx("div", { className: `w-2 h-2 rounded-full transition-all duration-300 ${i === idx ? 'bg-brass w-6' : i < idx ? 'bg-brass/60' : 'bg-neutral-700'}` }, i))) }), _jsx("h3", { className: "text-sm font-semibold", children: step.title }), _jsx("p", { className: "text-sm text-neutral-300 mt-1", children: step.text }), _jsxs("div", { className: "mt-3 flex gap-2", children: [idx > 0 && _jsx("button", { className: "badge", onClick: () => go(-1), disabled: animating, children: "Atr\u00E1s" }), !last && _jsx("button", { className: "badge", onClick: () => go(1), disabled: animating, children: "Siguiente" }), _jsx("button", { className: "badge", onClick: stop, disabled: animating, children: last ? 'Terminar' : 'Salir' })] })] })] }));
}
