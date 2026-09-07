import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import CommentingTab from './CommentingTab'
import * as commentsApi from '../../api/comments'

vi.mock('../../api/comments', () => ({
  generateComments: vi.fn(),
  getCommentsHistory: vi.fn(),
}))

describe('CommentingTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches history on mount and renders it', async () => {
    commentsApi.getCommentsHistory.mockResolvedValue({
      items: [{ id: 'c1', post_content: 'Some post', final_comment: 'Great take', verdict: 'PASS', created_at: '2026-09-06' }],
    })
    render(<CommentingTab />)
    await waitFor(() => expect(commentsApi.getCommentsHistory).toHaveBeenCalledWith(50))
    expect(await screen.findByText(/great take/i)).toBeInTheDocument()
  })

  it('renders angle selector with default insightful', async () => {
    commentsApi.getCommentsHistory.mockResolvedValue({ items: [] })
    render(<CommentingTab />)
    expect(await screen.findByText(/insightful/i)).toBeInTheDocument()
  })

  it('generates a comment and displays PolishCard', async () => {
    commentsApi.getCommentsHistory.mockResolvedValue({ items: [] })
    commentsApi.generateComments.mockResolvedValue({
      peak_score: 9.1,
      verdict: 'publish',
      final_comment: 'This is a high quality polished comment.',
      iteration: 2,
      humanized: true,
      burstiness_score: 8.5,
      judge_scores: { perell: 9.0, puri: 9.2 },
      judge_critiques: { perell: 'Great hook' },
      actions: ['Sharpen the contrast'],
    })

    render(<CommentingTab />)
    const textarea = screen.getByPlaceholderText(/paste the linkedin post content/i)
    fireEvent.change(textarea, { target: { value: 'This is a long enough post to comment on.' } })

    const generateBtn = screen.getByRole('button', { name: /run council round & generate comment/i })
    fireEvent.click(generateBtn)

    expect(await screen.findByText(/this is a high quality polished comment\./i)).toBeInTheDocument()
    expect(screen.getByText(/9\.1 \/ 10 • PASSED COUNCIL/i)).toBeInTheDocument()
    expect(screen.getByText(/Sharpen the contrast/i)).toBeInTheDocument()
  })

  it('populates editor when clicking Use in Editor from history', async () => {
    commentsApi.getCommentsHistory.mockResolvedValue({
      items: [{
        id: 'c1',
        post_content: 'Original post to review',
        final_comment: 'Previous comment',
        angle: 'contrarian',
        verdict: 'PASS',
        created_at: '2026-09-06',
      }],
    })

    render(<CommentingTab />)
    const useBtn = await screen.findByRole('button', { name: /use in editor/i })
    fireEvent.click(useBtn)

    const textarea = screen.getByPlaceholderText(/paste the linkedin post content/i)
    expect(textarea.value).toBe('Original post to review')
  })
})
