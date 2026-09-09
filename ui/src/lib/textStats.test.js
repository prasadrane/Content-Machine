import { describe, it, expect } from 'vitest'
import { countSentences } from './textStats'

describe('countSentences', () => {
  it('returns 0 for empty, whitespace-only, null and undefined', () => {
    expect(countSentences('')).toBe(0)
    expect(countSentences('   ')).toBe(0)
    expect(countSentences(null)).toBe(0)
    expect(countSentences(undefined)).toBe(0)
  })

  it('counts a lone terminator-free fragment as 1', () => {
    expect(countSentences('Hello world')).toBe(1)
  })

  it('counts multiple terminated sentences', () => {
    expect(countSentences('One. Two. Three.')).toBe(3)
  })

  it('ignores a trailing fragment with no terminator', () => {
    expect(countSentences('One. Two. Three')).toBe(2)
  })

  it('recognizes ? and ! as terminators', () => {
    expect(countSentences('Hi! How are you?')).toBe(2)
  })
})
