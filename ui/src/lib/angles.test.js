import { describe, it, expect } from 'vitest'
import { ANGLES, getAnglePill } from './angles'

describe('ANGLES', () => {
  it('lists the three editorial angles in order with id/label/desc', () => {
    expect(ANGLES.map((a) => a.id)).toEqual(['insightful', 'contrarian', 'question'])
    for (const angle of ANGLES) {
      expect(angle).toMatchObject({ id: expect.any(String), label: expect.any(String), desc: expect.any(String) })
    }
  })
})

describe('getAnglePill', () => {
  it('maps known angle keys to their display label', () => {
    expect(getAnglePill('insightful')).toBe('💡 Nuanced Insight')
    expect(getAnglePill('contrarian')).toBe('⚖️ Respectful Contrarian')
    expect(getAnglePill('question')).toBe('❓ Senior Question')
  })

  it('falls back to the raw key for unknown angles', () => {
    expect(getAnglePill('mystery_angle')).toBe('mystery_angle')
  })
})
