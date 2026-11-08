import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import * as workflow from './api/workflow'
import * as settings from './api/settings'

vi.mock('./app/useServerHealth', () => ({ useServerHealth: () => true }))
vi.mock('./api/workflow', () => ({ getCapabilities: vi.fn(), getItems: vi.fn(), getItem: vi.fn(),
  getOperations: vi.fn(), createItem: vi.fn(), saveItem: vi.fn(), skipReview: vi.fn(), approveItem: vi.fn(),
  getExport: vi.fn(), getHistory: vi.fn(), adaptVersion: vi.fn(), restoreVersion: vi.fn() }))
vi.mock('./api/settings', () => ({ getSettings: vi.fn(), saveProfile: vi.fn(), createSource: vi.fn(),
  updateSource: vi.fn(), createRequestId: vi.fn(() => 'settings-request') }))
vi.mock('./api/preferences', () => ({ getPreferences: vi.fn().mockResolvedValue({ preferences: [] }) }))

const profile = { name: '', role: '', bio: '', revision: 0, updated_at: null }
const source = { source_id: 'one', kind: 'rss', name: 'Engineering', url: 'https://example.com/feed',
  enabled: true, revision: 1, created_at: '', updated_at: '' }
const item = { item_id: 'item-1', owner_id: 'owner-1', title: 'Indexing', destination: 'linkedin',
  format: 'linkedin_post', stage: 'draft_review', working_revision: 1,
  context: { notes: '', experience: null, interpretation: null, sources: [], preference_snapshot_id: null },
  artifact: { segments: ['Saved draft'] }, active_approval_id: null, updated_at: '2026-11-05T09:12:00.000Z' }

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  workflow.getCapabilities.mockResolvedValue({ pairs: [{ destination: 'linkedin', format: 'linkedin_post', can_edit: true }] })
  workflow.getItems.mockResolvedValue({ items: [item] })
  workflow.getItem.mockResolvedValue({ item, review: null, approval: null })
  settings.getSettings.mockResolvedValue({ profile, sources: [source] })
})

describe('settings and workflow navigation', () => {
  it('keeps blank optional profile and unsaved settings while resuming the same exact draft', async () => {
    render(<App />)
    await userEvent.click(await screen.findByRole('button', { name: /resume indexing/i }))
    const draft = await screen.findByRole('textbox', { name: /^draft text$/i })
    fireEvent.change(draft, { target: { value: '  Exact draft\nsecond line  ' } })
    await userEvent.click(screen.getByRole('button', { name: /^settings$/i }))
    const name = await screen.findByRole('textbox', { name: /^name$/i })
    expect(name).toHaveValue('')
    fireEvent.change(name, { target: { value: '  Creator  ' } })
    const sourceGroup = screen.getByRole('group', { name: 'Engineering source' })
    fireEvent.change(within(sourceGroup).getByRole('textbox', { name: /source name/i }), { target: { value: '  Systems feed  ' } })
    expect(screen.getByRole('button', { name: /refresh settings/i })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /^workflow$/i }))
    expect(screen.getByRole('heading', { name: 'Indexing' })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /^draft text$/i })).toHaveValue('  Exact draft\nsecond line  ')
    await userEvent.click(screen.getByRole('button', { name: /^settings$/i }))
    expect(screen.getByRole('textbox', { name: /^name$/i })).toHaveValue('  Creator  ')
    expect(within(screen.getByRole('group', { name: 'Engineering source' })).getByRole('textbox', { name: /source name/i })).toHaveValue('  Systems feed  ')
    expect(screen.getByRole('button', { name: /refresh settings/i })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /open writing preferences/i }))
    expect(screen.getByRole('main', { name: /lessons workspace/i })).toBeInTheDocument()
  })
})
