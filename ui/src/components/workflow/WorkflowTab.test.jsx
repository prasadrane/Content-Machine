import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import WorkflowTab from './WorkflowTab'
import * as api from '../../api/workflow'

vi.mock('../../api/workflow', () => ({
  getCapabilities: vi.fn(), getItems: vi.fn(), getItem: vi.fn(), createItem: vi.fn(),
  saveItem: vi.fn(), skipReview: vi.fn(), approveItem: vi.fn(), getExport: vi.fn(),
  getHistory: vi.fn(), adaptVersion: vi.fn(),
}))

const emptyContext = { notes: '', experience: null, interpretation: null, sources: [], preference_snapshot_id: null }
const makeItem = (changes = {}) => ({
  item_id: 'item-1', owner_id: 'owner-1', title: 'Indexing', destination: 'linkedin',
  format: 'linkedin_post', stage: 'idea', working_revision: 1,
  context: { ...emptyContext }, artifact: { segments: [] }, active_approval_id: null,
  updated_at: '2026-11-05T09:12:00.000Z', ...changes,
})

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  api.getCapabilities.mockResolvedValue({ pairs: [{ destination: 'linkedin', format: 'linkedin_post', can_edit: true, can_generate: false, can_approve: true }] })
  api.getItems.mockResolvedValue({ items: [] })
})

describe('WorkflowTab', () => {
  it('distinguishes an empty saved-work list from a load failure', async () => {
    api.getItems.mockRejectedValueOnce(new Error('Workspace unavailable'))
    render(<WorkflowTab />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Workspace unavailable')
    expect(screen.queryByText(/no saved content/i)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByText(/no saved content/i)).toBeInTheDocument()
  })

  it('keeps the exact draft visible after a failed save', async () => {
    api.createItem.mockResolvedValue({ item: makeItem() })
    api.saveItem.mockRejectedValueOnce(new Error('Save failed'))
    render(<WorkflowTab />)
    await screen.findByText(/no saved content/i)
    await userEvent.click(screen.getByRole('button', { name: /new content/i }))
    await userEvent.type(screen.getByLabelText(/title/i), 'Indexing')
    await userEvent.click(screen.getByRole('button', { name: /create content/i }))
    const notes = await screen.findByRole('textbox', { name: /^your notes$/i })
    fireEvent.change(notes, { target: { value: '  exact notes\n' } })
    await userEvent.click(screen.getByRole('button', { name: /continue to draft/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Save failed')
    expect(notes).toHaveValue('  exact notes\n')
    await userEvent.click(screen.getByRole('button', { name: /continue to draft/i }))
    expect(api.saveItem.mock.calls[1][2]).toBe(api.saveItem.mock.calls[0][2])
  })

  it('lets the creator explicitly discard local edits and return to saved work', async () => {
    const initial = makeItem({ stage: 'draft_review', artifact: { segments: ['saved text'] } })
    api.getItems.mockResolvedValue({ items: [initial] })
    api.getItem.mockResolvedValue({ item: initial, review: null, approval: null })
    render(<WorkflowTab />)
    await userEvent.click(await screen.findByRole('button', { name: /resume indexing/i }))
    const draft = await screen.findByRole('textbox', { name: /^draft text$/i })
    fireEvent.change(draft, { target: { value: 'unsaved edit' } })
    expect(screen.getByRole('button', { name: /saved work/i })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /^discard changes$/i }))
    await userEvent.click(screen.getByRole('button', { name: /discard unsaved changes/i }))
    expect(screen.getByRole('textbox', { name: /^draft text$/i })).toHaveValue('saved text')
    await userEvent.click(screen.getByRole('button', { name: /saved work/i }))
    expect(await screen.findByRole('button', { name: /resume indexing/i })).toBeInTheDocument()
  })

  it('saves a draft, records a skip, obtains consent and exports the approved text', async () => {
    const initial = makeItem({ stage: 'draft_review' })
    api.getItems.mockResolvedValue({ items: [initial] })
    api.getItem.mockResolvedValue({ item: initial, review: null, approval: null })
    api.saveItem.mockImplementation(async (_id, payload) => ({ item: makeItem({ ...payload, working_revision: 2 }) }))
    api.skipReview.mockResolvedValue({ item: makeItem({ stage: 'approve', working_revision: 2, artifact: { segments: ['  My exact draft\n'] } }), review: { state: 'skipped', input_version_id: 'v2' } })
    api.approveItem.mockImplementation(async (_id, body) => ({ item: makeItem({ stage: 'export', working_revision: 2, artifact: { segments: ['  My exact draft\n'] }, active_approval_id: 'a2' }), approval: {
      approval_id: 'a2', version_id: 'v2', owner_id: 'owner-1', item_id: 'item-1', destination: 'linkedin',
      format: 'linkedin_post', artifact_digest: body.artifact_digest } }))
    api.getExport.mockImplementation(async () => ({ version_id: 'v2',
      artifact_digest: api.approveItem.mock.calls[0][1].artifact_digest, segments: ['  My exact draft\n'] }))
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })

    render(<WorkflowTab />)
    await userEvent.click(await screen.findByRole('button', { name: /resume indexing/i }))
    const draft = await screen.findByRole('textbox', { name: /^draft text$/i })
    fireEvent.change(draft, { target: { value: '  My exact draft\n' } })
    await userEvent.click(screen.getByRole('button', { name: /skip ai review and continue/i }))
    expect(await screen.findByText(/review skipped/i)).toBeInTheDocument()
    expect(api.skipReview).toHaveBeenCalledWith('item-1', { expected_revision: 2, expected_updated_at: '2026-11-05T09:12:00.000Z' }, expect.any(String))
    expect(screen.getByRole('button', { name: /approve this version/i })).toBeDisabled()
    await userEvent.click(screen.getByLabelText(/i approve/i))
    await userEvent.click(screen.getByRole('button', { name: /approve this version/i }))
    await waitFor(() => expect(api.approveItem).toHaveBeenCalledWith('item-1', expect.objectContaining({ expected_revision: 2, expected_updated_at: expect.any(String), consent: true, artifact_digest: expect.stringMatching(/^sha256:[a-f0-9]{64}$/) }), expect.any(String)))
    await screen.findByText(/ready to copy or download/i)
    await userEvent.click(screen.getByRole('button', { name: /^copy$/i }))
    expect(writeText).toHaveBeenCalledWith('  My exact draft\n')
  })
})
