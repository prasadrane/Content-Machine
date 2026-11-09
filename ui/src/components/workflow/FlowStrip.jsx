const STEPS = [
  ['Idea', 'Capture the engineering idea and who it is for.'],
  ['Draft & review', 'Shape a draft and check it before it moves on.'],
  ['Approve', 'You decide when a draft is ready.'],
  ['Export', 'Copy it out for your chosen platform.'],
]

/** Four-step overview. `compact` hides descriptions for the signed-in home. */
export default function FlowStrip({ compact = false, label = 'How Content Machine works' }) {
  return <ol className={`cm-flow${compact ? ' cm-flow-compact' : ''}`} aria-label={label}>
    {STEPS.map(([name, text], index) => <li key={name} className="cm-flow-step">
      <span className="cm-flow-num" aria-hidden="true">{index + 1}</span>
      <span className="cm-flow-name">{name}</span>
      {!compact && <span className="cm-muted cm-flow-text">{text}</span>}
    </li>)}
  </ol>
}
