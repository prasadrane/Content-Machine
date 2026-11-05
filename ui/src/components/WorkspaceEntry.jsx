export default function WorkspaceEntry({ onNavigate, onSample }) {
  const secondary = 'cm-button cm-button-secondary'
  return (
    <section aria-label="Start or continue your story" className="cm-panel space-y-4 mb-6">
      <div>
        <h1 className="cm-page-title">Your experience. A clearer story.</h1>
        <p className="cm-page-description max-w-3xl">Turn engineering sources and your experience into reviewed drafts and channel formats. You decide what is accurate and what to approve.</p>
      </div>
      <div className="cm-page-actions">
        <button type="button" onClick={() => onNavigate('council')} className={secondary}>Review a draft</button>
        <button type="button" onClick={() => onNavigate('distribute')} className={secondary}>Adapt an anchor</button>
        {onSample && <button type="button" onClick={onSample} className={secondary}>Explore a completed example</button>}
      </div>
      <p className="cm-muted">Your signal intake, Council draft and channel formats stay available during this session. Refresh and restart recovery are not guaranteed.</p>
    </section>
  )
}
