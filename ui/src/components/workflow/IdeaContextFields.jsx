import WorkflowTextField from './WorkflowTextField'

export default function IdeaContextFields({ flow, isActive }) {
  const update = field => value => flow.updateDraft(previous => ({
    ...previous, context: { ...previous.context,
      [field]: typeof value === 'function' ? value(previous.context[field] || '') : value },
  }))
  return <div className="space-y-5">
    <WorkflowTextField label="Your notes" value={flow.draft.context.notes || ''}
      onChange={update('notes')} enabled={isActive && !flow.busy} />
    {(flow.draft.context.sources || []).length > 0 && <div className="cm-subpanel space-y-3">
      <h3 className="cm-panel-title">Sources for this idea</h3>
      {flow.draft.context.sources.map((entry, index) => <div key={`${entry.source_id}-${entry.url}-${index}`}
        className="flex flex-wrap items-center justify-between gap-2">
        <span className="cm-prose break-words">{entry.title}</span>
        <button className="cm-button cm-button-quiet" disabled={flow.busy}
          aria-label={`Remove ${entry.title}`} onClick={() => flow.updateDraft(previous => ({
            ...previous, context: { ...previous.context,
              sources: previous.context.sources.filter((_, position) => position !== index) },
          }))}>Remove</button>
      </div>)}
    </div>}
    <details className="cm-subpanel space-y-4">
      <summary className="cursor-pointer font-medium">Add your experience and perspective</summary>
      <WorkflowTextField label="Your experience" value={flow.draft.context.experience || ''}
        onChange={update('experience')} enabled={isActive && !flow.busy} />
      <WorkflowTextField label="Your interpretation" value={flow.draft.context.interpretation || ''}
        onChange={update('interpretation')} enabled={isActive && !flow.busy} />
    </details>
  </div>
}
