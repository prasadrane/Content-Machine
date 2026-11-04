import { describe, it, expect } from 'vitest'
import { parseSources, toggleSource, validateSources } from './sourceInputs'
import { selectedSetFrom } from './PresetEditorPane'

describe('source inputs', () => {
  it('handles real and legacy literal line endings together', () => {
    expect(parseSources(' one\r\ntwo\\nthree\n\n')).toEqual(['one', 'two', 'three'])
    expect([...selectedSetFrom('one\\ntwo')]).toEqual(['one', 'two'])
  })
  it('removes a selected legacy preset and normalizes remaining lines', () => {
    expect(toggleSource('one\\ntwo', 'one')).toBe('two')
    expect(toggleSource('one\\ntwo', 'three')).toBe('one\ntwo\nthree')
  })
  it('allows supported LinkedIn handles and profile URLs', () => {
    expect(validateSources([], ['owner/repo'], ['satyanadella', 'in/satyanadella', 'company/cloudflare', 'https://www.linkedin.com/in/satyanadella/'])).toBe('')
  })
  it('rejects unsupported feed schemes and LinkedIn destinations', () => {
    expect(validateSources(['file:///secret'], [], [])).toMatch(/RSS feed 1/)
    expect(validateSources([], [], ['https://example.com/in/person'])).toMatch(/LinkedIn profile 1/)
  })
})
