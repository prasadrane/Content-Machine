import { useEffect, useState } from 'react'
import * as api from '../../api/workflow'
import { isClean, snapshotMatchesItem } from './workflowState'

const blank = { operation: null, pending: null, proposal: null, activities: null, loading: false, loadError: '' }

export function useWorkflowAI({ item, pairs, capabilitiesError, itemRef, draftRef, execute, persist, keyFor,
  pendingKeys, updateDraft, acknowledge, setApproval, setExported, setReview,
  setReviewBinding, setStage, setNotice }) {
  const [ai, setAI] = useState(blank)
  const pair = pairs.find(entry => entry.destination === item?.destination && entry.format === item?.format)
  const ready = Boolean(!capabilitiesError && (pair?.can_generate || pair?.can_review))
  useEffect(() => {
    let active = true
    setAI(blank)
    if (!item?.item_id || !ready) return () => { active = false }
    const id = item.item_id
    setAI({ ...blank, loading: true })
    api.getOperations(id).then(result => {
      if (!active) return
      const activities = result.operations.filter(entry => entry.item_id === id)
      const pending = activities.find(entry => entry.state === 'pending') || null
      setAI({ ...blank, activities, operation: pending, pending })
    }).catch(error => {
      if (active) setAI({ ...blank, loadError: error.message || 'Could not load AI activity.' })
    })
    return () => { active = false }
  }, [item?.item_id, ready])

  function matchesCurrent(operation) {
    const current = itemRef.current
    const snapshot = operation?.editorial_snapshot
    return Boolean(current && snapshot && operation.item_id === current.item_id &&
      operation.input_version_id === snapshot.version_id &&
      snapshotMatchesItem(snapshot, current) &&
      isClean(current, draftRef.current))
  }
  function display(operation) {
    const proposal = operation.kind === 'generate' && operation.state === 'completed' &&
      operation.result?.input_version_id === operation.input_version_id &&
      Array.isArray(operation.result?.artifact?.segments) ? operation : null
    setAI(previous => ({ ...previous, operation, proposal,
      pending: operation.state === 'pending' ? operation :
        previous.pending?.operation_id === operation.operation_id ? null : previous.pending,
      activities: previous.activities?.map(entry => entry.operation_id === operation.operation_id ? operation : entry),
    }))
    if (operation.kind === 'review' && operation.state === 'completed') {
      const review = operation.result?.review
      if (!review || review.item_id !== operation.item_id || review.input_version_id !== operation.input_version_id) return
      setReview(review)
      setReviewBinding({ itemId: operation.item_id, revision: operation.editorial_snapshot?.revision,
        versionId: operation.input_version_id, verified: matchesCurrent(operation), snapshot: operation.editorial_snapshot })
    }
  }
  const start = kind => execute(async valid => {
    if (ai.loading || ai.loadError) throw new Error('Load AI activity before starting another request.')
    if (ai.pending?.state === 'pending') throw new Error('Check the pending AI request before starting another.')
    const current = isClean(itemRef.current, draftRef.current)
      ? itemRef.current : await persist(null, valid)
    if (!valid()) return
    if (!isClean(current, draftRef.current)) throw new Error('Save your latest changes before continuing.')
    const body = { expected_revision: current.working_revision }
    const request = keyFor(kind, current.item_id, body)
    let result
    try {
      result = await (kind === 'generate' ? api.generateDraft : api.reviewDraft)(current.item_id, body, request.key)
    } catch (failure) {
      const failed = failure.body?.operation
      if (valid() && failed?.item_id === current.item_id && failed.state === 'failed') {
        pendingKeys.current.delete(request.signature)
        display(failed)
      }
      throw failure
    }
    pendingKeys.current.delete(request.signature)
    if (!valid() || itemRef.current?.item_id !== current.item_id) return
    if (result.operation?.item_id !== current.item_id || result.operation?.kind !== kind ||
        result.operation?.editorial_snapshot?.revision !== current.working_revision ||
        result.operation?.input_version_id !== result.operation?.editorial_snapshot?.version_id) {
      throw new Error('The AI response did not match the requested saved version.')
    }
    display(result.operation)
  })
  const checkAIStatus = () => execute(async valid => {
    const operation = ai.pending
    if (!operation || itemRef.current?.item_id !== operation.item_id) return
    const result = await api.getOperation(operation.item_id, operation.operation_id)
    if (valid() && itemRef.current?.item_id === operation.item_id &&
        result.operation?.operation_id === operation.operation_id && result.operation?.item_id === operation.item_id) {
      display(result.operation)
    }
  })
  const loadAIActivity = () => execute(async valid => {
    const id = itemRef.current.item_id
    const result = await api.getOperations(id)
    if (valid() && itemRef.current?.item_id === id) {
      const activities = result.operations.filter(entry => entry.item_id === id)
      const pending = activities.find(entry => entry.state === 'pending') || null
      setAI(previous => ({ ...previous, activities, pending, operation: pending || previous.operation, loadError: '' }))
    }
  })
  const abandonAI = () => execute(async valid => {
    const operation = ai.pending
    if (!operation || itemRef.current?.item_id !== operation.item_id) return
    const result = await api.abandonOperation(operation.item_id, operation.operation_id)
    if (valid() && itemRef.current?.item_id === operation.item_id && result.operation?.operation_id === operation.operation_id) {
      display(result.operation)
      setNotice(result.operation.state === 'completed'
        ? 'The request already completed. Review its result before continuing.'
        : result.operation.error?.code === 'operation_abandoned'
          ? 'Request closed. You may start a new request; the earlier provider call may still finish.'
          : 'The request has finished. Check its status before continuing.')
    }
  })
  const showAIActivity = operation => {
    if (operation.item_id === itemRef.current?.item_id) display(operation)
  }
  const acceptArtifact = (operation, artifact) => execute(async valid => {
    if (!matchesCurrent(operation)) throw new Error('This suggestion is for an earlier saved version. Your draft was preserved.')
    if (!artifact?.segments?.length || artifact.segments.some(text => typeof text !== 'string' || !text.trim())) {
      throw new Error('This suggestion does not contain a valid draft.')
    }
    const current = itemRef.current
    const original = JSON.stringify(draftRef.current)
    const body = { expected_revision: current.working_revision, context: draftRef.current.context, artifact,
      stage: 'draft_review' }
    const request = keyFor('accept-ai', current.item_id, body)
    const result = await api.saveItem(current.item_id, body, request.key)
    pendingKeys.current.delete(request.signature)
    if (!valid() || itemRef.current?.item_id !== current.item_id) return
    acknowledge(result.item)
    setApproval(null)
    setExported(null)
    setStage('draft_review')
    if (JSON.stringify(draftRef.current) === original) {
      updateDraft({ context: result.item.context, artifact: result.item.artifact })
      setNotice('Suggestion saved as a new draft. Review it before approval.')
    } else {
      setNotice('Suggestion saved. Your newer changes are still unsaved.')
    }
    setAI(previous => ({ ...previous, proposal: null }))
  })
  const acceptProposal = () => acceptArtifact(ai.proposal, ai.proposal?.result?.artifact)
  const acceptReviewProposal = suggestion => {
    const operation = ai.operation
    const segments = itemRef.current?.artifact?.segments
    if (!matchesCurrent(operation) || !Array.isArray(segments) ||
        !Number.isInteger(suggestion.segment) || segments[suggestion.segment] !== suggestion.current) {
      return execute(async () => { throw new Error('This suggestion is for an earlier saved version. Your draft was preserved.') })
    }
    const revised = [...segments]
    revised[suggestion.segment] = suggestion.proposed
    return acceptArtifact(operation, { segments: revised })
  }
  return {
    ai, generateDraft: () => start('generate'), requestReview: () => start('review'),
    checkAIStatus, abandonAI, loadAIActivity, showAIActivity, acceptProposal, acceptReviewProposal,
    cancelProposal: () => setAI(previous => ({ ...previous, proposal: null })),
    aiIsCurrent: matchesCurrent(ai.operation),
  }
}
