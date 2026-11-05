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
      <div className="cm-banner">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-3 text-sm">
          <p role="status" className="cm-muted">Public demo · Explore the workflow with illustrative sample data.</p>
          {onStart && <button type="button" onClick={start} disabled={starting} className="cm-button cm-button-primary">{starting ? 'Loading...' : 'Explore a completed example'}</button>}
          <details className="cm-muted">
            <summary className="cm-button cm-button-quiet cursor-pointer">Demo limits</summary>
            <p className="cm-prose max-w-2xl py-2">Runs on free-tier Gemini quota. Generation may fail or stop. When quota runs out, stored samples may be replayed; they are labeled and are not generated from your custom text. Demo data is temporary.</p>
          </details>
          {onGoto && <button type="button" aria-expanded={showGuide} aria-controls="demo-workflow" onClick={() => setShowGuide(v => !v)} className="cm-button cm-button-secondary">{showGuide ? 'Hide workflow guide' : 'Show workflow guide'}</button>}
          {startError && <p role="alert" className="cm-status cm-status-error">{startError}</p>}
        </div>
      </div>
      {showGuide && onGoto && (
        <nav id="demo-workflow" aria-label="Demo workflow" className="cm-banner">
          <div className="max-w-7xl mx-auto flex items-center gap-3 flex-wrap">
            <ol className="flex items-center gap-2 flex-wrap">
              {DEMO_STEPS.map((s, i) => (
                <li key={s.id}>
                  <button
                    type="button"
                    title={s.hint}
                    aria-current={current === s.id ? 'step' : undefined}
                    onClick={() => onGoto && onGoto(s.tab)}
                    className={`cm-chip ${current === s.id ? 'cm-chip-active' : ''}`}
                  >
                    {i + 1}. {s.title}
                  </button>
                </li>
              ))}
            </ol>
            {current && (
              <span className="cm-muted">{DEMO_STEPS.find((s) => s.id === current).hint}</span>
            )}
          </div>
        </nav>
      )}
    </>
  );
}
