import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AIWorkflowPanel from './AIWorkflowPanel'

const pair = { destination: 'linkedin', format: 'linkedin_post', can_generate: true, can_review: true }
const item = { item_id: 'one', destination: 'linkedin', format: 'linkedin_post', working_revision: 2,
  artifact: { segments: ['Original text'] } }
const proposal = { item_id: 'one', operation_id: 'op-1', kind: 'generate', state: 'completed',
  input_version_id: 'v2', editorial_snapshot: { version_id: 'v2', revision: 2, artifact: { segments: ['Original text'] } },
  result: { input_version_id: 'v2', artifact: { segments: ['  Suggested text\n'] } } }
function props(changes = {}) {
  return { item, pairs: [pair], capabilitiesLoading: false, capabilitiesError: '', dirty: false,
    busy: false, ai: { operation: null, proposal: null, activities: null }, aiIsCurrent: true,
    generateDraft: vi.fn(), requestReview: vi.fn(), checkAIStatus: vi.fn(), loadAIActivity: vi.fn(),
    showAIActivity: vi.fn(), acceptProposal: vi.fn(), acceptReviewProposal: vi.fn(), cancelProposal: vi.fn(),
    ...changes }
}
describe('AI drafting and review', () => {
  it('reflects server capabilities and keeps manual writing available', () => {
    render(<AIWorkflowPanel flow={props({ pairs: [{ ...pair, can_generate: false, can_review: false }] })} />)
    expect(screen.getByRole('button', { name: /create draft suggestion/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /request council review/i })).toBeDisabled()
    expect(screen.getByText(/write your draft yourself/i)).toBeInTheDocument()
  })
  it('compares the exact saved and suggested text with explicit acceptance and cancellation', async () => {
    const flow = props({ ai: { proposal, operation: proposal, activities: null } })
    render(<AIWorkflowPanel flow={flow} />)
    expect(screen.getByText('Original text')).toBeInTheDocument()
    expect(screen.getByText('Suggested text').textContent).toBe('  Suggested text\n')
    await userEvent.click(screen.getByRole('button', { name: /save this suggestion/i }))
    expect(flow.acceptProposal).toHaveBeenCalledOnce()
    await userEvent.click(screen.getByRole('button', { name: /discard suggestion/i }))
    expect(flow.cancelProposal).toHaveBeenCalledOnce()
  })
  it('refuses stale suggestions and names pending and failed outcomes accurately', () => {
    const { rerender } = render(<AIWorkflowPanel flow={props({ aiIsCurrent: false,
      ai: { proposal, operation: proposal, activities: null } })} />)
    expect(screen.getByRole('button', { name: /save this suggestion/i })).toBeDisabled()
    expect(screen.getByText(/earlier saved version/i)).toBeInTheDocument()
    const pending = { ...proposal, state: 'pending', result: null }
    rerender(<AIWorkflowPanel flow={props({ ai: { proposal: null,
      operation: pending, pending, activities: null } })} />)
    expect(screen.getByText(/AI drafting is pending/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /check status/i })).toBeInTheDocument()
    rerender(<AIWorkflowPanel flow={props({ ai: { proposal: null,
      operation: { ...proposal, state: 'failed', result: null }, activities: null } })} />)
    expect(screen.getByText(/AI drafting failed/i)).toBeInTheDocument()
  })
  it('keeps the pending request visible while viewing completed activity and resets confirmation for a different request', async () => {
    const pending = { ...proposal, operation_id: 'pending-1', kind: 'review', state: 'pending', result: null }
    const flow = props({ ai: { operation: proposal, proposal, pending, activities: [proposal, pending] }, abandonAI: vi.fn() })
    const { rerender } = render(<AIWorkflowPanel flow={flow} />)
    expect(screen.getByText(/Council review is pending/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create draft suggestion/i })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /close pending request/i }))
    expect(screen.getByRole('button', { name: /yes, close request/i })).toBeInTheDocument()
    const next = { ...pending, operation_id: 'pending-2' }
    rerender(<AIWorkflowPanel flow={{ ...flow, ai: { ...flow.ai, pending: next } }} />)
    expect(screen.queryByRole('button', { name: /yes, close request/i })).not.toBeInTheDocument()
    expect(flow.abandonAI).not.toHaveBeenCalled()
  })
  it('presents Council actions and lets the author accept a specific proposed segment', async () => {
    const operation = { ...proposal, kind: 'review', result: { review: {
      state: 'completed', actions: { required_actions: ['Explain the tradeoff'],
        notes: ['Wording suggestion unavailable. Your Council advice is preserved.'] },
      score_basis: { raw: { scale: [0, 10], composite: 7.4 }, normalized: null },
      proposals: [{ segment: 0, current: 'Original text', proposed: 'A clearer explanation', provenance: 'deterministic_cleanup' }],
    } } }
    const flow = props({ ai: { proposal: null, operation, activities: null } })
    render(<AIWorkflowPanel flow={flow} />)
    expect(screen.getByText('Explain the tradeoff')).toBeInTheDocument()
    expect(screen.getByText('Wording suggestion unavailable. Your Council advice is preserved.')).toBeInTheDocument()
    const comparison = screen.getByRole('group', { name: /suggestion for post 1/i })
    expect(within(comparison).getByText('Local cleanup suggestion')).toBeInTheDocument()
    expect(within(comparison).getByText('Original text')).toBeInTheDocument()
    expect(within(comparison).getByText('A clearer explanation')).toBeInTheDocument()
    await userEvent.click(within(comparison).getByRole('button', { name: /save this change/i }))
    expect(flow.acceptReviewProposal).toHaveBeenCalledWith(operation.result.review.proposals[0])
  })
})
