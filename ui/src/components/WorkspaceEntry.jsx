export default function WorkspaceEntry({ onNavigate, onSample }) {
  const secondary = 'min-h-10 px-4 py-2 rounded-full border border-[#b0aea5] text-sm font-medium hover:bg-[#f0eee6]'
  return (
    <section aria-label="Start or continue your story" className="mb-8 pb-6 border-b border-[#e3dacc] space-y-4">
      <div>
        <h1 className="font-serif text-3xl text-[#141413]">Your experience. A clearer story.</h1>
        <p className="mt-2 text-base leading-relaxed text-[#58574f] max-w-3xl">Turn engineering sources and your experience into reviewed drafts and channel formats. You decide what is accurate and what to approve.</p>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => onNavigate('council')} className={secondary}>Review a draft</button>
        <button type="button" onClick={() => onNavigate('distribute')} className={secondary}>Adapt an anchor</button>
        {onSample && <button type="button" onClick={onSample} className={secondary}>Explore a completed example</button>}
      </div>
      <p className="text-sm text-[#58574f]">Return to any view to continue your work during this session. Refresh and restart recovery are not guaranteed.</p>
    </section>
  )
}
