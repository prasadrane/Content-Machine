import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AnchorForm from './AnchorForm'

function props(overrides = {}) {
  return {
    anchorText: 'A draft grounded in the source.', onAnchorChange: vi.fn(),
    slug: 'draft-one', onSlugChange: vi.fn(),
    enabledFormats: { linkedin: true, x_thread: false }, onToggleFormat: vi.fn(),
    onOpenConfig: vi.fn(), humanize: false, onHumanizeToggle: vi.fn(),
    humanizeTone: 'pragmatic_architect', onToneChange: vi.fn(),
    loading: false, error: '', onSubmit: vi.fn(), activeFormatCount: 1,
    isApproved: false, ...overrides,
  }
}

describe('AnchorForm accessible controls and approval labels', () => {
  it('exposes native platform toggle buttons with their selected state', () => {
    const formProps = props()
    render(<AnchorForm {...formProps} />)
    const linkedIn = screen.getByRole('button', { name: 'LinkedIn', exact: true })
    const x = screen.getByRole('button', { name: 'X Thread', exact: true })
    expect(linkedIn.tagName).toBe('BUTTON')
    expect(linkedIn).toHaveAttribute('type', 'button')
    expect(linkedIn).toHaveAttribute('aria-pressed', 'true')
    expect(x).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(x)
    expect(formProps.onToggleFormat).toHaveBeenCalledWith('x_thread')
    expect(formProps.onSubmit).not.toHaveBeenCalled()
  })

  it('names the anchor and identifier fields and does not imply verification', () => {
    render(<AnchorForm {...props()} />)
    expect(screen.getByRole('textbox', { name: 'Anchor post' })).toHaveValue('A draft grounded in the source.')
    expect(screen.getByRole('textbox', { name: 'Post identifier' })).toHaveValue('draft-one')
    expect(screen.getByText('Needs approval')).toBeInTheDocument()
    expect(screen.queryByText(/verified/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /generate platform bundle/i })).toBeDisabled()
  })

  it('never defaults an unspecified approval to approved', () => {
    render(<AnchorForm {...props({ isApproved: undefined })} />)
    expect(screen.getByText('Needs approval')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /generate platform bundle/i })).toBeDisabled()
  })

  it('announces approval state and retains exact-text review confirmation', () => {
    const formProps = props({ reviewed: true, onApprove: vi.fn() })
    const { rerender } = render(<AnchorForm {...formProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'Approve this text' }))
    expect(formProps.onApprove).toHaveBeenCalledTimes(1)
    rerender(<AnchorForm {...props({ isApproved: true })} />)
    expect(screen.getByText('Approved by you')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Editing the text will require approval again.')
    expect(screen.getByRole('button', { name: /generate platform bundle/i })).toBeEnabled()
  })
})
