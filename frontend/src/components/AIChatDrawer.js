import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User, Copy } from 'lucide-react';
import { useAI } from '../context/AIContext';
export default function AIChatDrawer() {
    const { messages, isLoading, streamError, sendMessage, clearChat, } = useAI();
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [datasetId, setDatasetId] = useState('');
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };
    useEffect(() => { scrollToBottom(); }, [messages]);
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim())
            return;
        const q = input;
        setInput('');
        await sendMessage(q, datasetId || undefined);
    };
    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
    };
    if (!isOpen) {
        return (_jsxs("button", { onClick: () => setIsOpen(true), className: "fixed bottom-4 right-4 z-50 rounded-full bg-brass/20 px-4 py-2 text-sm font-medium text-brass border border-brass/30 shadow-lg hover:bg-brass/30 transition-all duration-200 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-brass focus:ring-offset-2 focus:ring-offset-[#0b0e14]", "aria-label": "Abrir asistente IA", children: [_jsx(Bot, { className: "inline w-4 h-4 mr-1" }), " Asistente IA"] }));
    }
    return (_jsxs("div", { className: "fixed inset-0 z-50 flex flex-col", role: "dialog", "aria-label": "Asistente IA", children: [_jsx("div", { className: "absolute inset-0 bg-black/50 transition-opacity", onClick: () => setIsOpen(false), "aria-hidden": "true" }), _jsxs("div", { className: "absolute right-0 top-0 bottom-0 w-full max-w-xl bg-[#161618] border-l border-neutral-800 shadow-2xl flex flex-col transition-transform duration-300 ease-out", children: [_jsxs("div", { className: "flex items-center justify-between p-4 border-b border-neutral-800", children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsx(Bot, { className: "w-5 h-5 text-brass" }), _jsx("span", { className: "font-semibold text-white", children: "Asistente IA" }), _jsx("span", { className: "text-xs px-2 py-0.5 bg-neutral-800 text-neutral-400 rounded", children: "v3" })] }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsxs("select", { value: datasetId, onChange: e => setDatasetId(e.target.value), className: "text-xs bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-white", "aria-label": "Dataset para contexto", children: [_jsx("option", { value: "", children: "Sin dataset" }), _jsx("option", { value: "demo", children: "Demo dataset" })] }), _jsx("button", { onClick: () => setIsOpen(false), className: "p-1 rounded hover:bg-neutral-800 transition-colors", "aria-label": "Cerrar chat", children: _jsx(X, { className: "w-5 h-5 text-neutral-400" }) })] })] }), _jsxs("div", { className: "flex-1 overflow-y-auto p-4 space-y-4", ref: messagesEndRef, children: [messages.length === 0 && (_jsxs("div", { className: "text-center text-neutral-500 py-8", children: [_jsx(Bot, { className: "w-12 h-12 mx-auto text-neutral-700 mb-2" }), _jsx("p", { className: "text-sm", children: "Pregunta sobre tus datos, pide filtros o pide sugerencias de limpieza." }), _jsx("p", { className: "text-xs text-neutral-600 mt-1", children: "Ej: \"Filtrar emails con @gmail\" \u00B7 \"Sugerir fix para issue #123\" \u00B7 \"Predecir score tras limpiar\"" })] })), messages.map((msg, i) => (_jsxs("div", { className: `flex gap-2 ${msg.role === 'assistant' ? '' : 'flex-row-reverse'}`, children: [_jsx("div", { className: `flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'assistant' ? 'bg-brass/20 text-brass' : 'bg-neutral-800 text-neutral-400'}`, children: msg.role === 'assistant' ? _jsx(Bot, { className: "w-4 h-4" }) : _jsx(User, { className: "w-4 h-4" }) }), _jsxs("div", { className: `max-w-[80%] ${msg.role === 'assistant' ? 'text-left' : 'text-right'}`, children: [_jsx("div", { className: `inline-block px-3 py-2 rounded-xl ${msg.role === 'assistant' ? 'bg-neutral-900 text-white' : 'bg-brass/20 text-white'}`, children: _jsx("pre", { className: "whitespace-pre-wrap text-sm font-mono", children: msg.content }) }), msg.role === 'assistant' && (_jsxs("div", { className: "flex items-center gap-1 mt-1 text-xs text-neutral-500", children: [msg.tokensUsed && _jsxs("span", { children: [msg.tokensUsed, " tokens"] }), msg.latencyMs && _jsxs("span", { children: ["\u00B7 ", msg.latencyMs, "ms"] }), _jsx("button", { onClick: () => navigator.clipboard.writeText(msg.content), className: "p-1 hover:text-brass transition-colors", "aria-label": "Copiar respuesta", children: _jsx(Copy, { className: "w-3 h-3" }) })] }))] })] }, i))), isLoading && (_jsxs("div", { className: "flex gap-2 justify-start", children: [_jsx("div", { className: "w-8 h-8 rounded-full bg-neutral-800 flex items-center justify-center", children: _jsx(Bot, { className: "w-4 h-4 text-brass" }) }), _jsx("div", { className: "bg-neutral-900 px-3 py-2 rounded-xl", children: _jsxs("div", { className: "flex gap-1", children: [_jsx("span", { className: "w-2 h-2 bg-brass rounded-full animate-bounce", style: { animationDelay: '0ms' } }), _jsx("span", { className: "w-2 h-2 bg-brass rounded-full animate-bounce", style: { animationDelay: '150ms' } }), _jsx("span", { className: "w-2 h-2 bg-brass rounded-full animate-bounce", style: { animationDelay: '300ms' } })] }) })] })), _jsx("div", { ref: messagesEndRef })] }), streamError && (_jsx("div", { className: "p-3 mx-4 mb-2 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm", children: streamError })), _jsxs("form", { onSubmit: handleSubmit, className: "p-4 border-t border-neutral-800", children: [_jsxs("div", { className: "flex gap-2", children: [_jsx("textarea", { ref: inputRef, value: input, onChange: e => setInput(e.target.value), placeholder: "Pregunta sobre tus datos...", className: "flex-1 bg-neutral-900 border border-neutral-700 rounded-xl px-3 py-2 text-white placeholder-neutral-500 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brass focus:border-transparent", rows: 1, style: { maxHeight: '100px' }, disabled: isLoading, onKeyDown: e => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                handleSubmit(e);
                                            }
                                        } }), _jsx("button", { type: "submit", disabled: !input.trim() || isLoading, className: "px-4 py-2 bg-brass text-black font-medium rounded-xl hover:bg-brass/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors", "aria-label": "Enviar pregunta", children: _jsx(Send, { className: "w-5 h-5" }) })] }), _jsx("p", { className: "text-xs text-neutral-500 text-center mt-1", children: "Shift+Enter para nueva l\u00EDnea \u00B7 Enter para enviar" })] })] })] }));
}
