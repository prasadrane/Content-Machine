import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useWorkflow } from './useWorkflow'
import * as api from '../../api/workflow'

vi.mock('../../api/workflow', () => ({
  getCapabilities: vi.fn(), getItems: vi.fn(), getItem: vi.fn(), getHistory: vi.fn(),
  createItem: vi.fn(), saveItem: vi.fn(), skipReview: vi.fn(), approveItem: vi.fn(),
  getExport: vi.fn(), adaptVersion: vi.fn(), restoreVersion: vi.fn(),
  generateDraft: vi.fn(), reviewDraft: vi.fn(), getOperation: vi.fn(), getOperations: vi.fn(), abandonOperation: vi.fn(),
}))

const item = { item_id: 'one', owner_id: 'owner', title: 'Indexes', destination: 'linkedin',
  format: 'linkedin_post', stage: 'draft_review', working_revision: 2,
  context: { notes: 'source notes', sources: [], experience: null, interpretation: null, preference_snapshot_id: null },
  artifact: { segments: ['Exact old text'] },
  active_approval_id: 'approval-old' }
const proposal = { operation_id: 'op-1', item_id: 'one', kind: 'generate', state: 'completed',
  input_version_id: 'v2', editorial_snapshot: { item_id: 'one', version_id: 'v2', revision: 2, title: 'Indexes',
    destination: 'linkedin', format: 'linkedin_post',
    context: { experience: null, interpretation: null, notes: 'source notes', preference_snapshot_id: null, sources: [] },
    artifact: item.artifact },
  result: { input_version_id: 'v2', artifact: { segments: ['  Proposed text\n'] } } }
const review = { review_id: 'r1', item_id: 'one', state: 'completed', input_version_id: 'v2',
  actions: { required_actions: ['Explain the tradeoff'], notes: {} }, proposals: [] }
const reviewed = { ...proposal, operation_id: 'op-r', kind: 'review', result: { review } }
const edit = (result, text) => act(() => result.current.updateDraft(previous => ({
  ...previous, artifact: { segments: [text] },
})))
async function open(result) {
  await act(async () => { await result.current.open('one') })
  await waitFor(() => expect(api.getOperations).toHaveBeenCalled())
  await waitFor(() => expect(result.current.ai.loading).toBe(false))
}
function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  api.getItems.mockResolvedValue({ items: [item] })
  api.getCapabilities.mockResolvedValue({ pairs: [{ destination: 'linkedin', format: 'linkedin_post',
    can_edit: true, can_generate: true, can_review: true }] })
  api.getItem.mockResolvedValue({ item, review: null, approval: null })
  api.getOperations.mockResolvedValue({ operations: [] })
})

describe('AI operations on a saved draft', () => {
  it('discards a proposal without saving or changing current text', async () => {
    api.generateDraft.mockResolvedValue({ operation: proposal })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.generateDraft() })
    act(() => result.current.cancelProposal())
    expect(result.current.ai.proposal).toBeNull()
    expect(result.current.draft.artifact.segments).toEqual(item.artifact.segments)
    expect(api.saveItem).not.toHaveBeenCalled()
  })

  it('keeps explicit skip available after a failed review without losing the draft', async () => {
    api.reviewDraft.mockRejectedValue(new Error('Review unavailable'))
    api.skipReview.mockResolvedValue({ item: { ...item, stage: 'approve' },
      review: { state: 'skipped', input_version_id: 'v2' } })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.requestReview() })
    expect(result.current.error).toBe('Review unavailable')
    await act(async () => { await result.current.skip() })
    expect(result.current.stage).toBe('approve')
    expect(result.current.review.state).toBe('skipped')
    expect(result.current.draft.artifact.segments).toEqual(item.artifact.segments)
  })

  it('saves a specific review wording proposal as a new unapproved revision', async () => {
    const suggestion = { segment: 0, current: 'Exact old text', proposed: 'Clearer wording' }
    api.reviewDraft.mockResolvedValue({ operation: { ...reviewed, result: { review: { ...review, proposals: [suggestion] } } } })
    api.saveItem.mockResolvedValue({ item: { ...item, working_revision: 3,
      artifact: { segments: ['Clearer wording'] }, active_approval_id: null } })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.requestReview() })
    await act(async () => { await result.current.acceptReviewProposal(suggestion) })
    expect(api.saveItem).toHaveBeenCalledWith('one', expect.objectContaining({ expected_revision: 2,
      artifact: { segments: ['Clearer wording'] } }), expect.any(String))
    expect(result.current.item.active_approval_id).toBeNull()
    expect(result.current.item.working_revision).toBe(3)
  })

  it('keeps an AI proposal separate until accepted and saves it as a new revision', async () => {
    api.generateDraft.mockResolvedValue({ operation: proposal })
    api.saveItem.mockResolvedValue({ item: { ...item, working_revision: 3,
      artifact: proposal.result.artifact, active_approval_id: null } })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.generateDraft() })
    expect(api.generateDraft).toHaveBeenCalledWith('one', { expected_revision: 2 }, expect.any(String))
    expect(result.current.draft.artifact.segments).toEqual(['Exact old text'])
    expect(result.current.ai.proposal.operation_id).toBe('op-1')
    await act(async () => { await result.current.acceptProposal() })
    expect(api.saveItem).toHaveBeenCalledWith('one', expect.objectContaining({ expected_revision: 2,
      artifact: { segments: ['  Proposed text\n'] } }), expect.any(String))
    expect(result.current.item.working_revision).toBe(3)
    expect(result.current.item.active_approval_id).toBeNull()
    expect(result.current.ai.proposal).toBeNull()
  })

  it('keeps later edits and refuses a proposal generated for the previous saved revision', async () => {
    const pending = deferred()
    api.generateDraft.mockReturnValue(pending.promise)
    const { result } = renderHook(useWorkflow)
    await open(result)
    let request
    act(() => { request = result.current.generateDraft() })
    edit(result, 'Newer unsaved text')
    await act(async () => { pending.resolve({ operation: proposal }); await request })
    expect(result.current.draft.artifact.segments).toEqual(['Newer unsaved text'])
    await act(async () => { await result.current.acceptProposal() })
    expect(api.saveItem).not.toHaveBeenCalled()
    expect(result.current.draft.artifact.segments).toEqual(['Newer unsaved text'])
  })

  it('does not accept a suggestion after a title-only change to the same revision', async () => {
    api.generateDraft.mockResolvedValue({ operation: { ...proposal,
      editorial_snapshot: { ...proposal.editorial_snapshot, title: 'Earlier title' } } })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.generateDraft() })
    expect(result.current.aiIsCurrent).toBe(false)
    await act(async () => { await result.current.acceptProposal() })
    expect(api.saveItem).not.toHaveBeenCalled()
  })

  it('does not accept a suggestion whose snapshot belongs to another item', async () => {
    api.generateDraft.mockResolvedValue({ operation: { ...proposal,
      editorial_snapshot: { ...proposal.editorial_snapshot, item_id: 'other' } } })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.generateDraft() })
    expect(result.current.aiIsCurrent).toBe(false)
    await act(async () => { await result.current.acceptProposal() })
    expect(api.saveItem).not.toHaveBeenCalled()
  })

  it('keeps request keys stable on transport failure and shows the real pending state', async () => {
    api.generateDraft.mockRejectedValueOnce(new Error('Connection lost'))
    api.generateDraft.mockResolvedValueOnce({ operation: { ...proposal, state: 'pending', result: null } })
    api.getOperation.mockResolvedValue({ operation: proposal })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.generateDraft() })
    expect(result.current.error).toBe('Connection lost')
    await act(async () => { await result.current.generateDraft() })
    expect(api.generateDraft.mock.calls[0][2]).toBe(api.generateDraft.mock.calls[1][2])
    expect(result.current.ai.operation.state).toBe('pending')
    await act(async () => { await result.current.generateDraft() })
    expect(api.generateDraft).toHaveBeenCalledTimes(2)
    await act(async () => { await result.current.checkAIStatus() })
    expect(result.current.ai.proposal.operation_id).toBe('op-1')
  })

  it('recovers a pending request when the saved item is reopened', async () => {
    api.getOperations.mockResolvedValue({ operations: [{ ...proposal, state: 'pending', result: null }] })
    const { result } = renderHook(useWorkflow)
    await open(result)
    expect(result.current.ai.operation.state).toBe('pending')
    await act(async () => { await result.current.generateDraft() })
    expect(api.generateDraft).not.toHaveBeenCalled()
  })

  it('keeps pending separate from selected activity and permits confirmed abandonment', async () => {
    const pending = { ...proposal, operation_id: 'pending', state: 'pending', result: null }
    api.getOperations.mockResolvedValue({ operations: [pending, reviewed] })
    api.abandonOperation.mockResolvedValue({ operation: { ...pending, state: 'failed', error: { code: 'operation_abandoned' } } })
    const { result } = renderHook(useWorkflow)
    await open(result)
    act(() => result.current.showAIActivity(reviewed))
    expect(result.current.ai.pending.operation_id).toBe('pending')
    await act(async () => { await result.current.generateDraft() })
    expect(api.generateDraft).not.toHaveBeenCalled()
    await act(async () => { await result.current.abandonAI() })
    expect(api.abandonOperation).toHaveBeenCalledWith('one', 'pending')
    expect(result.current.ai.pending).toBeNull()
  })

  it('reports when a request completed before the close request reached the server', async () => {
    const pending = { ...proposal, state: 'pending', result: null }
    api.getOperations.mockResolvedValue({ operations: [pending] })
    api.abandonOperation.mockResolvedValue({ operation: proposal })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.abandonAI() })
    expect(result.current.ai.proposal.operation_id).toBe('op-1')
    expect(result.current.notice).toMatch(/already completed/i)
    expect(result.current.notice).not.toMatch(/request closed/i)
  })

  it('does not mark older title advice current', async () => {
    const old = { ...reviewed, editorial_snapshot: { ...reviewed.editorial_snapshot, title: 'Old title' } }
    api.getOperations.mockResolvedValue({ operations: [old] })
    const { result } = renderHook(useWorkflow)
    await open(result)
    act(() => result.current.showAIActivity(old))
    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('does not create an operation when prior activity cannot be checked', async () => {
    api.getOperations.mockRejectedValue(new Error('Activity unavailable'))
    const { result } = renderHook(useWorkflow)
    await open(result)
    expect(result.current.ai.loadError).toBe('Activity unavailable')
    await act(async () => { await result.current.generateDraft() })
    expect(api.generateDraft).not.toHaveBeenCalled()
  })

  it('records Council advice as current only for its exact still-clean input', async () => {
    api.reviewDraft.mockResolvedValue({ operation: reviewed })
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.requestReview() })
    expect(result.current.reviewIsCurrent).toBe(true)
    expect(result.current.review.actions.required_actions).toEqual(['Explain the tradeoff'])
    edit(result, 'Changed after review')
    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('does not relabel late review results for a changed draft', async () => {
    const pending = deferred()
    api.reviewDraft.mockReturnValue(pending.promise)
    const { result } = renderHook(useWorkflow)
    await open(result)
    let request
    act(() => { request = result.current.requestReview() })
    edit(result, 'Changed while reviewing')
    await act(async () => { pending.resolve({ operation: reviewed }); await request })
    expect(result.current.reviewIsCurrent).toBe(false)
    expect(result.current.draft.artifact.segments).toEqual(['Changed while reviewing'])
  })

  it('does not apply results after unmount or expose another item response', async () => {
    const pending = deferred()
    api.generateDraft.mockReturnValue(pending.promise)
    const { result, unmount } = renderHook(useWorkflow)
    await open(result)
    let request
    act(() => { request = result.current.generateDraft() })
    unmount()
    await act(async () => { pending.resolve({ operation: { ...proposal, item_id: 'other' } }); await request })
    expect(api.saveItem).not.toHaveBeenCalled()
  })
})
