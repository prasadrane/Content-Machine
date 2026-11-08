import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import HumanizedDraftCard from './HumanizedDraftCard'

describe('HumanizedDraftCard', () => {
  it('shows a plain label and preserves the generated draft exactly', () => {
    const result = { humanized_text: 'Example text 🎯 from the author', burstiness_score: 3.2 }
    render(<HumanizedDraftCard humanizedResult={result} onUseInEditor={vi.fn()} onCopy={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText('Wording suggestion')).toBeInTheDocument()
    expect(screen.queryByText(/burstiness|authenticity verified/i)).not.toBeInTheDocument()
    expect(screen.getByText(result.humanized_text)).toBeInTheDocument()
  })
  it.each([['model_rewrite', 'Model wording suggestion'], ['deterministic_cleanup', 'Local text cleanup']])(
    'identifies %s provenance without automatically replacing the draft', (provenance, label) => {
      const use = vi.fn()
      render(<HumanizedDraftCard humanizedResult={{ humanized_text: 'Proposed text', provenance }}
        onUseInEditor={use} onCopy={vi.fn()} onDismiss={vi.fn()} />)
      expect(screen.getByText(label)).toBeInTheDocument()
      expect(use).not.toHaveBeenCalled()
    })
})
