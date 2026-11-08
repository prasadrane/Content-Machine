import { createHash, webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import * as workflow from './api/workflow'
import * as settings from './api/settings'
import * as preferences from './api/preferences'
import { refreshDiscovery } from './api/discovery'

vi.mock('./app/useServerHealth', () => ({ useServerHealth: () => true }))
vi.mock('./api/workflow', () => ({ getCapabilities: vi.fn(), getItems: vi.fn(), getItem: vi.fn(),
  getOperations: vi.fn(), createItem: vi.fn(), saveItem: vi.fn(), skipReview: vi.fn(), approveItem: vi.fn(),
  getExport: vi.fn(), getHistory: vi.fn(), adaptVersion: vi.fn(), restoreVersion: vi.fn() }))
vi.mock('./api/settings', () => ({ getSettings: vi.fn(), saveProfile: vi.fn(), createSource: vi.fn(),
  updateSource: vi.fn(), createRequestId: vi.fn(() => 'source-request') }))
vi.mock('./api/preferences', () => ({ getPreferences: vi.fn() }))
vi.mock('./api/discovery', () => ({ refreshDiscovery: vi.fn() }))

const context = { notes: '', experience: null, interpretation: null, sources: [], preference_snapshot_id: null }
const initial = { item_id: 'one', owner_id: 'owner', title: 'A measured engineering idea', destination: 'instagram',
  format: 'instagram_caption', stage: 'idea', working_revision: 1, context,
  artifact: { segments: [] }, active_approval_id: null, updated_at: '2026-11-05T09:12:00.000Z' }
let saved
let approvedDigest
beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  saved = structuredClone(initial)
  approvedDigest = null
  workflow.getCapabilities.mockResolvedValue({ pairs: [
    { destination: 'linkedin', format: 'linkedin_post', can_edit: true },
    { destination: 'instagram', format: 'instagram_caption', can_edit: true },
    { destination: 'instagram', format: 'instagram_reel_script', can_edit: true },
  ] })
  workflow.getItems.mockResolvedValue({ items: [] })
  workflow.createItem.mockImplementation(async body => ({ item: { ...saved, ...body } }))
  workflow.getItem.mockImplementation(async () => ({ item: saved, review: null, approval: null }))
  workflow.getOperations.mockResolvedValue({ operations: [] })
  workflow.saveItem.mockImplementation(async (_id, body) => {
    saved = { ...saved, ...body, working_revision: saved.working_revision + 1 }
    return { item: saved }
  })
  workflow.skipReview.mockImplementation(async () => {
    saved = { ...saved, stage: 'approve' }
    return { item: saved, review: { state: 'skipped', input_version_id: `v${saved.working_revision}` } }
  })
  workflow.approveItem.mockImplementation(async (_id, body) => {
    approvedDigest = body.artifact_digest
    saved = { ...saved, stage: 'export', active_approval_id: 'approval' }
    return { item: saved, approval: { approval_id: 'approval', owner_id: saved.owner_id, item_id: saved.item_id,
      version_id: `v${saved.working_revision}`, destination: saved.destination, format: saved.format,
      artifact_digest: body.artifact_digest } }
  })
  workflow.getExport.mockImplementation(async (_id, version_id) => ({ version_id,
    artifact_digest: approvedDigest, segments: saved.artifact.segments }))
  settings.getSettings.mockResolvedValue({ profile: { name: '', role: '', bio: '', revision: 0 }, sources: [] })
  settings.createSource.mockImplementation(async body => ({ source: { ...body, source_id: 'new-source', revision: 1 } }))
  preferences.getPreferences.mockResolvedValue({ preferences: [] })
  refreshDiscovery.mockResolvedValue({ status: 'unavailable', items: [], errors: [] })
})

describe('manual creator journey through the real App', () => {
  it('recovers acknowledged LinkedIn approval after remount and copies exact saved text without replaying actions', async () => {
    window.history.replaceState(null, '', '/')
    const exact = '  Saved LinkedIn observation.\nCaf\u00e9 and exact trailing space.  '
    saved = { ...saved, title: 'Approved LinkedIn draft', destination: 'linkedin', format: 'linkedin_post',
      stage: 'export', working_revision: 4, artifact: { segments: [exact] }, active_approval_id: 'approval' }
    approvedDigest = 'sha256:' + createHash('sha256').update(JSON.stringify({
      destination: 'linkedin', format: 'linkedin_post', segments: [exact],
    })).digest('hex')
    const approval = { approval_id: 'approval', owner_id: saved.owner_id, item_id: saved.item_id,
      version_id: 'v4', destination: saved.destination, format: saved.format, artifact_digest: approvedDigest }
    workflow.getItems.mockImplementation(async () => ({ items: [structuredClone(saved)] }))
    workflow.getItem.mockImplementation(async () => ({ item: structuredClone(saved), review: null, approval }))
    const copy = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: copy } })
    const first = render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'Resume Approved LinkedIn draft' }))
    await screen.findByText('Ready to copy or download')
    first.unmount()
    window.history.replaceState(null, '', '/')
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'Resume Approved LinkedIn draft' }))
    await screen.findByText('Ready to copy or download')
    await userEvent.click(screen.getByRole('button', { name: 'Copy' }))
    expect(copy).toHaveBeenCalledWith(exact)
    expect(workflow.getExport).toHaveBeenLastCalledWith(saved.item_id, 'v4')
    expect(workflow.createItem).not.toHaveBeenCalled()
    expect(workflow.saveItem).not.toHaveBeenCalled()
    expect(workflow.skipReview).not.toHaveBeenCalled()
    expect(workflow.approveItem).not.toHaveBeenCalled()
  })

  it('creates for a selected platform, preserves exact text and requires explicit approval after skip', async () => {
    const copy = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: copy } })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: 'New content' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Title' }), { target: { value: saved.title } })
    await userEvent.click(screen.getByRole('button', { name: 'Instagram' }))
    await userEvent.click(screen.getByRole('button', { name: 'Create content' }))
    expect(workflow.createItem).toHaveBeenCalledWith({ title: saved.title,
      destination: 'instagram', format: 'instagram_caption' }, expect.any(String))
    const notes = await screen.findByRole('textbox', { name: 'Your notes' })
    fireEvent.change(notes, { target: { value: '  Actual source notes\n' } })
    await userEvent.click(screen.getByRole('button', { name: 'Continue to draft' }))
    const draft = await screen.findByRole('textbox', { name: 'Draft text' })
    const exact = '  A technical observation.\nA measured tradeoff.  '
    fireEvent.change(draft, { target: { value: exact } })
    await userEvent.click(screen.getByRole('button', { name: '1. Idea' }))
    expect(screen.getByRole('textbox', { name: 'Your notes' })).toHaveValue('  Actual source notes\n')
    await userEvent.click(screen.getByRole('button', { name: '2. Draft & review' }))
    expect(screen.getByRole('textbox', { name: 'Draft text' })).toHaveValue(exact)
    await userEvent.click(screen.getByRole('button', { name: 'Skip AI review and continue' }))
    expect(await screen.findByText('Review skipped for this saved version.')).toBeInTheDocument()
    expect(workflow.approveItem).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Approve this version' })).toBeDisabled()
    expect(screen.getByText(exact, { exact: false, selector: 'pre', normalizer: value => value })).toHaveTextContent('A technical observation.')
    expect(screen.getAllByText(/instagram caption/i).length).toBeGreaterThan(0)
    await userEvent.click(screen.getByRole('checkbox', { name: /i approve this exact version/i }))
    await userEvent.click(screen.getByRole('button', { name: 'Approve this version' }))
    await screen.findByText('Ready to copy or download')
    await userEvent.click(screen.getByRole('button', { name: 'Copy' }))
    expect(copy).toHaveBeenCalledWith(exact)
    expect(settings.getSettings).not.toHaveBeenCalled()
    expect(preferences.getPreferences).not.toHaveBeenCalled()
    expect(refreshDiscovery).not.toHaveBeenCalled()
    expect(workflow.getOperations).not.toHaveBeenCalled()
    for (const label of ['Oracle', 'Council', 'Distribute', 'Audio', 'Show workflow guide', 'Hide workflow guide']) {
      expect(screen.queryByRole('button', { name: label })).not.toBeInTheDocument()
    }
  })

  it('resumes without platform selection and returns from source configuration to the same unsaved idea', async () => {
    workflow.getItems.mockResolvedValue({ items: [saved] })
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: `Resume ${saved.title}` }))
    expect(screen.queryByRole('heading', { name: 'Start a piece of content' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Your notes' }), { target: { value: '  Unsaved personal notes\n' } })
    await userEvent.click(screen.getByRole('button', { name: 'Discover ideas' }))
    await userEvent.click(screen.getByRole('button', { name: 'Find ideas' }))
    expect(await screen.findByText(/discovery is unavailable/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Manage sources' }))
    fireEvent.change(await screen.findByRole('textbox', { name: 'New source name' }), { target: { value: 'Engineering sources' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'New RSS or Atom URL' }), { target: { value: 'https://example.com/feed' } })
    await userEvent.click(screen.getByRole('button', { name: 'Add source' }))
    await screen.findByRole('group', { name: 'Engineering sources source' })
    await userEvent.click(screen.getByRole('button', { name: 'Workflow' }))
    const workspace = screen.getByRole('main', { name: 'Workflow workspace' })
    expect(within(workspace).getByRole('heading', { name: saved.title })).toBeInTheDocument()
    expect(within(workspace).getByRole('textbox', { name: 'Your notes' })).toHaveValue('  Unsaved personal notes\n')
    expect(within(workspace).getByRole('button', { name: 'Discover ideas' })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: 'Your idea' }))
    expect(screen.getByRole('textbox', { name: 'Your notes' })).toHaveValue('  Unsaved personal notes\n')
  })
})
