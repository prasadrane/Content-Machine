import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
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
  stage: 'idea',
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

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  api.getItems.mockResolvedValue({ items: [] })
  api.getCapabilities.mockResolvedValue({
    pairs: [{ destination: 'linkedin', format: 'linkedin_post', can_edit: true }],
  })
  api.getHistory.mockResolvedValue({ versions: [], approvals: [] })
})

describe('useWorkflow loading', () => {
  it('refreshes copied guest items without replacing selected unsaved account work and removes the listener on unmount', async () => {
    const item = makeItem()
    api.getItem.mockResolvedValueOnce({ item, review: null, approval: null })
    const { result, unmount } = renderHook(() => useWorkflow())
    await waitFor(() => expect(result.current.loading).toBe(false))
    await act(async () => { await result.current.open(item.item_id) })
    act(() => result.current.updateDraft(previous => ({ ...previous, context: { ...previous.context, notes: 'Unsaved creator work' } })))
    api.getItems.mockResolvedValueOnce({ items: [item, makeItem({ item_id: 'copied' })] })
    act(() => window.dispatchEvent(new Event('cm:guest-work-copied')))
    await waitFor(() => expect(result.current.items).toHaveLength(2))
    expect(result.current.item.item_id).toBe(item.item_id)
    expect(result.current.draft.context.notes).toBe('Unsaved creator work')
    expect(result.current.dirty).toBe(true)
    const requests = api.getItems.mock.calls.length
    unmount()
    window.dispatchEvent(new Event('cm:guest-work-copied'))
    expect(api.getItems).toHaveBeenCalledTimes(requests)
  })
  it('retains the authenticated principal for transcript recovery across saved-work screens', async () => {
    const principal = { owner_id: 'owner-1', mode: 'trusted_local' }
    api.getCapabilities.mockResolvedValueOnce({ principal, pairs: [] })
    const { result } = renderHook(() => useWorkflow())
    await waitFor(() => expect(result.current.capabilitiesLoading).toBe(false))
    expect(result.current.principal).toEqual(principal)
  })
  it('keeps the saved-work list when capabilities fail', async () => {
    api.getItems.mockResolvedValue({ items: [makeItem()] })
    api.getCapabilities.mockRejectedValueOnce(new Error('Capabilities unavailable'))
    const { result } = renderHook(() => useWorkflow())
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.items).toHaveLength(1)
    expect(result.current.error).toBe('')
    expect(result.current.capabilitiesError).toBe('Capabilities unavailable')
  })

  it('keeps previously loaded pairs when a later capabilities load fails', async () => {
    const { result } = renderHook(() => useWorkflow())
    await waitFor(() => expect(result.current.pairs).toHaveLength(1))

    api.getCapabilities.mockRejectedValueOnce(new Error('Reload failed'))
    await act(async () => {
      await result.current.refresh()
    })

    expect(result.current.capabilitiesError).toBe('Reload failed')
    expect(result.current.pairs).toHaveLength(1)
  })

  it('keeps the previous list when a saved-work reload fails', async () => {
    api.getItems.mockResolvedValue({ items: [makeItem()] })
    const { result } = renderHook(() => useWorkflow())
    await waitFor(() => expect(result.current.items).toHaveLength(1))

    api.getItems.mockRejectedValueOnce(new Error('Workspace unavailable'))
    await act(async () => {
      await result.current.refresh()
    })

    expect(result.current.items).toHaveLength(1)
    expect(result.current.error).toBe('Workspace unavailable')
    expect(result.current.capabilitiesError).toBe('')
  })

  it('ignores a stale load that resolves after a newer one', async () => {
    const stale = deferred()
    const newer = deferred()
    api.getItems.mockReturnValueOnce(stale.promise).mockReturnValueOnce(newer.promise)
    const { result } = renderHook(() => useWorkflow())
    await waitFor(() => expect(api.getItems).toHaveBeenCalledTimes(1))

    let pending
    act(() => {
      pending = result.current.refresh()
    })
    await act(async () => {
      newer.resolve({ items: [makeItem({ item_id: 'newer' })] })
      await newer.promise
      await pending
    })
    await act(async () => {
      stale.resolve({ items: [makeItem({ item_id: 'stale' })] })
      await stale.promise
    })

    expect(result.current.items.map(entry => entry.item_id)).toEqual(['newer'])
  })

  it('drops a late opened item after unmount', async () => {
    const pending = deferred()
    api.getItem.mockReturnValueOnce(pending.promise)
    const { result, unmount } = renderHook(() => useWorkflow())
    await waitFor(() => expect(result.current.loading).toBe(false))

    let opening
    act(() => {
      opening = result.current.open('item-1')
    })
    unmount()
    await act(async () => {
      pending.resolve({
        item: makeItem(),
        review: { state: 'completed', input_version_id: 'v1' },
        approval: null,
      })
      await opening
    })

    expect(api.getHistory).not.toHaveBeenCalled()
  })
})
