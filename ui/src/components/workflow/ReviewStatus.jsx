export default function ReviewStatus({ flow }) {
  if (!flow.review) return <p className="cm-muted">AI review is optional.</p>
  const verified = flow.reviewBinding?.verified && !flow.dirty &&
    flow.reviewBinding.revision === flow.item.working_revision
  if (flow.review.state === 'skipped' && verified) return <p className="cm-muted">Review skipped for this saved version.</p>
  if (flow.reviewIsCurrent) return <div className="cm-status cm-status-info space-y-2">
    <p>Review completed for this saved version.</p>
    {Object.entries(flow.review.actions || {}).map(([name, advice]) =>
      <p key={name}>{name} — {typeof advice === 'string' ? advice : JSON.stringify(advice)}</p>)}
  </div>
  if (flow.review.state === 'failed') return <p className="cm-muted">The last AI review failed. Your draft is still available.</p>
  if (flow.review.state === 'pending') return <p className="cm-muted">AI review is pending.</p>
  return <p className="cm-muted">A previous review is saved in history. It is not verified for your current draft.</p>
}
