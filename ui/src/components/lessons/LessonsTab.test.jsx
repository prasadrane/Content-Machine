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
  it('exposes named rule and comparison inputs', async () => {
    lessonsApi.getLessons.mockResolvedValue({ rules: [], pending: [] })
    render(<LessonsTab />)
    expect(screen.getByRole('textbox', { name: /declarative rule/i })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /original draft/i })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /published text/i })).toBeInTheDocument()
    await waitFor(() => expect(lessonsApi.getLessons).toHaveBeenCalled())
  })
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
