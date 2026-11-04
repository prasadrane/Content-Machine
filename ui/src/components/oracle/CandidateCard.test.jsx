import { expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import CandidateCard from './CandidateCard'

it('prioritizes author perspective while retaining direct draft entry and source context', () => {
  const candidate = { title: 'A deployment lesson', source: 'Engineering feed', published_at: '2026-11-01T12:00:00Z', body_snippet: 'A source excerpt', score: 8.9, verdict: 'pass' }
  const interview = vi.fn(), draft = vi.fn()
  render(<CandidateCard candidate={candidate} onOpenInterview={interview} onSendToCouncil={draft} onDismiss={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Add my perspective' }))
  expect(interview).toHaveBeenCalledWith(candidate)
  fireEvent.click(screen.getByRole('button', { name: 'Review a draft' }))
  expect(draft).toHaveBeenCalledWith(candidate)
  expect(screen.getByText('Engineering feed')).toBeVisible()
  expect(screen.getByText('A source excerpt')).toBeVisible()
})
