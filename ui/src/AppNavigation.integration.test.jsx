import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import * as workflow from './api/workflow'

vi.mock('./app/useServerHealth', () => ({ useServerHealth: () => true }))
vi.mock('./api/workflow', () => ({ getCapabilities: vi.fn(), getItems: vi.fn(), getItem: vi.fn(),
  getOperations: vi.fn(), createItem: vi.fn(), saveItem: vi.fn(), skipReview: vi.fn(), approveItem: vi.fn(),
  getExport: vi.fn(), getHistory: vi.fn(), getVersion: vi.fn(), adaptVersion: vi.fn(), restoreVersion: vi.fn(),
  generateDraft: vi.fn(), reviewDraft: vi.fn() }))
vi.mock('./api/settings', () => ({ getSettings: vi.fn().mockResolvedValue({
  profile: { name: '', role: '', bio: '', revision: 0 }, sources: [] }) }))
vi.mock('./api/preferences', () => ({ getPreferences: vi.fn().mockResolvedValue({ preferences: [] }) }))

const item = { item_id: 'one', owner_id: 'owner', title: 'Engineering draft', destination: 'linkedin',
  format: 'linkedin_post', stage: 'draft_review', working_revision: 2,
  context: { notes: '', experience: null, interpretation: null, sources: [], preference_snapshot_id: null },
  artifact: { segments: ['Original saved text'] }, active_approval_id: null, updated_at: '2026-11-07T12:00:00.000Z' }

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  window.history.replaceState(null, '', '/')
  workflow.getCapabilities.mockResolvedValue({ pairs: [{ destination: 'linkedin', format: 'linkedin_post', can_edit: true }] })
  workflow.getItems.mockResolvedValue({ items: [item] })
  workflow.getItem.mockResolvedValue({ item, review: null, approval: null })
  workflow.getOperations.mockResolvedValue({ operations: [] })
})

describe('private item browser navigation', () => {
  it('retains an unfinished new-content form across Back and Forward', async () => {
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'New content' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Title' }), { target: { value: 'Unfinished title' } })
    act(() => window.history.back())
    await screen.findByRole('heading', { name: 'Your content' })
    act(() => window.history.forward())
    expect(await screen.findByRole('textbox', { name: 'Title' })).toHaveValue('Unfinished title')
  })
  it('opens an item link and handles missing Export prerequisites visibly without generating or approving', async () => {
    window.history.replaceState(null, '', '/#/workflow/items/one/export')
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Engineering draft' })).toBeInTheDocument()
    expect(await screen.findByText(/approve this saved version before exporting/i)).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue('Original saved text')
    expect(window.location.hash).toBe('#/workflow/items/one/draft_review')
    expect(workflow.approveItem).not.toHaveBeenCalled()
    expect(workflow.getExport).not.toHaveBeenCalled()
    expect(workflow.getOperations).not.toHaveBeenCalled()
  })

  it('preserves unsaved input and active stage through Back/Forward and Settings without replaying AI', async () => {
    workflow.getCapabilities.mockResolvedValue({ pairs: [{ destination: 'linkedin', format: 'linkedin_post',
      can_edit: true, can_generate: true, can_review: true }] })
    window.history.replaceState(null, '', '/#/workflow/items/one/draft_review')
    render(<App />)
    const draft = await screen.findByRole('textbox', { name: 'Draft text' })
    fireEvent.change(draft, { target: { value: '  Unsaved exact draft\n' } })
    await userEvent.click(screen.getByRole('button', { name: '1. Idea' }))
    expect(window.location.hash).toBe('#/workflow/items/one/idea')
    act(() => window.history.back())
    await waitFor(() => expect(screen.getByRole('button', { name: '2. Draft & review' })).toHaveAttribute('aria-current', 'step'))
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue('  Unsaved exact draft\n')
    await userEvent.click(screen.getByRole('button', { name: 'Settings' }))
    expect(window.location.hash).toBe('#/settings')
    act(() => window.history.back())
    await screen.findByRole('main', { name: 'Workflow workspace' })
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue('  Unsaved exact draft\n')
    act(() => window.history.forward())
    await screen.findByRole('main', { name: 'Settings workspace' })
    await userEvent.click(screen.getByRole('button', { name: 'Workflow' }))
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue('  Unsaved exact draft\n')
    expect(workflow.getItem).toHaveBeenCalledTimes(1)
    expect(workflow.generateDraft).not.toHaveBeenCalled()
    expect(workflow.reviewDraft).not.toHaveBeenCalled()
    expect(workflow.approveItem).not.toHaveBeenCalled()
  })

  it('rejects an item-changing history jump while preserving newer unsaved text', async () => {
    window.history.replaceState(null, '', '/#/workflow/items/one/draft_review')
    render(<App />)
    fireEvent.change(await screen.findByRole('textbox', { name: 'Draft text' }), { target: { value: 'Newer private text' } })
    act(() => {
      window.history.pushState(null, '', '#/workflow/items/other/idea')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })
    expect(await screen.findByText(/save or discard your changes before leaving/i)).toBeInTheDocument()
    expect(window.location.hash).toBe('#/workflow/items/one/draft_review')
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue('Newer private text')
    expect(workflow.getItem).toHaveBeenCalledTimes(1)
  })
})
