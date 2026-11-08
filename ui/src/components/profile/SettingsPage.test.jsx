import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SettingsPage from './SettingsPage'
import * as api from '../../api/settings'

vi.mock('../../api/settings', () => ({
  getSettings: vi.fn(), saveProfile: vi.fn(), createSource: vi.fn(), updateSource: vi.fn(),
  createRequestId: vi.fn(),
}))

const profile = { name: '', role: '', bio: '', revision: 0, updated_at: null }
const source = (id, name, url) => ({ source_id: id, kind: 'rss', name, url,
  enabled: true, revision: 1, created_at: '2026-11-01T00:00:00.000Z', updated_at: '2026-11-01T00:00:00.000Z' })

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  let request = 0
  api.createRequestId.mockImplementation(() => `request-${++request}`)
  api.getSettings.mockResolvedValue({ profile, sources: [] })
})

describe('creator settings', () => {
  it('starts with optional blank factual fields and links to the shared preferences view', async () => {
    const openLessons = vi.fn()
    render(<SettingsPage onOpenLessons={openLessons} />)
    expect(await screen.findByRole('heading', { name: /settings/i })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /^name$/i })).toHaveValue('')
    expect(screen.getByRole('textbox', { name: /^role$/i })).toHaveValue('')
    expect(screen.getByRole('textbox', { name: /^about you$/i })).toHaveValue('')
    expect(screen.getByText(/no sources configured/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /open writing preferences/i }))
    expect(openLessons).toHaveBeenCalledOnce()
  })

  it('preserves exact profile input and the retry key on a failed save', async () => {
    api.saveProfile.mockRejectedValueOnce(new Error('Save failed'))
    api.saveProfile.mockImplementationOnce(async data => ({ profile: {
      name: data.name, role: data.role, bio: data.bio, revision: 1, updated_at: '2026-11-01T00:00:00.000Z',
    } }))
    render(<SettingsPage />)
    const name = await screen.findByRole('textbox', { name: /^name$/i })
    fireEvent.change(name, { target: { value: '  Ada  ' } })
    const bio = screen.getByRole('textbox', { name: /^about you$/i })
    fireEvent.change(bio, { target: { value: 'First line\nSecond line  ' } })
    expect(screen.getByRole('button', { name: /refresh settings/i })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /save profile/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Save failed')
    expect(name).toHaveValue('  Ada  ')
    expect(bio).toHaveValue('First line\nSecond line  ')
    await userEvent.click(screen.getByRole('button', { name: /save profile/i }))
    await waitFor(() => expect(api.saveProfile).toHaveBeenCalledTimes(2))
    expect(api.saveProfile.mock.calls[0][1]).toBe(api.saveProfile.mock.calls[1][1])
    expect(api.saveProfile.mock.calls[1][0]).toEqual({ name: '  Ada  ', role: '',
      bio: 'First line\nSecond line  ', expected_revision: 0 })
    expect(await screen.findByText('Profile saved')).toBeInTheDocument()
  })

  it('edits and disables one source without replacing another', async () => {
    const first = source('one', 'Engineering', 'https://example.com/feed')
    const second = source('two', 'Database', 'https://example.org/rss')
    api.getSettings.mockResolvedValue({ profile, sources: [first, second] })
    api.updateSource.mockResolvedValue({ source: { ...first, enabled: false, revision: 2 } })
    render(<SettingsPage />)
    const group = await screen.findByRole('group', { name: 'Engineering source' })
    await userEvent.click(within(group).getByRole('checkbox', { name: /enabled/i }))
    await userEvent.click(within(group).getByRole('button', { name: /save source/i }))
    await waitFor(() => expect(api.updateSource).toHaveBeenCalledWith('one',
      { expected_revision: 1, name: 'Engineering', url: 'https://example.com/feed', enabled: false }, expect.any(String)))
    expect(await screen.findByRole('group', { name: 'Database source' })).toBeInTheDocument()
    expect(within(group).getByRole('checkbox', { name: /enabled/i })).not.toBeChecked()
  })

  it('retains exact source input and retry key after a failed save', async () => {
    const first = source('one', 'Engineering', 'https://example.com/feed')
    api.getSettings.mockResolvedValue({ profile, sources: [first] })
    api.updateSource.mockRejectedValueOnce(new Error('Source save failed'))
    api.updateSource.mockImplementationOnce(async (_id, data) => ({ source: { ...first, ...data, revision: 2 } }))
    render(<SettingsPage />)
    const group = await screen.findByRole('group', { name: 'Engineering source' })
    const name = within(group).getByRole('textbox', { name: /source name/i })
    const url = within(group).getByRole('textbox', { name: /RSS or Atom URL/i })
    fireEvent.change(name, { target: { value: '  Systems feed  ' } })
    fireEvent.change(url, { target: { value: 'https://example.org/exact?x=1' } })
    await userEvent.click(within(group).getByRole('button', { name: /save source/i }))
    expect(await within(group).findByRole('alert')).toHaveTextContent('Source save failed')
    expect(name).toHaveValue('  Systems feed  ')
    expect(url).toHaveValue('https://example.org/exact?x=1')
    expect(screen.getByRole('button', { name: /refresh settings/i })).toBeDisabled()
    await userEvent.click(within(group).getByRole('button', { name: /save source/i }))
    await waitFor(() => expect(api.updateSource).toHaveBeenCalledTimes(2))
    expect(api.updateSource.mock.calls[1][2]).toBe(api.updateSource.mock.calls[0][2])
    expect(api.createRequestId).toHaveBeenCalledTimes(1)
    expect(api.updateSource.mock.calls[1][1]).toMatchObject({ name: '  Systems feed  ', url: 'https://example.org/exact?x=1' })
  })

  it('preserves edits made while a profile save is pending', async () => {
    let finish
    api.saveProfile.mockReturnValueOnce(new Promise(resolve => { finish = resolve }))
    render(<SettingsPage />)
    const name = await screen.findByRole('textbox', { name: /^name$/i })
    fireEvent.change(name, { target: { value: 'Original' } })
    await userEvent.click(screen.getByRole('button', { name: /save profile/i }))
    fireEvent.change(name, { target: { value: 'Newer unsaved input' } })
    finish({ profile: { ...profile, name: 'Original', revision: 1 } })
    await waitFor(() => expect(screen.getByText(/unsaved profile changes/i)).toBeInTheDocument())
    expect(name).toHaveValue('Newer unsaved input')
    expect(screen.getByRole('button', { name: /refresh settings/i })).toBeDisabled()
  })

  it('prevents edits while a clean settings refresh is in flight', async () => {
    let finish
    api.getSettings.mockResolvedValueOnce({ profile, sources: [source('one', 'Engineering', 'https://example.com/feed')] })
      .mockReturnValueOnce(new Promise(resolve => { finish = resolve }))
    render(<SettingsPage />)
    const name = await screen.findByRole('textbox', { name: /^name$/i })
    await userEvent.click(screen.getByRole('button', { name: /refresh settings/i }))
    expect(name).toBeDisabled()
    expect(within(screen.getByRole('group', { name: 'Engineering source' })).getByRole('textbox', { name: /source name/i })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: /new source name/i })).toBeDisabled()
    finish({ profile, sources: [] })
    await waitFor(() => expect(name).toBeEnabled())
  })

  it('does not refresh while a source save is still pending', async () => {
    let finish
    const first = source('one', 'Engineering', 'https://example.com/feed')
    api.getSettings.mockResolvedValue({ profile, sources: [first] })
    api.updateSource.mockReturnValue(new Promise(resolve => { finish = resolve }))
    render(<SettingsPage />)
    const group = await screen.findByRole('group', { name: 'Engineering source' })
    const checkbox = within(group).getByRole('checkbox', { name: /enabled/i })
    await userEvent.click(checkbox)
    await userEvent.click(within(group).getByRole('button', { name: /save source/i }))
    await userEvent.click(checkbox)
    expect(screen.getByRole('button', { name: /refresh settings/i })).toBeDisabled()
    finish({ source: { ...first, enabled: false, revision: 2 } })
    await waitFor(() => expect(within(group).getByRole('button', { name: /save source/i })).toBeEnabled())
    expect(checkbox).toBeChecked()
    expect(screen.getByRole('button', { name: /refresh settings/i })).toBeDisabled()
  })
})
