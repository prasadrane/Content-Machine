import { render, screen, fireEvent } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import PlatformConfigModal from './PlatformConfigModal'

it('names its dialog and lets keyboard users change formats and dismiss it', () => {
  const onToggleFormat = vi.fn()
  const onClose = vi.fn()
  render(<PlatformConfigModal show onClose={onClose} enabledFormats={{ linkedin: true }} onToggleFormat={onToggleFormat} onSelectAll={vi.fn()} onResetDefaults={vi.fn()} />)
  const dialog = screen.getByRole('dialog', { name: /platform distribution formats/i })
  const format = screen.getByRole('checkbox', { name: /linkedin/i })
  fireEvent.click(format)
  expect(onToggleFormat).toHaveBeenCalledWith('linkedin')
  fireEvent.keyDown(dialog, { key: 'Escape' })
  expect(onClose).toHaveBeenCalledOnce()
})
