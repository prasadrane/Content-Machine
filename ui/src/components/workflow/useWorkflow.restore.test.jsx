import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import * as api from '../../api/workflow'
import { useWorkflow } from './useWorkflow'

vi.mock('../../api/workflow', () => ({
  getItems: vi.fn(), getCapabilities: vi.fn(), getItem: vi.fn(), getHistory: vi.fn(),
  getExport: vi.fn(), restoreVersion: vi.fn(), createItem: vi.fn(), saveItem: vi.fn(),
  skipReview: vi.fn(), approveItem: vi.fn(), adaptVersion: vi.fn(),
}))
const item = {
  item_id: 'one', title: 'A draft', destination: 'linkedin', format: 'linkedin_post',
  stage: 'export', working_revision: 3, context: { notes: 'current' },
  artifact: { segments: ['current draft'] }, active_approval_id: 'approval-1',
}
const restored = { ...item, stage: 'draft_review', working_revision: 4,
  context: { notes: 'older' }, artifact: { segments: ['older draft'] }, active_approval_id: null }
function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  api.getItems.mockResolvedValue({ items: [item] })
  api.getCapabilities.mockResolvedValue({ pairs: [] })
  api.getItem.mockResolvedValue({ item, review: null, approval: { approval_id: 'approval-1', version_id: 'v3' } })
  api.getExport.mockResolvedValue({ version_id: 'v3', segments: ['current draft'] })
})
async function open(result) { await act(async () => { await result.current.open('one') }) }

describe('restoring owned versions', () => {
  it('uses the same key on a failed retry and opens the unapproved restored draft', async () => {
    const { result } = renderHook(useWorkflow)
    await open(result)
    api.restoreVersion.mockRejectedValueOnce(new Error('Try again')).mockResolvedValueOnce({ item: restored })
    await act(async () => { await result.current.restore('old-version') })
    expect(result.current.error).toBe('Try again')
    expect(result.current.item).toEqual(item)
    await act(async () => { await result.current.restore('old-version') })
    expect(api.restoreVersion.mock.calls[0]).toEqual(['one', { expected_revision: 3, version_id: 'old-version' },
      api.restoreVersion.mock.calls[1][2]])
    expect(result.current.item).toEqual(restored)
    expect(result.current.draft.artifact.segments).toEqual(['older draft'])
    expect(result.current.stage).toBe('draft_review')
    expect(result.current.approval).toBeNull()
    expect(result.current.exported).toBeNull()
  })
  it('keeps text edited while a restore was pending', async () => {
    const pending = deferred()
    api.restoreVersion.mockReturnValue(pending.promise)
    const { result } = renderHook(useWorkflow)
    await open(result)
    let operation
    act(() => { operation = result.current.restore('old-version') })
    act(() => result.current.updateDraft(previous => ({ ...previous, context: { notes: 'new notes' } })))
    await act(async () => { pending.resolve({ item: restored }); await operation })
    expect(result.current.draft.context.notes).toBe('new notes')
    expect(result.current.item.working_revision).toBe(4)
    expect(result.current.dirty).toBe(true)
    expect(result.current.approval).toBeNull()
  })
  it('refuses restoration while a draft has unsaved changes', async () => {
    const { result } = renderHook(useWorkflow)
    await open(result)
    act(() => result.current.updateDraft(previous => ({ ...previous, context: { notes: 'unsaved' } })))
    await act(async () => { await result.current.restore('old-version') })
    expect(api.restoreVersion).not.toHaveBeenCalled()
    expect(result.current.draft.context.notes).toBe('unsaved')
    expect(result.current.error).toMatch(/save/i)
  })
})
