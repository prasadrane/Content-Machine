import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import LessonsTab from './LessonsTab'
import * as lessonsApi from '../../api/lessons'

vi.mock('../../api/lessons', () => ({
  getLessons: vi.fn(),
  addCustomLesson: vi.fn(),
  diffLessons: vi.fn(),
  approveLesson: vi.fn(),
  rejectLesson: vi.fn(),
}))

describe('LessonsTab', () => {
  it('loads lessons on mount and lists active rules', async () => {
    lessonsApi.getLessons.mockResolvedValue({
      rules: [{ id: 'r1', rule_text: 'Never use buzzwords' }],
      pending: [{ id: 'r2', rule_text: 'Prefer short sentences' }],
    })
    render(<LessonsTab />)
    await waitFor(() => expect(lessonsApi.getLessons).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/never use buzzwords/i)).toBeInTheDocument()
  })
})
