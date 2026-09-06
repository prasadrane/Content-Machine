import { describe, it, expect } from 'vitest'
import { getTopicBadgeClass, formatTopicLabel } from './topics'

describe('getTopicBadgeClass', () => {
  it('muted style for empty topic', () => {
    expect(getTopicBadgeClass('')).toBe('bg-[#f0eee6] text-[#87867f] border-[#e3dacc]')
  })
  it('clay style for AI topic', () => {
    expect(getTopicBadgeClass('AI & Machine Learning')).toBe('bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30')
  })
  it('rose style for Security topic', () => {
    expect(getTopicBadgeClass('Security')).toContain('text-rose-800')
  })
})

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
