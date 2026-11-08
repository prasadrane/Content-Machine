import { useEffect, useRef, useState } from 'react'
import * as api from '../../api/workflow'
import { artifactDigest } from './workflowUtils'
import { approvalMatchesItem, draftOf, isClean, requestId, reviewMatches, snapshotMatchesItem } from './workflowState'
import { useWorkflowLibrary } from './workflowLibrary'
import { useWorkflowAI } from './useWorkflowAI'

export function useWorkflow() {
  const [item, setItem] = useState(null)
  const [draft, setDraft] = useState(null)
  const [review, setReview] = useState(null)
  const [approval, setApproval] = useState(null)
  const [exported, setExported] = useState(null)
  const [screen, setScreen] = useState('list')
  const [stage, setStage] = useState('idea')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(null)
  const [reviewBinding, setReviewBinding] = useState(null)
  const [notice, setNotice] = useState('')
  const [history, setHistory] = useState(null)
  const library = useWorkflowLibrary(setError)
  const busyRef = useRef(false)
  const generation = useRef(0)
  const mounted = useRef(true)
  const pendingKeys = useRef(new Map())
  const itemRef = useRef(item)
  const draftRef = useRef(draft)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      generation.current += 1
    }
  }, [])

  const keyFor = (operation, id, body) => {
    const signature = JSON.stringify([operation, id, body])
    if (!pendingKeys.current.has(signature)) pendingKeys.current.set(signature, requestId())
    return { signature, key: pendingKeys.current.get(signature) }
  }
  const updateDraft = updater => {
    draftRef.current = typeof updater === 'function' ? updater(draftRef.current) : updater
    setDraft(draftRef.current)
    setNotice('')
  }
  const acknowledge = next => {
    itemRef.current = next
    setItem(next)
  }
  const applyItem = (next, nextReview = null, nextApproval = null) => {
    acknowledge(next)
    updateDraft(draftOf(next))
    setStage(next.stage)
    setReview(nextReview)
    setApproval(nextApproval)
    setReviewBinding(null)
    setConflict(null)
    setExported(null)
    setHistory(null)
    setScreen('item')
  }
  const execute = async operation => {
    if (busyRef.current || !mounted.current) return
    busyRef.current = true
    setBusy(true)
    setError('')
    setNotice('')
    setConflict(null)
    const current = generation.current
    try {
      await operation(() => mounted.current && current === generation.current)
    } catch (failure) {
      if (!mounted.current || current !== generation.current) return
      setError(failure.message || 'The request could not be completed.')
      setConflict(failure.status === 409 ? failure.body : null)
    } finally {
      busyRef.current = false
      if (mounted.current) setBusy(false)
    }
  }

  const open = id => execute(async valid => {
    const result = await api.getItem(id)
    if (!valid()) return
    applyItem(result.item, result.review, result.approval)
    if (result.review) {
      let snapshot = null
      let verified = false
      try {
        if (result.review.state === 'skipped') {
          const owned = await api.getHistory(id)
          verified = owned.versions.some(version => version.version_id === result.review.input_version_id &&
            version.revision === result.item.working_revision)
        } else {
          const activity = await api.getOperations(id)
          const operation = activity.operations.find(entry => entry.kind === 'review' && entry.state === 'completed' &&
            entry.result?.review?.review_id === result.review.review_id && entry.input_version_id === result.review.input_version_id)
          snapshot = operation?.editorial_snapshot
          verified = snapshotMatchesItem(snapshot, result.item)
        }
      } catch { /* Unverified history cannot establish a current review. */ }
      if (!valid()) return
      setReviewBinding({ itemId: id, revision: result.item.working_revision,
        versionId: result.review.input_version_id, verified, snapshot })
    }
    if (result.item.active_approval_id && result.approval?.approval_id === result.item.active_approval_id) {
      const output = await api.getExport(id, result.approval.version_id)
      if (valid()) setExported(output)
    }
  })
  const create = (title, pair) => execute(async valid => {
    const body = { title, destination: pair.destination, format: pair.format }
    const request = keyFor('create', '', body)
    const result = await api.createItem(body, request.key)
    pendingKeys.current.delete(request.signature)
    if (valid()) applyItem(result.item)
  })

  // Capture the exact sent draft. An older save must leave newer edits intact.
  const persist = async (targetStage, valid) => {
    const source = itemRef.current
    const sent = draftRef.current
    const body = { expected_revision: source.working_revision, ...sent }
    if (targetStage) body.stage = targetStage
    const request = keyFor('save', source.item_id, body)
    const result = await api.saveItem(source.item_id, body, request.key)
    pendingKeys.current.delete(request.signature)
    if (!valid() || itemRef.current?.item_id !== source.item_id) return result.item
    acknowledge(result.item)
    if (JSON.stringify(draftRef.current) === JSON.stringify(sent)) updateDraft(draftOf(result.item))
    if (targetStage && isClean(result.item, draftRef.current)) setStage(targetStage)
    if (!result.item.active_approval_id) {
      setApproval(null)
      setExported(null)
    }
    return result.item
  }
  const save = () => execute(async valid => {
    const saved = await persist(null, valid)
    if (valid() && isClean(saved, draftRef.current)) setNotice('Saved')
  })
  const continueToDraft = () => execute(async valid => {
    const saved = await persist('draft_review', valid)
    if (valid() && isClean(saved, draftRef.current)) setNotice('Saved')
  })
  const skip = () => execute(async valid => {
    const current = isClean(itemRef.current, draftRef.current)
      ? itemRef.current : await persist(null, valid)
    if (!valid()) return
    if (!isClean(current, draftRef.current)) throw new Error('Save your latest changes before continuing.')
    const body = { expected_revision: current.working_revision }
    const request = keyFor('skip-review', current.item_id, body)
    const result = await api.skipReview(current.item_id, body, request.key)
    pendingKeys.current.delete(request.signature)
    if (!valid()) return
    acknowledge(result.item)
    setReview(result.review)
    setReviewBinding({ itemId: current.item_id, revision: current.working_revision,
      versionId: result.review?.input_version_id, verified: true })
    setStage(isClean(result.item, draftRef.current) ? 'approve' : 'draft_review')
  })
  const approve = () => execute(async valid => {
    const current = itemRef.current
    if (!isClean(current, draftRef.current)) throw new Error('Save your changes before approving.')
    const digest = await artifactDigest(current)
    if (!valid()) return
    if (!isClean(current, draftRef.current)) throw new Error('Save your changes before approving.')
    const body = { expected_revision: current.working_revision, artifact_digest: digest, consent: true }
    const request = keyFor('approve', current.item_id, body)
    const result = await api.approveItem(current.item_id, body, request.key)
    if (!valid()) return
    if (!approvalMatchesItem(result, current, digest)) {
      throw new Error('The approval response did not match this saved version. Your draft is preserved; retry approval.')
    }
    pendingKeys.current.delete(request.signature)
    acknowledge(result.item)
    setApproval(result.approval)
    if (!isClean(result.item, draftRef.current)) {
      setStage('draft_review')
      return
    }
    setStage('export')
    const output = await api.getExport(current.item_id, result.approval.version_id)
    if (valid()) setExported(output)
  })
  const loadExport = () => execute(async valid => {
    const current = itemRef.current
    if (!isClean(current, draftRef.current) || !approval || approval.approval_id !== current.active_approval_id) {
      throw new Error('Approve this saved version before exporting.')
    }
    const output = await api.getExport(current.item_id, approval.version_id)
    if (valid()) setExported(output)
  })
  const loadHistory = () => execute(async valid => {
    const result = await api.getHistory(itemRef.current.item_id)
    if (valid()) setHistory(result)
  })
  const restore = versionId => execute(async valid => {
    const current = itemRef.current
    const originalDraft = JSON.stringify(draftRef.current)
    if (!isClean(current, draftRef.current)) throw new Error('Save your changes before restoring a version.')
    const body = { expected_revision: current.working_revision, version_id: versionId }
    const request = keyFor('restore', current.item_id, body)
    const result = await api.restoreVersion(current.item_id, body, request.key)
    pendingKeys.current.delete(request.signature)
    if (!valid() || itemRef.current?.item_id !== current.item_id) return
    if (JSON.stringify(draftRef.current) === originalDraft) {
      applyItem(result.item)
      setNotice('Version restored as a new draft. Review and approve it before export.')
      return
    }
    acknowledge(result.item)
    setReview(null)
    setReviewBinding(null)
    setApproval(null)
    setExported(null)
    setHistory(null)
    setStage('draft_review')
    setNotice('Version restored. Your newer edits are still unsaved.')
  })
  const adapt = pair => execute(async valid => {
    const current = itemRef.current
    if (!isClean(current, draftRef.current) || !approval || approval.approval_id !== current.active_approval_id) {
      throw new Error('Approve this saved version before creating an adaptation.')
    }
    const body = { source_version_id: approval.version_id, destination: pair.destination, format: pair.format }
    const request = keyFor('adapt', current.item_id, body)
    const result = await api.adaptVersion(current.item_id, body, request.key)
    pendingKeys.current.delete(request.signature)
    if (valid()) applyItem(result.item)
  })
  const dirty = Boolean(item && draft) && !isClean(item, draft)
  const discard = () => {
    if (busyRef.current || !itemRef.current) return
    if (conflict) return open(itemRef.current.item_id)
    updateDraft(draftOf(itemRef.current))
    setStage(itemRef.current.stage)
    setError('')
    setNotice('Unsaved changes discarded')
  }
  const showList = () => {
    if (!isClean(itemRef.current, draftRef.current) || busyRef.current) return
    generation.current += 1
    acknowledge(null)
    updateDraft(null)
    setReviewBinding(null)
    setConflict(null)
    setScreen('list')
    library.refresh()
  }
  const aiActions = useWorkflowAI({ item, pairs: library.pairs, capabilitiesError: library.capabilitiesError,
    itemRef, draftRef, execute, persist, keyFor,
    pendingKeys, updateDraft, acknowledge, setApproval, setExported, setReview,
    setReviewBinding, setStage, setNotice })
  return {
    ...library, item, draft, review, approval, exported, screen, stage, busy,
    error, conflict, reviewBinding, notice, history, dirty,
    reviewIsCurrent: reviewMatches(review, reviewBinding, item) && !dirty,
    generation, itemRef, setScreen, setStage, updateDraft, setError, setNotice,
    open, create, save, discard, continueToDraft, skip, approve, loadExport, loadHistory, restore,
    closeHistory: () => setHistory(null), adapt, showList,
    ...aiActions,
  }
}

