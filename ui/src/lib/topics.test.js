import { describe, it, expect } from 'vitest'
import { formatTopicLabel } from './topics'

describe('formatTopicLabel', () => {
  it('passes through All and falsy', () => {
    expect(formatTopicLabel('All')).toBe('All')
    expect(formatTopicLabel('')).toBe('All')
  })
  it('prefixes emoji for Systems topic', () => {
    expect(formatTopicLabel('Systems Thinking')).toBe('⚡ Systems Thinking')
  })
  it('does not double-prefix already-emoji label', () => {
    expect(formatTopicLabel('🤖 AI')).toBe('🤖 AI')
  })
})
