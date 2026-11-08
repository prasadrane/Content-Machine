import { describe, it, expect } from 'vitest'
import { formatTopicLabel } from './topics'

describe('formatTopicLabel', () => {
  it('passes through All and falsy', () => {
    expect(formatTopicLabel('All')).toBe('All')
    expect(formatTopicLabel('')).toBe('All')
  })
  it('keeps plain topic labels without adding decoration', () => {
    expect(formatTopicLabel('Systems Thinking')).toBe('Systems Thinking')
  })
  it('cleans legacy decorative prefixes without changing the underlying value', () => {
    expect(formatTopicLabel('🤖 AI')).toBe('AI')
    expect(formatTopicLabel('☁️ Cloud & Infrastructure')).toBe('Cloud & Infrastructure')
    expect(formatTopicLabel('🛠️ Developer Productivity')).toBe('Developer Productivity')
    expect(formatTopicLabel('💻 General Engineering')).toBe('General Engineering')
    expect(formatTopicLabel('Original 🎯 insight')).toBe('Original 🎯 insight')
  })
})
