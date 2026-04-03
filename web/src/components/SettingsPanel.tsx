'use client';

import { useState } from 'react';

export interface DubbingSettings {
    asr_model: string;
    translation_engine: string;
    tts_rate: string;
    mix_original: boolean;
    original_volume: number;
    use_cosyvoice: boolean;
    use_chatterbox: boolean;
    use_indic_parler: boolean;
    use_elevenlabs: boolean;
    use_google_tts: boolean;
    use_coqui_xtts: boolean;
    use_edge_tts: boolean;
    prefer_youtube_subs: boolean;
    use_yt_translate: boolean;
    multi_speaker: boolean;
    transcribe_only: boolean;
    audio_priority: boolean;
    audio_untouchable: boolean;
    post_tts_level: string;
    audio_bitrate: string;
    encode_preset: string;
    split_duration: number;
    dub_duration: number;
    fast_assemble: boolean;
    dub_chain: string[];
    enable_manual_review: boolean;
    use_whisperx: boolean;
    simplify_english: boolean;
    step_by_step: boolean;
    use_new_pipeline: boolean;
    pipeline_mode?: string;
    _input_mode?: string;
}

interface SettingsPanelProps {
    settings: DubbingSettings;
    onChange: (settings: DubbingSettings) => void;
}

export default function SettingsPanel({ settings, onChange }: SettingsPanelProps) {
    const [open, setOpen] = useState(false);

    const update = (partial: Partial<DubbingSettings>) => {
        onChange({ ...settings, ...partial });
    };

    return (
        <div className="glass-card overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-white/[0.02] transition-colors"
            >
                <div className="flex items-center gap-2">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
                        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                        <circle cx="12" cy="12" r="3" />
                    </svg>
                    <span className="text-sm font-medium text-text-secondary">Advanced Settings</span>
                </div>
                <svg
                    width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                    className={`text-text-muted transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
                >
                    <path d="m6 9 6 6 6-6" />
                </svg>
            </button>

            {open && (() => {
                // ── Pipeline mode ──
                const mode = (settings as any).pipeline_mode || 'classic';
                const isClassic = mode === 'classic';
                const isHybrid = mode === 'hybrid';
                const isNew = mode === 'new';
                const isOneFlow = mode === 'oneflow';
                const isSrtMode = settings._input_mode === 'srt';

                // ── Dependency flags ──
                const ytTranslateOn = settings.use_yt_translate;
                const ytSubsOn = settings.prefer_youtube_subs;
                const transcribeOnly = settings.transcribe_only;
                // Whisper disabled when YouTube provides subs, New pipeline, OneFlow, or SRT mode
                const whisperDisabled = ytTranslateOn || ytSubsOn || isOneFlow || isSrtMode;
                const whisperxDisabled = whisperDisabled;
                // Translation disabled only when YT gives Hindi directly
                const translationDisabled = ytTranslateOn || isOneFlow || isSrtMode;
                // Simplify disabled only when YT gives Hindi (no English to simplify)
                const simplifyDisabled = ytTranslateOn || isOneFlow || isSrtMode;

                return (<div className="px-5 pb-5 space-y-5 animate-slide-up border-t border-border pt-4">
                    {/* ── Pipeline Mode Banner ── */}
                    <div className={`rounded-lg p-3 text-xs ${
                        isOneFlow ? 'bg-red-500/10 border border-red-500/30 text-red-400' :
                        isNew ? 'bg-green-500/10 border border-green-500/30 text-green-400' :
                        isHybrid ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400' :
                        'bg-primary/10 border border-primary/30 text-primary-light'
                    }`}>
                        <p className="font-medium mb-1">
                            {isOneFlow ? 'OneFlow (Fastest)' :
                             isNew ? 'New Pipeline (Experimental)' :
                             isHybrid ? 'Hybrid Pipeline (Recommended)' :
                             'Classic Pipeline (Proven)'}
                        </p>
                        <p className="text-[10px] opacity-80">
                            {isOneFlow ? 'Groq Whisper → Google Translate (100 workers) → Edge-TTS (150 workers) → fixed 1.15x → video adapts. No LLM, no cue rebuild, just speed.' :
                             isNew ? 'Parakeet ASR + WhisperX timing + DP cue builder + glossary lock. All new modular code.' :
                             isHybrid ? 'Whisper ASR (all options) + DP cue builder + glossary + Hindi fitting + QC gates. Best quality + proven infrastructure.' :
                             'Full monolith pipeline. All engines, all options, battle-tested. Maximum flexibility.'}
                        </p>
                    </div>

                    {/* SRT Mode: lock transcription + translation (SRT already has translated text) */}
                    {isSrtMode && (
                        <div className="rounded-lg bg-purple-500/5 border border-purple-500/20 p-3">
                            <p className="text-xs font-medium text-purple-400">SRT Dub Mode</p>
                            <p className="text-[10px] text-text-muted mt-1">
                                Transcription + Translation are skipped — your SRT file provides the text.
                                Only TTS, Audio, and Assembly settings apply.
                            </p>
                        </div>
                    )}

                    {/* OneFlow: lock ALL settings — everything is pre-configured */}
                    {isOneFlow && (
                        <div className="rounded-lg bg-red-500/5 border border-red-500/20 p-3 space-y-2">
                            <p className="text-xs font-medium text-red-400">OneFlow — All Settings Fixed</p>
                            <div className="grid grid-cols-2 gap-2 text-[10px] text-text-muted">
                                <div>ASR: Groq Whisper (cloud)</div>
                                <div>Translate: Google (100 workers)</div>
                                <div>TTS: Edge-TTS (150 workers)</div>
                                <div>Speed: fixed 1.15x uniform</div>
                                <div>QC: 1 check + 1 retry per stage</div>
                                <div>Video: adapts to audio (freeze/slow)</div>
                            </div>
                            <p className="text-[10px] opacity-60">All settings below are ignored in OneFlow mode.</p>
                        </div>
                    )}

                    {/* ── Transcription + Translation: HIDDEN in SRT mode ── */}
                    {!isSrtMode && (<>
                    {/* ── Transcription Section ── */}
                    {/* Classic + Hybrid: show Whisper options. New: show Parakeet info */}
                    <div>
                        <p className="text-sm font-medium text-text-primary mb-1">
                            {isNew ? 'Transcription (Parakeet + WhisperX)' : 'Transcription (Whisper)'}
                        </p>
                        <p className="text-[10px] text-text-muted mb-3">
                            Converts speech in the video to text. Larger models are slower but more accurate.
                            {whisperDisabled && <span className="text-yellow-400 ml-1"> (Whisper skipped — using YouTube subs)</span>}
                        </p>
                        <div className="space-y-3">
                            <div className={whisperDisabled || isNew ? 'opacity-40 pointer-events-none' : ''}>
                                <p className="text-xs text-text-muted mb-1.5">
                                    {isNew ? 'ASR Model (Parakeet — fixed)' : 'Whisper Model'}
                                </p>
                                <div className="grid grid-cols-5 gap-1.5">
                                    {[
                                        { value: 'base',          label: 'Base',    desc: 'Fastest' },
                                        { value: 'small',         label: 'Small',   desc: 'Fast' },
                                        { value: 'medium',        label: 'Medium',  desc: 'Balanced' },
                                        { value: 'large-v3-turbo',label: 'Turbo',   desc: 'Fast+accurate' },
                                        { value: 'large-v3',      label: 'Large-v3',desc: 'Best' },
                                        { value: 'parakeet',      label: 'Parakeet',desc: 'NVIDIA SOTA' },
                                        { value: 'groq-whisper',  label: 'Groq',    desc: 'Cloud, fastest' },
                                    ].map((m) => (
                                        <button
                                            key={m.value}
                                            onClick={() => update({ asr_model: m.value })}
                                            className={`
                                                px-3 py-2 rounded-lg text-xs text-center transition-all border
                                                ${settings.asr_model === m.value
                                                    ? 'bg-primary/20 border-primary text-primary-light'
                                                    : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                            `}
                                        >
                                            <div className="font-medium">{m.label}</div>
                                            <div className="text-[10px] opacity-70 mt-0.5">{m.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* YouTube Subtitles — disabled when YT Auto-Translate or New pipeline */}
                            <div className={`flex items-center justify-between ${(ytTranslateOn || isNew || isOneFlow || isSrtMode) ? 'opacity-40 pointer-events-none' : ''}`}>
                                <div>
                                    <p className="text-sm text-text-primary">Use YouTube Subtitles</p>
                                    <p className="text-xs text-text-muted">
                                        Skip Whisper, use existing subs (faster)
                                        {ytTranslateOn && <span className="text-yellow-400 ml-1">— off: YT Translate active</span>}
                                        {isNew && <span className="text-yellow-400 ml-1">— off: New pipeline uses Parakeet</span>}
                                    </p>
                                </div>
                                <button
                                    type="button" title="Toggle YouTube Subtitles"
                                    onClick={() => update({
                                        prefer_youtube_subs: !settings.prefer_youtube_subs,
                                        ...(!settings.prefer_youtube_subs ? { use_yt_translate: false } : {}),
                                    })}
                                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.prefer_youtube_subs ? 'bg-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.prefer_youtube_subs ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            {/* YouTube Auto-Translate — disabled when YT Subtitles, Transcribe Only, or New pipeline */}
                            <div className={`flex items-center justify-between ${(ytSubsOn || transcribeOnly || isNew || isOneFlow || isSrtMode) ? 'opacity-40 pointer-events-none' : ''}`}>
                                <div>
                                    <p className="text-sm text-text-primary">YT Auto-Translate</p>
                                    <p className="text-xs text-text-muted">
                                        Use YouTube&apos;s translated subs (skips Whisper + translation)
                                        {ytSubsOn && <span className="text-yellow-400 ml-1">— off: YT Subtitles active</span>}
                                        {transcribeOnly && !ytSubsOn && <span className="text-yellow-400 ml-1">— off: Transcribe Only active</span>}
                                    </p>
                                </div>
                                <button
                                    type="button" title="Toggle YouTube Translate"
                                    onClick={() => update({
                                        use_yt_translate: !settings.use_yt_translate,
                                        ...(!settings.use_yt_translate ? { prefer_youtube_subs: false, transcribe_only: false } : {}),
                                    })}
                                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.use_yt_translate ? 'bg-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.use_yt_translate ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            {/* Chain Dub — disabled when YT Translate or New pipeline */}
                            <div className={`flex items-center justify-between ${(ytTranslateOn || isNew || isOneFlow || isSrtMode) ? 'opacity-40 pointer-events-none' : ''}`}>
                                <div>
                                    <p className="text-sm text-text-primary">Chain Dub (English → Hindi)</p>
                                    <p className="text-xs text-text-muted">Dub to English first using subs, then English to Hindi (best for non-English videos)</p>
                                </div>
                                <button
                                    type="button" title="Toggle Chain Dub"
                                    onClick={() => update({ dub_chain: settings.dub_chain.length > 0 ? [] : ['en', 'hi'] })}
                                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.dub_chain.length > 0 ? 'bg-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.dub_chain.length > 0 ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            {/* WhisperX — disabled when Whisper skipped or New pipeline (built-in) */}
                            <div className={`flex items-center justify-between ${(whisperxDisabled || isNew || isOneFlow || isSrtMode) ? 'opacity-40 pointer-events-none' : ''}`}>
                                <div>
                                    <p className="text-sm text-text-primary">WhisperX Alignment</p>
                                    <p className="text-xs text-text-muted">
                                        Force word-level timestamp alignment (requires whisperx)
                                        {whisperDisabled && <span className="text-yellow-400 ml-1">— needs Whisper</span>}
                                    </p>
                                </div>
                                <button
                                    type="button" title="Toggle WhisperX Alignment" onClick={() => update({ use_whisperx: !settings.use_whisperx })}
                                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.use_whisperx ? 'bg-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.use_whisperx ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            {/* Simplify English — only for Classic mode. Hybrid/New use DP cue builder */}
                            <div className={`flex items-center justify-between ${simplifyDisabled || !isClassic ? 'opacity-40 pointer-events-none' : ''}`}>
                                <div>
                                    <p className="text-sm text-text-primary">Simplify English</p>
                                    <p className="text-xs text-text-muted">
                                        Rewrite complex English into simple sentences — much better Hindi
                                        {ytTranslateOn && <span className="text-yellow-400 ml-1">— not needed with YT Translate</span>}
                                    </p>
                                </div>
                                <button
                                    type="button" title="Toggle Simplify English" onClick={() => update({ simplify_english: !settings.simplify_english })}
                                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.simplify_english ? 'bg-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.simplify_english ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* ── Translation Section ── */}
                    <div className={translationDisabled ? 'opacity-40 pointer-events-none' : ''}>
                        <p className="text-sm font-medium text-text-primary mb-1">Translation Engine</p>
                        <p className="text-[10px] text-text-muted mb-3">
                            {(isHybrid || isNew)
                                ? 'Translation with DP cue boundaries + glossary lock + Hindi fitting + QC gates.'
                                : 'How the transcribed text gets translated. Auto picks the best for Hindi.'}
                            {ytTranslateOn && <span className="text-yellow-400 ml-1"> (Skipped — using YouTube translated subs)</span>}
                        </p>
                        <div className="grid grid-cols-5 gap-2 mb-3">
                            {[
                                { value: 'auto', label: 'Auto', desc: 'Best available' },
                                { value: 'turbo', label: 'Turbo', desc: 'Groq+SambaNova parallel' },
                                { value: 'groq', label: 'Groq', desc: 'Llama 3.3 70B (free)' },
                                { value: 'sambanova', label: 'SambaNova', desc: 'Llama 3.3 70B (free)' },
                                { value: 'gemini', label: 'Gemini', desc: 'Google AI (free)' },
                            ].map((m) => (
                                <button
                                    key={m.value}
                                    onClick={() => update({ translation_engine: m.value })}
                                    className={`
                                        px-3 py-2 rounded-lg text-xs text-center transition-all border
                                        ${settings.translation_engine === m.value
                                            ? 'bg-primary/20 border-primary text-primary-light'
                                            : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                    `}
                                >
                                    <div className="font-medium">{m.label}</div>
                                    <div className="text-[10px] opacity-70 mt-0.5">{m.desc}</div>
                                </button>
                            ))}
                        </div>
                        <div className="grid grid-cols-4 gap-2">
                            {[
                                { value: 'chain_dub', label: 'Chain Dub', desc: 'IndicTrans2+ → Turbo refine' },
                                { value: 'nllb_polish', label: 'IndicTrans2+', desc: 'IndicTrans2 → LLM → Rules' },
                                { value: 'google_polish', label: 'Google+Polish', desc: 'Fast Google → LLM polish' },
                                { value: 'nllb', label: 'IndicTrans2', desc: 'Local meaning model' },
                                { value: 'ollama', label: 'Ollama', desc: 'Local LLM (GPU)' },
                                { value: 'hinglish', label: 'Hinglish AI', desc: 'Custom Hindi model' },
                                { value: 'google', label: 'Google', desc: 'Free, basic' },
                                { value: 'seamless', label: 'SeamlessM4T', desc: 'Meta end-to-end (GPU)' },
                            ].map((m) => (
                                <button
                                    key={m.value}
                                    onClick={() => update({ translation_engine: m.value })}
                                    className={`
                                        px-3 py-2 rounded-lg text-xs text-center transition-all border
                                        ${settings.translation_engine === m.value
                                            ? 'bg-primary/20 border-primary text-primary-light'
                                            : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                    `}
                                >
                                    <div className="font-medium">{m.label}</div>
                                    <div className="text-[10px] opacity-70 mt-0.5">{m.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* ── New Pipeline Features (hybrid + new only) ── */}
                    {(isHybrid || isNew) && (
                        <div className="rounded-lg bg-green-500/5 border border-green-500/20 p-3 space-y-2">
                            <p className="text-xs font-medium text-green-400">New Pipeline Features (Active)</p>
                            <div className="grid grid-cols-2 gap-2 text-[10px] text-text-muted">
                                <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                    DP Cue Builder
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                    Glossary Lock
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                    Hindi Fitting
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                    Pre-TTS QC Gate
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                    English QC
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                                    {isNew ? 'Parakeet + WhisperX' : 'Whisper + DP Cues'}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Transcribe Only — disabled when YT Auto-Translate or New pipeline */}
                    <div className={`flex items-center justify-between ${(ytTranslateOn || isNew || isOneFlow || isSrtMode) ? 'opacity-40 pointer-events-none' : ''}`}>
                        <div>
                            <p className="text-sm text-text-primary">Transcribe Only</p>
                            <p className="text-xs text-text-muted">
                                Get SRT to translate yourself (e.g. with Claude), then upload back
                                {ytTranslateOn && <span className="text-yellow-400 ml-1">— off: YT Translate active</span>}
                            </p>
                        </div>
                        <button
                            type="button" title="Toggle Transcribe Only"
                            onClick={() => update({
                                transcribe_only: !settings.transcribe_only,
                                ...(!settings.transcribe_only ? { use_yt_translate: false } : {}),
                            })}
                            className={`w-11 h-6 rounded-full transition-colors relative ${settings.transcribe_only ? 'bg-primary' : 'bg-white/10'}`}
                        >
                            <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.transcribe_only ? 'translate-x-6' : 'translate-x-1'}`} />
                        </button>
                    </div>

                    {/* Multi-Speaker Voices — disabled when YT Translate or New pipeline */}
                    <div className={`flex items-center justify-between ${(ytTranslateOn || isNew || isOneFlow || isSrtMode) ? 'opacity-40 pointer-events-none' : ''}`}>
                        <div>
                            <p className="text-sm text-text-primary">Multi-Speaker Voices</p>
                            <p className="text-xs text-text-muted">Detect speakers & assign distinct voices (needs HF_TOKEN, adds ~30s)</p>
                        </div>
                        <button
                            type="button" title="Toggle Multi-speaker" onClick={() => update({ multi_speaker: !settings.multi_speaker })}
                            className={`
                                w-11 h-6 rounded-full transition-colors relative
                                ${settings.multi_speaker ? 'bg-primary' : 'bg-white/10'}
                            `}
                        >
                            <div className={`
                                w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                ${settings.multi_speaker ? 'translate-x-6' : 'translate-x-1'}
                            `} />
                        </button>
                    </div>

                    </>)}
                    {/* ── End of Transcription + Translation (hidden in SRT mode) ── */}

                    {/* TTS Engines */}
                    <div>
                        <p className="text-sm font-medium text-text-primary mb-1">TTS Engines</p>
                        <p className="text-[10px] text-text-muted mb-3">
                            English dub auto-uses: Chatterbox-Turbo → Chatterbox Multilingual → XTTS v2 → Edge-TTS (all free, local). Non-English uses toggles below. CosyVoice 2 = best for Hindi.
                        </p>
                        <div className="space-y-3">
                            {/* CosyVoice 2 */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">CosyVoice 2 ⭐</p>
                                    <p className="text-xs text-text-muted">Free, GPU, near-ElevenLabs quality, voice clones original speaker in Hindi</p>
                                </div>
                                <button
                                    type="button"
                                    title="Toggle CosyVoice 2"
                                    onClick={() => update({ use_cosyvoice: !settings.use_cosyvoice })}
                                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.use_cosyvoice ? 'bg-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.use_cosyvoice ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>
                            {/* Chatterbox */}
                            {/* Indic Parler-TTS */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Indic Parler-TTS</p>
                                    <p className="text-xs text-text-muted">Free, GPU, best open-source for Hindi/Indic (AI4Bharat)</p>
                                </div>
                                <button
                                    type="button" title="Toggle Indic Parler-TTS" onClick={() => update({ use_indic_parler: !settings.use_indic_parler })}
                                    className={`w-11 h-6 rounded-full transition-colors relative ${settings.use_indic_parler ? 'bg-primary' : 'bg-white/10'}`}
                                >
                                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${settings.use_indic_parler ? 'translate-x-6' : 'translate-x-1'}`} />
                                </button>
                            </div>
                            {/* Chatterbox */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Chatterbox AI</p>
                                    <p className="text-xs text-text-muted">Free, GPU required, most human-like</p>
                                </div>
                                <button
                                    type="button" title="Toggle Chatterbox" onClick={() => update({ use_chatterbox: !settings.use_chatterbox })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.use_chatterbox ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.use_chatterbox ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* ElevenLabs */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">ElevenLabs</p>
                                    <p className="text-xs text-text-muted">
                                        Paid API, needs ELEVENLABS_API_KEY in .env
                                        {settings.use_elevenlabs && <span className="text-yellow-400 ml-1">— make sure API key is set or job will fail!</span>}
                                    </p>
                                </div>
                                <button
                                    type="button" title="Toggle ElevenLabs" onClick={() => update({ use_elevenlabs: !settings.use_elevenlabs })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.use_elevenlabs ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.use_elevenlabs ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* Coqui XTTS v2 */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Coqui XTTS v2</p>
                                    <p className="text-xs text-text-muted">Free, GPU required, voice cloning from original speaker</p>
                                </div>
                                <button
                                    type="button" title="Toggle Coqui XTTS v2" onClick={() => update({ use_coqui_xtts: !settings.use_coqui_xtts })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.use_coqui_xtts ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.use_coqui_xtts ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* Google Cloud TTS */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Google Cloud TTS</p>
                                    <p className="text-xs text-text-muted">Free 1M chars/mo, WaveNet/Neural2 voices, needs GCP credentials</p>
                                </div>
                                <button
                                    type="button" title="Toggle Google TTS" onClick={() => update({ use_google_tts: !settings.use_google_tts })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.use_google_tts ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.use_google_tts ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* Edge-TTS */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Edge-TTS</p>
                                    <p className="text-xs text-text-muted">Free, no GPU needed, decent quality</p>
                                </div>
                                <button
                                    type="button" title="Toggle Edge TTS" onClick={() => update({ use_edge_tts: !settings.use_edge_tts })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.use_edge_tts ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.use_edge_tts ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>
                        </div>
                        {settings.use_coqui_xtts && settings.use_edge_tts ? (
                            <p className="text-[10px] text-primary mt-2 font-medium">
                                Hybrid Mode: Coqui XTTS + Edge-TTS will run in parallel (~2x faster)
                            </p>
                        ) : (
                            <p className="text-[10px] text-text-muted mt-2">First enabled engine from top to bottom will be used. Enable both Coqui + Edge for hybrid parallel mode.</p>
                        )}
                    </div>

                    {/* TTS Speech Rate */}
                    <div>
                        <label className="label mb-2 block">
                            Speech Rate: <span className="text-primary-light">{settings.tts_rate}</span>
                        </label>
                        <input
                            type="range"
                            min={-50}
                            max={50}
                            value={parseInt(settings.tts_rate) || 0}
                            onChange={(e) => {
                                const v = parseInt(e.target.value);
                                update({ tts_rate: `${v >= 0 ? '+' : ''}${v}%` });
                            }}
                            className="w-full accent-primary"
                        />
                        <div className="flex justify-between text-[10px] text-text-muted">
                            <span>Slower</span>
                            <span>Normal</span>
                            <span>Faster</span>
                        </div>
                    </div>

                    {/* Mix Background Music */}
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-text-primary">Mix Background Music</p>
                            <p className="text-xs text-text-muted">Keep original background music (vocals removed) behind dubbed voice</p>
                        </div>
                        <button
                            type="button" title="Toggle Mix Original Audio" onClick={() => update({ mix_original: !settings.mix_original })}
                            className={`
                                w-11 h-6 rounded-full transition-colors relative
                                ${settings.mix_original ? 'bg-primary' : 'bg-white/10'}
                            `}
                        >
                            <div className={`
                                w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                ${settings.mix_original ? 'translate-x-6' : 'translate-x-1'}
                            `} />
                        </button>
                    </div>

                    {/* Music Volume */}
                    {settings.mix_original && (
                        <div className="animate-slide-up">
                            <label className="label mb-2 block">
                                Music Volume: <span className="text-primary-light">{Math.round(settings.original_volume * 100)}%</span>
                            </label>
                            <input
                                type="range"
                                min={0}
                                max={50}
                                value={settings.original_volume * 100}
                                onChange={(e) => update({ original_volume: parseInt(e.target.value) / 100 })}
                                className="w-full accent-primary"
                                title="Original volume"
                            />
                        </div>
                    )}

                    {/* ── Audio & Performance Section ── */}
                    <div>
                        <p className="text-sm font-medium text-text-primary mb-1">Audio & Performance</p>
                        <p className="text-[10px] text-text-muted mb-3">
                            Controls how audio and video are assembled. Audio Priority lets TTS speak naturally without speed changes.
                        </p>
                        <div className="space-y-3">
                            {/* Audio Priority */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Audio Priority</p>
                                    <p className="text-xs text-text-muted">TTS speaks naturally, video adjusts to match (best for listening)</p>
                                </div>
                                <button
                                    type="button" title="Toggle Audio Priority" onClick={() => update({ audio_priority: !settings.audio_priority })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.audio_priority ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.audio_priority ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* Audio Untouchable */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Audio Untouchable</p>
                                    <p className="text-xs text-text-muted">TTS output is never modified — no trim, no normalize, no speed change</p>
                                </div>
                                <button
                                    type="button" title="Toggle Audio Untouchable" onClick={() => update({ audio_untouchable: !settings.audio_untouchable })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.audio_untouchable ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.audio_untouchable ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* Post-TTS Processing Level */}
                            <div>
                                <p className="text-xs text-text-muted mb-1.5">Post-TTS Processing</p>
                                <div className="grid grid-cols-3 gap-2">
                                    {[
                                        { value: 'full', label: 'Full', desc: 'Trim+Norm+Compress' },
                                        { value: 'minimal', label: 'Minimal', desc: 'Fade+Loudness only' },
                                        { value: 'none', label: 'None', desc: 'Zero processing' },
                                    ].map((m) => (
                                        <button key={m.value} type="button"
                                            onClick={() => update({ post_tts_level: m.value })}
                                            className={`
                                                px-2 py-1.5 rounded-lg text-xs font-medium transition-all text-center
                                                ${settings.post_tts_level === m.value
                                                    ? 'bg-primary/20 text-primary border border-primary/30'
                                                    : 'bg-white/5 text-text-muted border border-white/5 hover:border-white/20'}
                                            `}
                                        >
                                            <div>{m.label}</div>
                                            <div className="text-[10px] opacity-60">{m.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Audio Bitrate */}
                            <div>
                                <p className="text-xs text-text-muted mb-1.5">Audio Quality</p>
                                <div className="grid grid-cols-4 gap-2">
                                    {[
                                        { value: '128k', label: '128k', desc: 'Small file' },
                                        { value: '192k', label: '192k', desc: 'Standard' },
                                        { value: '256k', label: '256k', desc: 'High' },
                                        { value: '320k', label: '320k', desc: 'Best' },
                                    ].map((m) => (
                                        <button
                                            type="button"
                                            key={m.value}
                                            onClick={() => update({ audio_bitrate: m.value })}
                                            className={`
                                                px-2 py-2 rounded-lg text-xs text-center transition-all border
                                                ${settings.audio_bitrate === m.value
                                                    ? 'bg-primary/20 border-primary text-primary-light'
                                                    : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                            `}
                                        >
                                            <div className="font-medium">{m.label}</div>
                                            <div className="text-[10px] opacity-70 mt-0.5">{m.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Encode Speed */}
                            <div>
                                <p className="text-xs text-text-muted mb-1.5">Video Encode Speed</p>
                                <div className="grid grid-cols-4 gap-2">
                                    {[
                                        { value: 'ultrafast', label: 'Ultra Fast', desc: 'Fastest' },
                                        { value: 'veryfast', label: 'Very Fast', desc: 'Default' },
                                        { value: 'fast', label: 'Fast', desc: 'Better' },
                                        { value: 'medium', label: 'Medium', desc: 'Best video' },
                                    ].map((m) => (
                                        <button
                                            type="button"
                                            key={m.value}
                                            onClick={() => update({ encode_preset: m.value })}
                                            className={`
                                                px-2 py-2 rounded-lg text-xs text-center transition-all border
                                                ${settings.encode_preset === m.value
                                                    ? 'bg-primary/20 border-primary text-primary-light'
                                                    : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                            `}
                                        >
                                            <div className="font-medium">{m.label}</div>
                                            <div className="text-[10px] opacity-70 mt-0.5">{m.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Fast Assemble */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Fast Assemble</p>
                                    <p className="text-xs text-text-muted">In-memory audio (instant). Off = ffmpeg mixing (slower, preserves overlapping audio)</p>
                                </div>
                                <button
                                    type="button" title="Toggle Fast Assemble" onClick={() => update({ fast_assemble: !settings.fast_assemble })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.fast_assemble ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.fast_assemble ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* Manual Review Queue */}
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-text-primary">Manual Review Queue</p>
                                    <p className="text-xs text-text-muted">Save segments that failed QC after all retries to manual_review_queue.json for inspection</p>
                                </div>
                                <button
                                    type="button" title="Toggle Manual Review Queue" onClick={() => update({ enable_manual_review: !settings.enable_manual_review })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.enable_manual_review ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.enable_manual_review ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>

                            {/* Step-by-Step Review — disabled when YT Translate or New pipeline */}
                            <div className={`flex items-center justify-between ${(ytTranslateOn || isNew || isOneFlow || isSrtMode) ? 'opacity-40 pointer-events-none' : ''}`}>
                                <div>
                                    <p className="text-sm text-text-primary">Step-by-Step Review</p>
                                    <p className="text-xs text-text-muted">
                                        Pause after transcription & translation to review output before continuing
                                        {ytTranslateOn && <span className="text-yellow-400 ml-1">— off: YT Translate skips these steps</span>}
                                    </p>
                                </div>
                                <button
                                    type="button" title="Toggle Step-by-Step Review" onClick={() => update({ step_by_step: !settings.step_by_step })}
                                    className={`
                                        w-11 h-6 rounded-full transition-colors relative
                                        ${settings.step_by_step ? 'bg-primary' : 'bg-white/10'}
                                    `}
                                >
                                    <div className={`
                                        w-4 h-4 rounded-full bg-white absolute top-1 transition-transform
                                        ${settings.step_by_step ? 'translate-x-6' : 'translate-x-1'}
                                    `} />
                                </button>
                            </div>
                        </div>

                        {/* Dub Duration Limit */}
                        <div>
                            <p className="text-xs text-text-muted mb-1.5">Dub Duration — only dub the first N minutes of the video. Useful for long videos when you only need a portion.</p>
                            <div className="grid grid-cols-5 gap-2">
                                {[
                                    { value: 0, label: 'Full', desc: 'Entire video' },
                                    { value: 30, label: '30 min', desc: 'First 30m' },
                                    { value: 60, label: '1 hr', desc: 'First 1h' },
                                    { value: 120, label: '2 hr', desc: 'First 2h' },
                                    { value: 180, label: '3 hr', desc: 'First 3h' },
                                ].map((m) => (
                                    <button
                                        key={m.value}
                                        onClick={() => update({ dub_duration: m.value })}
                                        className={`
                                            px-3 py-2 rounded-lg text-xs text-center transition-all border
                                            ${settings.dub_duration === m.value
                                                ? 'bg-primary/20 border-primary text-primary-light'
                                                : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                        `}
                                    >
                                        <div className="font-medium">{m.label}</div>
                                        <div className="text-[10px] opacity-70 mt-0.5">{m.desc}</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Split Long Videos */}
                        <div>
                            <p className="text-xs text-text-muted mb-1.5">Split Long Videos — breaks video into parts, dubs each separately. Avoids timeout/crashes on 1h+ videos.</p>
                            <div className="grid grid-cols-4 gap-2">
                                {[
                                    { value: 0, label: 'Off', desc: 'No splitting' },
                                    { value: 30, label: '30 min', desc: 'Split every 30m' },
                                    { value: 40, label: '40 min', desc: 'Split every 40m' },
                                    { value: 60, label: '60 min', desc: 'Split every 1h' },
                                ].map((m) => (
                                    <button
                                        key={m.value}
                                        onClick={() => update({ split_duration: m.value })}
                                        className={`
                                            px-3 py-2 rounded-lg text-xs text-center transition-all border
                                            ${settings.split_duration === m.value
                                                ? 'bg-primary/20 border-primary text-primary-light'
                                                : 'bg-white/5 border-white/10 text-text-muted hover:bg-white/10'}
                                        `}
                                    >
                                        <div className="font-medium">{m.label}</div>
                                        <div className="text-[10px] opacity-70 mt-0.5">{m.desc}</div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>);
            })()}
        </div>
    );
}
