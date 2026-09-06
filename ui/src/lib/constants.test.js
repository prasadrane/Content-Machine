import { describe, it, expect } from 'vitest'
import { DIMENSION_LABELS, HUMANIZE_TONES, DISTRIBUTION_FORMATS, CORE_VOICE_INVARIANTS } from './constants'

describe('constants', () => {
  it('DIMENSION_LABELS maps score keys', () => {
    expect(DIMENSION_LABELS.lived_experience).toBe('Experience')
    expect(Object.keys(DIMENSION_LABELS)).toHaveLength(7)
  })
  it('HUMANIZE_TONES has 3 tone ids in order', () => {
    expect(HUMANIZE_TONES.map((t) => t.id)).toEqual(['punchy_direct', 'pragmatic_architect', 'conversational_peer'])
  })
  it('DISTRIBUTION_FORMATS has 5 format ids in order', () => {
    expect(DISTRIBUTION_FORMATS.map((f) => f.id)).toEqual(['linkedin', 'x_thread', 'video_script_short', 'video_script_long', 'newsletter'])
  })
  it('CORE_VOICE_INVARIANTS entries have title/summary/description', () => {
    expect(CORE_VOICE_INVARIANTS.length).toBe(5)
    for (const inv of CORE_VOICE_INVARIANTS) {
      expect(inv).toMatchObject({ title: expect.any(String), summary: expect.any(String), description: expect.any(String) })
    }
  })
})
