import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import CandidateCard from './CandidateCard'
import ScanProgressHUD from './ScanProgressHUD'

const candidate = {
  title: 'Interesting idea',
  url: 'https://example.com/post',
  source: 'hn',
  body_snippet: 'A snippet body',
  topic_tag: 'AI & Machine Learning',
  verdict: 'pass',
  score: 8.1,
  dimension_scores: { novelty: 8, specificity: 7, lived_experience: 9, pov: 8, relevance: 7, rigor: 8 },
}

describe('CandidateCard', () => {
  it('renders title, snippet and verdict', () => {
    render(<CandidateCard candidate={candidate} onSendToCouncil={vi.fn()} onOpenInterview={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText('Interesting idea')).toBeInTheDocument()
    expect(screen.getByText(/a snippet body/i)).toBeInTheDocument()
    expect(screen.getByText(/pass/i)).toBeInTheDocument()
  })
})

describe('ScanProgressHUD', () => {
  it('renders phase stepper from progress object', () => {
    const progress = {
      phase: 'scoring',
      sourcesFetched: 10,
      sourcesTotal: 10,
      cachedSkipped: 8,
      total: 10,
      current: 5,
      passed: 3,
    }
    render(<ScanProgressHUD progress={progress} loading={true} onDismiss={vi.fn()} />)
    expect(screen.getByText(/scoring/i)).toBeInTheDocument()
  })
})
