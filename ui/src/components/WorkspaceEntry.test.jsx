import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import WorkspaceEntry from './WorkspaceEntry'

test('offers direct tasks without resetting work or requiring an interview', () => {
  const onNavigate = vi.fn()
  const onSample = vi.fn()
  render(<WorkspaceEntry onNavigate={onNavigate} onSample={onSample} />)
  expect(screen.getByText(/engineering sources and your experience/i)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /review a draft/i }))
  expect(onNavigate).toHaveBeenLastCalledWith('council')
  fireEvent.click(screen.getByRole('button', { name: /adapt an anchor/i }))
  expect(onNavigate).toHaveBeenLastCalledWith('distribute')
  fireEvent.click(screen.getByRole('button', { name: /explore a completed example/i }))
  expect(onSample).toHaveBeenCalledOnce()
})
