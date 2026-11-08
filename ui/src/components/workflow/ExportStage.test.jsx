import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExportStage from './ExportStage'
import { getDownload } from '../../api/workflow'

vi.mock('../../api/workflow', () => ({ getDownload: vi.fn() }))
const digest = `sha256:${'a'.repeat(64)}`
const flow = () => ({
  item: { item_id: 'one', title: 'Indexing', working_revision: 2, active_approval_id: 'a2' },
  approval: { approval_id: 'a2', version_id: 'v2', artifact_digest: digest },
  exported: { version_id: 'v2', artifact_digest: digest, segments: ['  first\n', 'second  '] },
  busy: false, dirty: false, pairs: [], loadExport: vi.fn(), adapt: vi.fn(),
})
beforeEach(() => {
  vi.restoreAllMocks()
  vi.resetAllMocks()
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true, value: { writeText: vi.fn().mockResolvedValue() },
  })
  URL.createObjectURL = vi.fn().mockReturnValue('blob:export')
  URL.revokeObjectURL = vi.fn()
})
describe('approved export', () => {
  it('copies exact segments and reports clipboard denial', async () => {
    render(<ExportStage flow={flow()} />)
    await userEvent.click(screen.getByRole('button', { name: /^copy$/i }))
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('  first\n\n\nsecond  ')
    navigator.clipboard.writeText.mockRejectedValueOnce(new Error('Permission denied'))
    await userEvent.click(screen.getByRole('button', { name: /copy post 2/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not copy/i)
  })
  it('downloads the server blob and filename and revokes its object URL', async () => {
    const blob = new Blob(['server exact bytes'])
    getDownload.mockResolvedValue({ blob, filename: 'server-r2.txt', artifactDigest: digest })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      expect(this.download).toBe('server-r2.txt')
      expect(this.href).toBe('blob:export')
    })
    render(<ExportStage flow={flow()} />)
    await userEvent.click(screen.getByRole('button', { name: /download/i }))
    expect(getDownload).toHaveBeenCalledWith('one', 'v2')
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob)
    expect(click).toHaveBeenCalledOnce()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:export')
  })
  it('refuses a different snapshot digest and reports download initiation failure', async () => {
    getDownload.mockResolvedValue({ blob: new Blob(['wrong']), filename: 'wrong.txt', artifactDigest: 'wrong' })
    render(<ExportStage flow={flow()} />)
    await userEvent.click(screen.getByRole('button', { name: /download/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/match/i)
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    getDownload.mockResolvedValue({ blob: new Blob(['exact']), filename: 'exact.txt', artifactDigest: digest })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { throw new Error('Denied') })
    await userEvent.click(screen.getByRole('button', { name: /download/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not start/i)
    expect(URL.revokeObjectURL).toHaveBeenCalled()
  })
  it('does not expose copy or download for an unapproved or dirty version', () => {
    const state = flow()
    state.dirty = true
    render(<ExportStage flow={state} />)
    expect(screen.queryByRole('button', { name: /^copy$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /download/i })).not.toBeInTheDocument()
  })
})
