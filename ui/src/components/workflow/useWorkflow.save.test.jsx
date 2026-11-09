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
  working_revision: 1,
  context: { ...emptyContext },
  artifact: { segments: [] },
  active_approval_id: null,
  updated_at: '2026-11-05T09:12:00.000Z',
  ...changes,
})

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

const openDraft = async result => {
  const item = makeItem()
  api.getItem.mockResolvedValueOnce({ item, review: null, approval: null })
  await act(async () => {
    await result.current.open(item.item_id)
  })
  return item
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
})

describe('useWorkflow saving', () => {
  it('keeps the exact draft and reuses the same key and body after a failed save', async () => {
    const { result } = renderHook(() => useWorkflow())
    await openDraft(result)
    const notes = '  exact notes\r\nsecond line  '
    await editNotes(result, notes)

    api.saveItem.mockRejectedValueOnce(new Error('Save failed'))
    await act(async () => {
      await result.current.save()
    })

    expect(result.current.error).toBe('Save failed')
    expect(result.current.notice).toBe('')
    expect(result.current.draft.context.notes).toBe(notes)
    expect(result.current.item.working_revision).toBe(1)
    expect(result.current.dirty).toBe(true)

    api.saveItem.mockResolvedValueOnce({
      item: makeItem({ working_revision: 2, context: { ...emptyContext, notes } }),
    })
    await act(async () => {
      await result.current.save()
    })

    const [first, retry] = api.saveItem.mock.calls
    expect(retry[2]).toBe(first[2])
    expect(retry[1]).toEqual({
      expected_revision: 1,
      expected_updated_at: '2026-11-05T09:12:00.000Z',
      context: expect.objectContaining({ notes }),
      artifact: { segments: [] },
    })
    expect(result.current.item.working_revision).toBe(2)
    expect(result.current.dirty).toBe(false)
    expect(result.current.notice).toBe('Saved')
  })

  it('does not erase newer text when a pending save resolves', async () => {
    const { result } = renderHook(() => useWorkflow())
    await openDraft(result)
    await editNotes(result, '  first text  ')

    const pending = deferred()
    api.saveItem.mockReturnValueOnce(pending.promise)
    let saving
    act(() => {
      saving = result.current.save()
    })
    await editNotes(result, '  newer text  ')
    await act(async () => {
      pending.resolve({
        item: makeItem({ working_revision: 2, context: { ...emptyContext, notes: '  first text  ' } }),
      })
      await saving
    })

    expect(result.current.draft.context.notes).toBe('  newer text  ')
    expect(result.current.item.working_revision).toBe(2)
    expect(result.current.dirty).toBe(true)
    expect(result.current.notice).toBe('')
  })

  it('sends the last known updated_at and advances it from each save response', async () => {
    const { result } = renderHook(() => useWorkflow())
    await openDraft(result)
    api.saveItem.mockResolvedValueOnce({ item: makeItem({ working_revision: 2, updated_at: '2026-11-05T09:30:00.000Z' }) })
    await editNotes(result, 'one')
    await act(async () => { await result.current.save() })
    expect(api.saveItem.mock.calls[0][1].expected_updated_at).toBe('2026-11-05T09:12:00.000Z')
    api.saveItem.mockResolvedValueOnce({ item: makeItem({ working_revision: 3, updated_at: '2026-11-05T09:40:00.000Z' }) })
    await editNotes(result, 'two')
    await act(async () => { await result.current.save() })
    expect(api.saveItem.mock.calls[1][1].expected_updated_at).toBe('2026-11-05T09:30:00.000Z')
  })

  it('surfaces a revision conflict without clearing the draft', async () => {
    const { result } = renderHook(() => useWorkflow())
    await openDraft(result)
    await editNotes(result, '  pending text  ')

    api.saveItem.mockRejectedValueOnce(Object.assign(new Error('Revision conflict'), {
      status: 409,
      body: {
        detail: 'Revision conflict',
        code: 'revision_conflict',
        working_revision: 3,
        stage: 'draft_review',
        updated_at: '2026-11-05T09:20:00.000Z',
        active_approval_id: null,
      },
    }))
    await act(async () => {
      await result.current.save()
    })

    expect(result.current.error).toBe('Revision conflict')
    expect(result.current.conflict).toMatchObject({ code: 'revision_conflict', working_revision: 3 })
    expect(result.current.draft.context.notes).toBe('  pending text  ')
    expect(result.current.item.working_revision).toBe(1)
    expect(result.current.notice).toBe('')
    expect(result.current.dirty).toBe(true)
  })

  it('blocks opening another item while a save is pending, then permits a clean switch', async () => {
    const { result } = renderHook(() => useWorkflow())
    await openDraft(result)
    await editNotes(result, 'Saved A notes')
    const pending = deferred()
    api.saveItem.mockReturnValueOnce(pending.promise)
    let saving
    act(() => { saving = result.current.save() })
    await act(async () => { await result.current.open('item-B') })
    expect(api.getItem).toHaveBeenCalledTimes(1)
    expect(result.current.item.item_id).toBe('item-1')
    await act(async () => {
      pending.resolve({ item: makeItem({ working_revision: 2,
        context: { ...emptyContext, notes: 'Saved A notes' } }) })
      await saving
    })
    api.getItem.mockResolvedValueOnce({ item: makeItem({ item_id: 'item-B',
      context: { ...emptyContext, notes: 'B notes' } }), review: null, approval: null })
    await act(async () => { await result.current.open('item-B') })
    expect(result.current.item.item_id).toBe('item-B')
    expect(result.current.draft.context.notes).toBe('B notes')
  })

  it('clears conflict state once a save succeeds', async () => {
    const { result } = renderHook(() => useWorkflow())
    await openDraft(result)
    await editNotes(result, '  text  ')

    api.saveItem.mockRejectedValueOnce(Object.assign(new Error('Revision conflict'), {
      status: 409,
      body: { detail: 'Revision conflict', code: 'revision_conflict', working_revision: 3 },
    }))
    await act(async () => {
      await result.current.save()
    })
    expect(result.current.conflict).not.toBeNull()

    api.saveItem.mockResolvedValueOnce({
      item: makeItem({ working_revision: 4, context: { ...emptyContext, notes: '  text  ' } }),
    })
    await act(async () => {
      await result.current.save()
    })

    expect(result.current.conflict).toBeNull()
    expect(result.current.error).toBe('')
  })
})
