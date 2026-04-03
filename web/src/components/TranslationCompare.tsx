'use client';

import { useState, useEffect } from 'react';
import { compareTranslations, type CompareResult } from '@/lib/api';
import { formatTime } from '@/lib/utils';

interface TranslationCompareProps {
    jobId: string;
}

const ENGINE_COLORS: Record<string, string> = {
    'Groq': 'text-green-400',
    'SambaNova': 'text-blue-400',
    'Gemini': 'text-purple-400',
    'Google': 'text-red-400',
    'Google+Polish': 'text-orange-400',
    'IndicTrans2': 'text-teal-400',
    'IndicTrans2+': 'text-cyan-400',
    'Chain Dub': 'text-yellow-400',
    'Turbo': 'text-pink-400',
};

export default function TranslationCompare({ jobId }: TranslationCompareProps) {
    const [available, setAvailable] = useState<Array<{ key: string; label: string }>>([]);
    const [selectedEngine, setSelectedEngine] = useState<string | null>(null);
    const [result, setResult] = useState<CompareResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [segCount, setSegCount] = useState(10);

    // Fetch available engines on mount
    useEffect(() => {
        compareTranslations(jobId, [], 0)
            .then((data) => {
                if (data.available) setAvailable(data.available);
            })
            .catch(() => {
                setAvailable([
                    { key: 'groq', label: 'Groq' },
                    { key: 'sambanova', label: 'SambaNova' },
                    { key: 'gemini', label: 'Gemini' },
                    { key: 'google', label: 'Google' },
                    { key: 'google_polish', label: 'Google+Polish' },
                    { key: 'nllb', label: 'IndicTrans2' },
                    { key: 'nllb_polish', label: 'IndicTrans2+' },
                    { key: 'chain_dub', label: 'Chain Dub' },
                ]);
            });
    }, [jobId]);

    const tryEngine = async (engineKey: string) => {
        setSelectedEngine(engineKey);
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await compareTranslations(jobId, [engineKey], segCount);
            setResult(data);
            if (data.available) setAvailable(data.available);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed');
        }
        setLoading(false);
    };

    const engineLabel = available.find(e => e.key === selectedEngine)?.label || selectedEngine || '';
    const segments = result?.engines?.[engineLabel] || [];

    return (
        <div className="glass-card overflow-hidden">
            <div className="px-5 py-3 border-b border-border">
                <h3 className="text-sm font-semibold text-text-primary mb-2">Try Translation Engine</h3>
                <p className="text-[10px] text-text-muted mb-3">
                    Pick an engine to preview its translation. Try different ones to find the best quality.
                </p>

                {/* Engine selector */}
                <div className="flex flex-wrap gap-2 mb-3">
                    {available.map((eng) => (
                        <button
                            key={eng.key}
                            type="button"
                            onClick={() => tryEngine(eng.key)}
                            disabled={loading}
                            className={`
                                px-3 py-1.5 rounded-lg text-xs font-medium transition-all border
                                ${selectedEngine === eng.key
                                    ? 'bg-primary/20 border-primary text-primary-light'
                                    : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                ${loading ? 'opacity-50' : ''}
                            `}
                        >
                            {eng.label}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-3">
                    <label className="text-xs text-text-muted">Segments:</label>
                    <select
                        title="Number of segments"
                        value={segCount}
                        onChange={(e) => setSegCount(Number(e.target.value))}
                        className="text-xs bg-white/5 border border-white/10 rounded px-2 py-1 text-text-primary"
                    >
                        <option value={5}>5</option>
                        <option value={10}>10</option>
                        <option value={15}>15</option>
                        <option value={20}>20</option>
                    </select>
                    {loading && (
                        <div className="flex items-center gap-2">
                            <svg className="animate-spin text-primary" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                            </svg>
                            <span className="text-xs text-text-muted">Running {engineLabel}...</span>
                        </div>
                    )}
                </div>
                {error && <p className="text-xs text-error mt-2">{error}</p>}
            </div>

            {/* Results */}
            {segments.length > 0 && (
                <>
                    <div className="px-5 py-2 border-b border-border bg-white/[0.02]">
                        <span className={`text-xs font-semibold ${ENGINE_COLORS[engineLabel] || 'text-primary'}`}>
                            {engineLabel}
                        </span>
                        <span className="text-[10px] text-text-muted ml-2">
                            {segments.length} segments
                        </span>
                    </div>
                    <div className="max-h-[400px] overflow-y-auto">
                        {segments.map((seg, i) => (
                            <div
                                key={i}
                                className="grid grid-cols-[50px_1fr_1fr] gap-3 px-5 py-2.5 border-b border-border/30 hover:bg-white/[0.02]"
                            >
                                <span className="text-xs text-text-muted font-mono">
                                    {formatTime(seg.start)}
                                </span>
                                <p className="text-xs text-text-secondary leading-relaxed">
                                    {seg.text}
                                </p>
                                <p className={`text-xs leading-relaxed ${ENGINE_COLORS[engineLabel] || 'text-text-primary'}`}>
                                    {seg.text_translated || '—'}
                                </p>
                            </div>
                        ))}
                    </div>
                </>
            )}

            {!loading && segments.length === 0 && selectedEngine && !error && (
                <div className="px-5 py-6 text-center text-xs text-text-muted">
                    No results — try another engine
                </div>
            )}
        </div>
    );
}
