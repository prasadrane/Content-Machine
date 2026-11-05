import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AudioTab from './AudioTab'

describe('AudioTab', () => {
  it('exposes named transcription controls and updates the model command', () => {
    render(<AudioTab />)
    fireEvent.change(screen.getByRole('textbox', { name: /audio file path/i }), { target: { value: 'recording.wav' } })
    fireEvent.change(screen.getByRole('combobox', { name: /model size/i }), { target: { value: 'base' } })
    expect(screen.getByRole('textbox', { name: /audio file path/i })).toHaveValue('recording.wav')
    expect(screen.getByText(/--model base/)).toBeInTheDocument()
  })
  it('renders without crashing', () => {
    const { container } = render(<AudioTab />)
    expect(container.textContent.length).toBeGreaterThan(0)
  })
})
