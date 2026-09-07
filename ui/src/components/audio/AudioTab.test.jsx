import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import AudioTab from './AudioTab'

describe('AudioTab', () => {
  it('renders without crashing', () => {
    const { container } = render(<AudioTab />)
    expect(container.textContent.length).toBeGreaterThan(0)
  })
})
