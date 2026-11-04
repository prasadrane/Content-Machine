import { useEffect, useState } from 'react';
import { fetchJson } from '../api/client.js';

// Ideal workflow, in order. `tab` is where the step happens.
export const DEMO_STEPS = [
  { id: 'pick', tab: 'oracle', title: 'Pick a signal', hint: 'The Oracle scores feed items; open one that passed.' },
  { id: 'review', tab: 'council', title: 'Council review', hint: 'Four judges score the draft against the frozen rubric.' },
  { id: 'approve', tab: 'council', title: 'You approve', hint: 'Read the verdict, then approve the exact text. Nothing moves on without this.' },
  { id: 'distribute', tab: 'distribute', title: 'Distribute', hint: 'Channel formats are generated only for approved text.' },
  { id: 'lessons', tab: 'lessons', title: 'Teach the system', hint: 'Diff your edits; proposed rules wait for your approval.' },
];

export function currentStepId(activeTab, approved) {
  if (activeTab === 'oracle') return 'pick';
  if (activeTab === 'council') return approved ? 'approve' : 'review';
  if (activeTab === 'distribute') return 'distribute';
  if (activeTab === 'lessons') return 'lessons';
  return null;
}

export default function DemoBanner({ activeTab, approved = false, onStart, onGoto }) {
  const [demo, setDemo] = useState(false);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchJson('/api/meta')
      .then((m) => alive && setDemo(Boolean(m && m.demo_mode)))
      .catch(() => alive && setDemo(false));
    return () => { alive = false; };
  }, []);

  if (!demo) return null;

  const start = async () => {
    setStarting(true);
    setStartError('');
    try {
      await onStart();
    } catch (e) {
      setStartError(e?.message || 'Could not load the sample draft.');
    } finally {
      setStarting(false);
    }
  };

  const current = currentStepId(activeTab, approved);

  return (
    <>
      <div className="bg-[#f0eee6] border-b border-[#e3dacc] px-4 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-3 text-sm">
          <p role="status" className="text-[#58574f]">Public demo · Explore the workflow with illustrative sample data.</p>
          {onStart && <button type="button" onClick={start} disabled={starting} className="min-h-10 px-4 py-2 rounded-full bg-[#141413] text-[#faf9f5] disabled:opacity-50">{starting ? 'Loading...' : 'Explore a completed example'}</button>}
          <details className="text-[#58574f]">
            <summary className="cursor-pointer min-h-10 flex items-center">Demo limits</summary>
            <p className="max-w-2xl py-2">Runs on free-tier Gemini quota. Generation may fail or stop. When quota runs out, stored samples may be replayed; they are labeled and are not generated from your custom text. Demo data is temporary.</p>
          </details>
          {onGoto && <button type="button" aria-expanded={showGuide} aria-controls="demo-workflow" onClick={() => setShowGuide(v => !v)} className="min-h-10 px-3 py-2 rounded-lg border border-[#b0aea5]">{showGuide ? 'Hide workflow guide' : 'Show workflow guide'}</button>}
          {startError && <p role="alert" className="text-rose-800">{startError}</p>}
        </div>
      </div>
      {showGuide && onGoto && (
        <nav id="demo-workflow" aria-label="Demo workflow" className="bg-[#f0eee6] border-b border-[#e3dacc] px-6 py-2">
          <div className="max-w-7xl mx-auto flex items-center gap-3 flex-wrap text-xs font-mono">
            <ol className="flex items-center gap-2 flex-wrap">
              {DEMO_STEPS.map((s, i) => (
                <li key={s.id}>
                  <button
                    type="button"
                    title={s.hint}
                    aria-current={current === s.id ? 'step' : undefined}
                    onClick={() => onGoto && onGoto(s.tab)}
                    className={`px-2.5 py-1 rounded-full border ${
                      current === s.id
                        ? 'bg-[#c6613f] text-[#faf9f5] border-[#c6613f]'
                        : 'bg-[#faf9f5] text-[#87867f] border-[#e3dacc] hover:text-[#141413]'
                    }`}
                  >
                    {i + 1}. {s.title}
                  </button>
                </li>
              ))}
            </ol>
            {current && (
              <span className="text-[#87867f]">{DEMO_STEPS.find((s) => s.id === current).hint}</span>
            )}
          </div>
        </nav>
      )}
    </>
  );
}
