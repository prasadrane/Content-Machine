import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useWorkflow } from './useWorkflow'
import * as api from '../../api/workflow'
import { artifactDigest } from './workflowUtils'

vi.mock('../../api/workflow', () => ({
  getItems: vi.fn(), getCapabilities: vi.fn(), getItem: vi.fn(),
  getHistory: vi.fn(), getExport: vi.fn(), saveItem: vi.fn(),
  skipReview: vi.fn(), approveItem: vi.fn(), createItem: vi.fn(), adaptVersion: vi.fn(),
}))

const item = {
  item_id: 'one', owner_id: 'owner-one', title: 'Indexing', destination: 'linkedin', format: 'linkedin_post',
  working_revision: 2, stage: 'draft_review', context: { notes: '' },
  artifact: { segments: ['saved draft'] }, active_approval_id: null,
}
function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}
async function open(result) {
  await act(async () => { await result.current.open('one') })
}
function edit(result) {
  act(() => result.current.updateDraft(previous => ({
    ...previous, artifact: { segments: ['newer unsaved draft'] },
  })))
}
beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  api.getItems.mockResolvedValue({ items: [item] })
  api.getCapabilities.mockResolvedValue({ pairs: [] })
  api.getItem.mockResolvedValue({ item, review: null, approval: null })
})

describe('workflow pending operations', () => {
  it.each(['different-item', 'different-digest', 'different-revision', 'different-approval'])('rejects a %s approval receipt without advancing', async scenario => {
    const receipt = { item: { ...item, stage: 'export', active_approval_id: 'approval' },
      approval: { approval_id: 'approval', owner_id: item.owner_id, item_id: item.item_id,
        version_id: 'v2', destination: item.destination, format: item.format,
        artifact_digest: await artifactDigest(item) } }
    if (scenario === 'different-item') receipt.approval.item_id = 'other'
    if (scenario === 'different-digest') receipt.approval.artifact_digest = `sha256:${'0'.repeat(64)}`
    if (scenario === 'different-revision') receipt.item.working_revision = 1
    if (scenario === 'different-approval') receipt.item.active_approval_id = 'other'
    api.approveItem.mockResolvedValue(receipt)
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.approve() })
    expect(result.current.stage).toBe('draft_review')
    expect(result.current.approval).toBeNull()
    expect(result.current.item).toEqual(item)
    expect(result.current.error).toMatch(/approval.*match/i)
    expect(api.getExport).not.toHaveBeenCalled()
  })

  it('keeps the exact draft and reuses the approval key after a failed request', async () => {
    api.approveItem.mockRejectedValue(new Error('Approval unavailable'))
    const { result } = renderHook(useWorkflow)
    await open(result)
    await act(async () => { await result.current.approve() })
    expect(result.current.stage).toBe('draft_review')
    expect(result.current.draft.artifact).toEqual(item.artifact)
    expect(result.current.approval).toBeNull()
    expect(api.getExport).not.toHaveBeenCalled()
    await act(async () => { await result.current.approve() })
    expect(api.approveItem.mock.calls[1][2]).toBe(api.approveItem.mock.calls[0][2])
  })
  it('shows saved work without waiting for capabilities', async () => {
    const capabilities = deferred()
    api.getCapabilities.mockReturnValue(capabilities.promise)
    const { result, unmount } = renderHook(useWorkflow)
    await waitFor(() => expect(result.current.items).toEqual([item]))
    expect(result.current.loading).toBe(false)
    expect(result.current.capabilitiesLoading).toBe(true)
    await act(async () => { capabilities.resolve({ pairs: [] }); await capabilities.promise })
    expect(result.current.capabilitiesLoading).toBe(false)
    unmount()
  })

  it('keeps newer text after a pending skip and leaves it in the editor', async () => {
    const pending = deferred()
    api.skipReview.mockReturnValue(pending.promise)
    const { result } = renderHook(useWorkflow)
    await open(result)
    let skipping
    act(() => { skipping = result.current.skip() })
    edit(result)
    await act(async () => {
      pending.resolve({ item: { ...item, stage: 'approve' }, review: { state: 'skipped' } })
      await skipping
    })
    expect(result.current.draft.artifact.segments).toEqual(['newer unsaved draft'])
    expect(result.current.dirty).toBe(true)
    expect(result.current.stage).toBe('draft_review')
  })

  it('does not approve if the draft changes while its digest is calculated', async () => {
    const digest = deferred()
    vi.stubGlobal('crypto', { ...webcrypto, subtle: { digest: () => digest.promise } })
    const { result } = renderHook(useWorkflow)
    await open(result)
    let approving
    act(() => { approving = result.current.approve() })
    edit(result)
    await act(async () => {
      digest.resolve(new Uint8Array(32).buffer)
      await approving
    })
    expect(api.approveItem).not.toHaveBeenCalled()
    expect(result.current.error).toMatch(/save.*changes/i)
  })

  it('keeps newer text after pending approval and requires another approval', async () => {
    const pending = deferred()
    api.approveItem.mockReturnValue(pending.promise)
    const { result } = renderHook(useWorkflow)
    await open(result)
    let approving
    act(() => { approving = result.current.approve() })
    await waitFor(() => expect(api.approveItem).toHaveBeenCalled())
    edit(result)
    await act(async () => {
      pending.resolve({
        item: { ...item, stage: 'export', active_approval_id: 'approval' },
        approval: { approval_id: 'approval', version_id: 'v2', owner_id: item.owner_id,
          item_id: item.item_id, destination: item.destination, format: item.format,
          artifact_digest: await artifactDigest(item) },
      })
      await approving
    })
    expect(result.current.draft.artifact.segments).toEqual(['newer unsaved draft'])
    expect(result.current.stage).toBe('draft_review')
    expect(api.getExport).not.toHaveBeenCalled()
    await act(async () => { await result.current.loadExport() })
    expect(api.getExport).not.toHaveBeenCalled()
  })
})
