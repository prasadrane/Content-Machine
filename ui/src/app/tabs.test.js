import { describe, it, expect } from 'vitest'
import { TABS } from './tabs'

describe('tab registry', () => {
  it('exposes workflow, lessons and settings in nav order', () => {
    expect(TABS.map((t) => t.id)).toEqual(['workflow', 'lessons', 'settings'])
  })
  it('every entry has label + Component', () => {
    for (const t of TABS) {
      expect(typeof t.label).toBe('string')
      expect(typeof t.Component).toBe('function')
    }
  })
  it('does not expose the retired comments feature', () => {
    expect(TABS.some((t) => t.id === 'commenting' || t.label === 'Comments')).toBe(false)
  })
})
