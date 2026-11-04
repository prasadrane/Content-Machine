import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RevisionComparison from './RevisionComparison'
import VerdictPanel from './VerdictPanel'

describe('revision comparison', () => {
  it('presents current and proposed text in reading order and changes nothing until accepted', () => {
    const onAccept = vi.fn()
    const onCancel = vi.fn()
    render(<RevisionComparison currentText="Current claim" proposedText="Proposed claim" onAccept={onAccept} onCancel={onCancel} />)
    expect(screen.getByRole('heading', { name: 'Current draft' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Proposed draft' })).toBeInTheDocument()
    expect(onAccept).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /keep current draft/i }))
    expect(onCancel).toHaveBeenCalledOnce()
    expect(onAccept).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /use proposed draft/i }))
    expect(onAccept).toHaveBeenCalledWith('Proposed claim')
  })

  it('requires comparing a revised result before replacing the editor', () => {
    const onLoadDraft = vi.fn()
    render(<VerdictPanel result={{ score: 8, verdict: 'pass', draft: 'Revision', actions: ['Clarify the source.'] }} draft="Current" onLoadDraft={onLoadDraft} />)
    fireEvent.click(screen.getByRole('button', { name: /compare revised draft/i }))
    expect(onLoadDraft).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /keep current draft/i }))
    expect(onLoadDraft).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /compare revised draft/i }))
    fireEvent.click(screen.getByRole('button', { name: /use proposed draft/i }))
    expect(onLoadDraft).toHaveBeenCalledWith('Revision')
  })

  it('does not attach an earlier verdict to changed current text', () => {
    const onRequestApproval = vi.fn()
    render(<VerdictPanel result={{ score: 9, verdict: 'pass', draft: 'Reviewed', reviewInput: { text: 'Original', slug: 'story' } }} draft="New claim" spikeId="story" onRequestApproval={onRequestApproval} />)
    fireEvent.click(screen.getByRole('button', { name: /approve & distribute/i }))
    expect(onRequestApproval).toHaveBeenCalledWith('New claim', { verdict: 'unreviewed' })
    expect(screen.getByText(/not a factual verification/i)).toBeInTheDocument()
  })
  it('dismisses a comparison if the author edits before accepting', () => {
    const onLoadDraft = vi.fn()
    const props = { result: { score: 8, verdict: 'pass', draft: 'Revision' }, draft: 'Current', spikeId: 'story', onLoadDraft }
    const { rerender } = render(<VerdictPanel {...props} />)
    fireEvent.click(screen.getByRole('button', { name: /compare revised draft/i }))
    rerender(<VerdictPanel {...props} draft="Newer author edit" />)
    expect(screen.queryByRole('button', { name: /use proposed draft/i })).not.toBeInTheDocument()
    expect(onLoadDraft).not.toHaveBeenCalled()
  })
})
