import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PreferencesPage from './PreferencesPage'
import * as api from '../../api/preferences'

vi.mock('../../api/preferences', () => ({
  getPreferences: vi.fn(), createPreference: vi.fn(), editPreference: vi.fn(),
  activatePreference: vi.fn(), stopPreference: vi.fn(), rejectPreference: vi.fn(),
  getPreferenceHistory: vi.fn(),
}))

const active = { preference_id: 'pref-1', revision: 1, text: 'Use concrete examples.',
  status: 'active', origin: 'manual', created_at: '2026-11-06T12:00:00.000Z' }
const pending = { preference_id: 'pref-2', revision: 1, text: 'Avoid unsupported claims.',
  status: 'pending', origin: 'item', origin_ref: 'ver-2', created_at: '2026-11-06T12:00:00.000Z' }
beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('crypto', webcrypto)
  api.getPreferences.mockResolvedValue({ preferences: [] })
})

describe('creator writing preferences', () => {
  it('explains reusable preferences without generalizing item-specific facts automatically', async () => {
    render(<PreferencesPage />)
    await userEvent.click(await screen.findByRole('button', { name: /add preference/i }))
    expect(screen.getByText(/future AI requests use your active preferences/i)).toBeInTheDocument()
    expect(screen.getByText(/keep factual corrections in the content they belong to/i)).toBeInTheDocument()
    expect(screen.queryByText(/when that integration is available/i)).not.toBeInTheDocument()
    expect(api.createPreference).not.toHaveBeenCalled()
  })
  it('shows a truthful empty state and keeps exact input after a failed save', async () => {
    api.createPreference.mockRejectedValueOnce(new Error('Similar preference exists'))
    api.createPreference.mockResolvedValueOnce({ preference: active })
    render(<PreferencesPage />)
    expect(await screen.findByText(/no active preferences/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /add preference/i }))
    expect(screen.getByText(/future AI requests use your active preferences/i)).toBeInTheDocument()
    const text = screen.getByRole('textbox', { name: /preference text/i })
    await userEvent.type(text, '  Use concrete examples.  ')
    await userEvent.click(screen.getByRole('button', { name: /save and use/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Similar preference exists')
    expect(text).toHaveValue('  Use concrete examples.  ')
    expect(screen.queryByText('Added by you')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /save and use/i }))
    expect(await screen.findByText('Added by you')).toBeInTheDocument()
    expect(api.createPreference.mock.calls[1][1]).toBe(api.createPreference.mock.calls[0][1])
    expect(api.createPreference.mock.calls[0][0]).toEqual({ text: '  Use concrete examples.  ', consent: true })
  })

  it('keeps suggestions pending when activation is blocked and permits explicit dismissal', async () => {
    api.getPreferences.mockResolvedValue({ preferences: [pending] })
    api.activatePreference.mockRejectedValue(new Error('A similar active preference already exists.'))
    api.rejectPreference.mockResolvedValue({ preference: { ...pending, status: 'rejected', revision: 2 } })
    render(<PreferencesPage />)
    expect(await screen.findByText('Avoid unsupported claims.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /use suggestion/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/similar active preference/i)
    expect(screen.getByText('Pending suggestion')).toBeInTheDocument()
    expect(api.activatePreference.mock.calls[0][1]).toEqual({ expected_revision: 1, consent: true })
    await userEvent.click(screen.getByRole('button', { name: /dismiss suggestion/i }))
    expect(await screen.findByText('Dismissed')).toBeInTheDocument()
  })

  it('lets the author revise a suggestion before explicitly using it', async () => {
    api.getPreferences.mockResolvedValue({ preferences: [{ ...pending, conflict_preference_id: 'pref-1' }] })
    api.editPreference.mockResolvedValue({ preference: { ...pending, text: 'Use grounded examples.', status: 'active', revision: 2 } })
    render(<PreferencesPage />)
    expect(await screen.findByText(/overlapped with an active preference/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /edit suggestion/i }))
    const text = screen.getByRole('textbox', { name: /preference text/i })
    await userEvent.clear(text)
    await userEvent.type(text, 'Use grounded examples.')
    await userEvent.click(screen.getByRole('button', { name: /save and use/i }))
    expect(await screen.findByText('Active')).toBeInTheDocument()
    expect(api.editPreference.mock.calls[0][1]).toEqual({
      text: 'Use grounded examples.', expected_revision: 1, consent: true,
    })
  })

  it('stops and edits only after acknowledged server responses', async () => {
    api.getPreferences.mockResolvedValue({ preferences: [active] })
    api.stopPreference.mockRejectedValueOnce(new Error('Could not save'))
    api.stopPreference.mockResolvedValueOnce({ preference: { ...active, status: 'stopped', revision: 2 } })
    render(<PreferencesPage />)
    await screen.findByText(active.text)
    await userEvent.click(screen.getByRole('button', { name: /stop using/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not save')
    expect(screen.getByText('Active')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /stop using/i }))
    expect(await screen.findByText('Stopped')).toBeInTheDocument()
    expect(api.stopPreference.mock.calls[0][2]).toBe(api.stopPreference.mock.calls[1][2])
  })

  it('preserves the edit field on conflict and exposes persisted history', async () => {
    api.getPreferences.mockResolvedValue({ preferences: [active] })
    api.editPreference.mockRejectedValue(new Error('This preference changed.'))
    api.getPreferenceHistory.mockResolvedValue({ events: [
      { revision: 1, text: active.text, status: 'active', event: 'created' },
    ] })
    render(<PreferencesPage />)
    await screen.findByText(active.text)
    const card = screen.getByText(active.text).closest('article')
    await userEvent.click(within(card).getByRole('button', { name: /history/i }))
    expect(await within(card).findByText(/revision 1/i)).toBeInTheDocument()
    await userEvent.click(within(card).getByRole('button', { name: /edit/i }))
    const text = screen.getByRole('textbox', { name: /preference text/i })
    await userEvent.clear(text)
    await userEvent.type(text, 'New wording')
    await userEvent.click(screen.getByRole('button', { name: /save and use/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This preference changed.')
    expect(text).toHaveValue('New wording')
    expect(api.editPreference.mock.calls[0][1]).toEqual({ text: 'New wording', expected_revision: 1, consent: true })
  })

  it('keeps the editor stable while a save is pending', async () => {
    let finish
    api.createPreference.mockReturnValue(new Promise(resolve => { finish = resolve }))
    render(<PreferencesPage />)
    await screen.findByText(/no active preferences/i)
    await userEvent.click(screen.getByRole('button', { name: /add preference/i }))
    const text = screen.getByRole('textbox', { name: /preference text/i })
    await userEvent.type(text, 'A saved preference')
    await userEvent.click(screen.getByRole('button', { name: /save and use/i }))
    expect(text).toBeDisabled()
    finish({ preference: { ...active, text: 'A saved preference' } })
    expect(await screen.findByText('Added by you')).toBeInTheDocument()
    expect(screen.getByText('A saved preference')).toBeInTheDocument()
  })

  it('discards history that resolves after the list is refreshed', async () => {
    let finish
    api.getPreferences.mockResolvedValue({ preferences: [active] })
    api.getPreferenceHistory.mockReturnValue(new Promise(resolve => { finish = resolve }))
    render(<PreferencesPage />)
    await screen.findByText(active.text)
    await userEvent.click(screen.getByRole('button', { name: /history/i }))
    await userEvent.click(screen.getByRole('button', { name: /refresh/i }))
    await act(async () => {
      finish({ events: [{ revision: 1, text: 'Stale history', status: 'active' }] })
    })
    await screen.findByText(active.text)
    expect(screen.queryByText(/stale history/i)).not.toBeInTheDocument()
  })

  it('protects an unsaved edit from unrelated preference actions', async () => {
    api.getPreferences.mockResolvedValue({ preferences: [active, pending] })
    render(<PreferencesPage />)
    await screen.findByText(active.text)
    await userEvent.click(screen.getByRole('button', { name: /^edit$/i }))
    const text = screen.getByRole('textbox', { name: /preference text/i })
    await userEvent.clear(text)
    await userEvent.type(text, '  Unsaved wording  ')
    for (const button of screen.getAllByRole('button', { name: /stop using|use suggestion|edit suggestion|dismiss suggestion|^edit$/i })) {
      expect(button).toBeDisabled()
    }
    await userEvent.click(screen.getByRole('button', { name: /use suggestion/i }))
    expect(api.activatePreference).not.toHaveBeenCalled()
    expect(text).toHaveValue('  Unsaved wording  ')
  })
})
