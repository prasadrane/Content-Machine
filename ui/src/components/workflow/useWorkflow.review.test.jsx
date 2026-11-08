import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useWorkflow } from './useWorkflow'
import * as api from '../../api/workflow'

vi.mock('../../api/workflow', () => ({
  getCapabilities: vi.fn(),
  getItems: vi.fn(),
  getItem: vi.fn(),
  createItem: vi.fn(),
  saveItem: vi.fn(),
  skipReview: vi.fn(),
  approveItem: vi.fn(),
  getExport: vi.fn(),
  getHistory: vi.fn(),
  getOperations: vi.fn(),
  adaptVersion: vi.fn(),
}))

const emptyContext = {
  notes: '',
  experience: null,
  interpretation: null,
  sources: [],
  preference_snapshot_id: null,
}

const makeItem = (changes = {}) => ({
  item_id: 'item-1',
  owner_id: 'owner-1',
  title: 'Indexing',
  destination: 'linkedin',
  format: 'linkedin_post',
  stage: 'draft_review',
  working_revision: 2,
  context: { ...emptyContext },
  artifact: { segments: ['  exact draft\n'] },
  active_approval_id: null,
  updated_at: '2026-11-05T09:12:00.000Z',
  ...changes,
})

const completedReview = (changes = {}) => ({
  review_id: 'review-1',
  item_id: 'item-1',
  input_version_id: 'v2',
  state: 'completed',
  actions: {},
  proposals: [],
  ...changes,
})

const open = async (result, item, review, history) => {
  api.getItem.mockResolvedValueOnce({ item, review, approval: null })
  if (history && review) {
    const version = history.versions.find(entry => entry.version_id === review.input_version_id)
    if (version) api.getOperations.mockResolvedValueOnce({ operations: [{ kind: 'review', state: 'completed',
      item_id: item.item_id, input_version_id: version.version_id, result: { review },
      editorial_snapshot: { item_id: item.item_id, version_id: version.version_id, revision: version.revision,
        title: item.title, destination: item.destination, format: item.format, context: item.context, artifact: item.artifact } }] })
  }
  await act(async () => {
    await result.current.open(item.item_id)
  })
}

const editNotes = (result, notes) => act(() => {
  result.current.updateDraft(previous => ({ ...previous, context: { ...previous.context, notes } }))
})

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  api.getItems.mockResolvedValue({ items: [] })
  api.getCapabilities.mockResolvedValue({
    pairs: [{ destination: 'linkedin', format: 'linkedin_post', can_edit: true }],
  })
  api.getHistory.mockResolvedValue({ versions: [], approvals: [] })
  api.getOperations.mockResolvedValue({ operations: [] })
})

describe('useWorkflow review currency', () => {
  it('is current when an owned completed operation binds the review to the acknowledged snapshot', async () => {
    const { result } = renderHook(() => useWorkflow())
    await open(result, makeItem(), completedReview(), {
      versions: [{ version_id: 'v2', revision: 2 }],
      approvals: [],
    })

    expect(result.current.reviewBinding).toMatchObject({ revision: 2, versionId: 'v2', verified: true })
    expect(result.current.reviewIsCurrent).toBe(true)
  })

  it('is not current for a review of an earlier version', async () => {
    const { result } = renderHook(() => useWorkflow())
    await open(result, makeItem(), completedReview({ input_version_id: 'v1' }), {
      versions: [{ version_id: 'v1', revision: 1 }, { version_id: 'v2', revision: 2 }],
      approvals: [],
    })

    expect(result.current.reviewBinding.verified).toBe(false)
    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('is not current when operations cannot confirm the association', async () => {
    const { result } = renderHook(() => useWorkflow())
    api.getOperations.mockRejectedValueOnce(new Error('Activity unavailable'))
    await open(result, makeItem(), completedReview())

    expect(result.current.reviewBinding.verified).toBe(false)
    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('rejects a completed operation whose snapshot belongs to another item', async () => {
    const item = makeItem()
    const review = completedReview()
    api.getOperations.mockResolvedValueOnce({ operations: [{ kind: 'review', state: 'completed',
      item_id: item.item_id, input_version_id: review.input_version_id, result: { review },
      editorial_snapshot: { ...item, item_id: 'other', revision: item.working_revision, version_id: 'v2' } }] })
    const { result } = renderHook(() => useWorkflow())
    await open(result, item, review)
    expect(result.current.reviewBinding.verified).toBe(false)
    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('rejects an operation for a different review even when its snapshot matches', async () => {
    const item = makeItem()
    const review = completedReview()
    api.getOperations.mockResolvedValueOnce({ operations: [{ kind: 'review', state: 'completed',
      input_version_id: 'v2', result: { review: completedReview({ review_id: 'other' }) },
      editorial_snapshot: { ...item, revision: 2, version_id: 'v2' } }] })
    const { result } = renderHook(() => useWorkflow())
    await open(result, item, review)
    expect(result.current.reviewBinding.verified).toBe(false)
    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('is not current for a failed review even if the version matches', async () => {
    const { result } = renderHook(() => useWorkflow())
    await open(result, makeItem(), completedReview({ state: 'failed' }), {
      versions: [{ version_id: 'v2', revision: 2 }],
      approvals: [],
    })

    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('is not current after the draft changes', async () => {
    const { result } = renderHook(() => useWorkflow())
    await open(result, makeItem(), completedReview(), {
      versions: [{ version_id: 'v2', revision: 2 }],
      approvals: [],
    })
    expect(result.current.reviewIsCurrent).toBe(true)

    await editNotes(result, '  edited after review  ')

    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('marks a review stale once a newer revision is acknowledged', async () => {
    const { result } = renderHook(() => useWorkflow())
    await open(result, makeItem(), completedReview(), {
      versions: [{ version_id: 'v2', revision: 2 }],
      approvals: [],
    })
    await editNotes(result, '  newer text  ')
    api.saveItem.mockResolvedValueOnce({
      item: makeItem({ working_revision: 3, context: { ...emptyContext, notes: '  newer text  ' } }),
    })
    await act(async () => {
      await result.current.save()
    })

    expect(result.current.item.working_revision).toBe(3)
    expect(result.current.reviewIsCurrent).toBe(false)
  })

  it('keeps an explicit skip distinct from a current completed review', async () => {
    const { result } = renderHook(() => useWorkflow())
    await open(result, makeItem(), null)
    api.skipReview.mockResolvedValueOnce({
      item: makeItem({ stage: 'approve', working_revision: 2 }),
      review: { review_id: 'review-2', state: 'skipped', input_version_id: 'v2' },
    })
    await act(async () => {
      await result.current.skip()
    })

    expect(result.current.review).toMatchObject({ state: 'skipped', input_version_id: 'v2' })
    expect(result.current.reviewBinding).toMatchObject({ revision: 2, versionId: 'v2', verified: true })
    expect(result.current.reviewIsCurrent).toBe(false)
  })
})
