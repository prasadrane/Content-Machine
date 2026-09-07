import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import DistributeTab from './DistributeTab'
import * as distributeApi from '../../api/distribute'

vi.mock('../../api/distribute', () => ({ runDistribute: vi.fn() }))

describe('DistributeTab', () => {
  it('seeds anchor text and slug from props', () => {
    render(<DistributeTab initialText="Seeded draft" initialSlug="my-post" />)
    expect(screen.getByDisplayValue('Seeded draft')).toBeInTheDocument()
  })
  it('renders all five format chips', () => {
    render(<DistributeTab initialText="" initialSlug="" />)
    expect(screen.getByText('LinkedIn')).toBeInTheDocument()
    expect(screen.getByText('Newsletter')).toBeInTheDocument()
  })
})
