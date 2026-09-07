import { describe, it, expect } from 'vitest'
import { TABS } from './tabs'

describe('tab registry', () => {
  it('declares all 7 tabs in nav order', () => {
    expect(TABS.map((t) => t.id)).toEqual(['oracle', 'council', 'distribute', 'lessons', 'audio', 'commenting', 'profile'])
  })
  it('every entry has label + Component', () => {
    for (const t of TABS) {
      expect(typeof t.label).toBe('string')
      expect(typeof t.Component).toBe('function')
    }
  })
  it('commenting tab labeled Comments', () => {
    expect(TABS.find((t) => t.id === 'commenting').label).toBe('Comments')
  })
})
