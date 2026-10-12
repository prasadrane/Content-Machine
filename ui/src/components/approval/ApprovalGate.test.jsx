import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ApprovalGate from './ApprovalGate'

describe('ApprovalGate', () => {
  it('requires the read-and-approve checkbox before confirming', () => {
    const onConfirm = vi.fn()
    render(<ApprovalGate text="Final draft" verdict="pass" score={9.3} onConfirm={onConfirm} onCancel={vi.fn()} />)
    const btn = screen.getByRole('button', { name: /approve & send/i })
    expect(btn).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    expect(btn).toBeEnabled()
    fireEvent.click(btn)
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('flags an override when the council did not pass the draft', () => {
    render(<ApprovalGate text="Draft" verdict="revise" score={7.1} onConfirm={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.getByText(/overrides the judges/i)).toBeInTheDocument()
  })

  it('shows no override warning for a passing draft', () => {
    render(<ApprovalGate text="Draft" verdict="pass" score={9.3} onConfirm={vi.fn()} onCancel={vi.fn()} />)
    expect(screen.queryByText(/overrides the judges/i)).toBeNull()
  })
})
