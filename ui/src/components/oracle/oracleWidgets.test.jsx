import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import CandidateCard from './CandidateCard'
import ScanProgressHUD from './ScanProgressHUD'
import ArchiveView from './ArchiveView'
import TriageToolbar from './TriageToolbar'
import { DEFAULT_AVAILABLE_TOPICS } from './presets'

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
  it('displays historical topics without their decorative prefix', () => {
    render(<CandidateCard candidate={{ ...candidate, topic_tag: '🤖 AI & Machine Learning' }} onSendToCouncil={vi.fn()} onOpenInterview={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText('AI & Machine Learning')).toBeInTheDocument()
  })
})

describe('topic filters', () => {
  it('shows plain default category labels', () => {
    expect(DEFAULT_AVAILABLE_TOPICS).toContain('Systems & Architecture')
    expect(DEFAULT_AVAILABLE_TOPICS).toContain('Engineering Leadership')
    expect(DEFAULT_AVAILABLE_TOPICS).toContain('AI & Machine Learning')
    expect(DEFAULT_AVAILABLE_TOPICS).toContain('Cloud & Infrastructure')
  })

  it('preserves the stored topic when a plain-looking archive filter is selected', () => {
    const select = vi.fn()
    render(<ArchiveView archiveSearch="" setArchiveSearch={vi.fn()} archiveVerdict="All" setArchiveVerdict={vi.fn()} archiveTopic="All" setArchiveTopic={select} availableTopics={['All', '🤖 AI & Machine Learning']} archiveItems={[{ id: 1, title: 'Saved idea', source: 'rss', topic_tag: '🤖 AI & Machine Learning' }]} archiveTotal={1} archiveLoading={false} fetchArchive={vi.fn()} onOpenInterview={vi.fn()} />)
    const filter = screen.getByRole('button', { name: /AI & Machine Learning/ })
    expect(filter.textContent).not.toContain('🤖')
    expect(filter).toHaveTextContent('1')
    expect(screen.getByText('AI & Machine Learning', { selector: 'span.cm-badge' })).toBeInTheDocument()
    filter.click()
    expect(select).toHaveBeenCalledWith('🤖 AI & Machine Learning')
  })

  it('keeps the raw topic identity for active-batch filtering', () => {
    const select = vi.fn()
    render(<TriageToolbar batchSearch="" setBatchSearch={vi.fn()} batchSort="score" setBatchSort={vi.fn()} batchTopic="All" setBatchTopic={select} batchTopics={['All', '☁️ Cloud & Infrastructure']} candidates={[{ topic_tag: '☁️ Cloud & Infrastructure' }]} />)
    const filter = screen.getByRole('button', { name: /Cloud & Infrastructure/ })
    expect(filter.textContent).not.toContain('☁')
    expect(filter).toHaveTextContent('1')
    filter.click()
    expect(select).toHaveBeenCalledWith('☁️ Cloud & Infrastructure')
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
