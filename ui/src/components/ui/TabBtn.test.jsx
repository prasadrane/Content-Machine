import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TabBtn from './TabBtn'

describe('TabBtn', () => {
  it('renders label and fires onClick', async () => {
    const onClick = vi.fn()
    render(<TabBtn active={false} onClick={onClick} label="Oracle" />)
    await userEvent.click(screen.getByRole('button', { name: /oracle/i }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
