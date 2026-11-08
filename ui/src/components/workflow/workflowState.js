export function requestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  if (!globalThis.crypto?.getRandomValues) throw new Error('This browser cannot create a request ID.')
  return Array.from(globalThis.crypto.getRandomValues(new Uint8Array(16)),
    byte => byte.toString(16).padStart(2, '0')).join('')
}

export function isClean(item, draft) {
  return Boolean(item && draft) &&
    JSON.stringify(item.context) === JSON.stringify(draft.context) &&
    JSON.stringify(item.artifact) === JSON.stringify(draft.artifact)
}

export function snapshotMatchesItem(snapshot, item) {
  if (!snapshot || !item || snapshot.title !== item.title || snapshot.revision !== item.working_revision ||
      snapshot.item_id !== item.item_id || snapshot.destination !== item.destination || snapshot.format !== item.format) return false
  const contextValue = context => context && [context.notes, context.experience, context.interpretation,
    context.preference_snapshot_id, context.sources?.map(source => [source.source_id, source.url, source.title, source.excerpt, source.fetched_at])]
  return JSON.stringify(contextValue(snapshot.context)) === JSON.stringify(contextValue(item.context)) &&
    JSON.stringify(snapshot.artifact?.segments) === JSON.stringify(item.artifact?.segments)
}

export function reviewMatches(review, binding, item) {
  return Boolean(review && binding && item && review.state === 'completed' &&
    binding.itemId === item.item_id && binding.revision === item.working_revision &&
    binding.versionId === review.input_version_id && binding.verified && snapshotMatchesItem(binding.snapshot, item))
}

export function draftOf(item) {
  return { context: item.context, artifact: item.artifact }
}

export function approvalMatchesItem(result, item, digest) {
  const saved = result?.item
  const approval = result?.approval
  return Boolean(saved && approval && approval.approval_id && approval.version_id &&
    saved.item_id === item.item_id && saved.owner_id === item.owner_id &&
    saved.working_revision === item.working_revision && saved.destination === item.destination &&
    saved.format === item.format && isClean(saved, draftOf(item)) &&
    saved.active_approval_id === approval.approval_id && approval.item_id === item.item_id &&
    approval.owner_id === item.owner_id && approval.destination === item.destination &&
    approval.format === item.format && approval.artifact_digest === digest)
}
