// Editorial angle definitions and their pill labels.
export const ANGLES = [
  {
    id: 'insightful',
    label: '💡 Nuanced Insight',
    desc: 'Adds a deeper dimension, nuance, or underlying operational mechanism.',
  },
  {
    id: 'contrarian',
    label: '⚖️ Respectful Contrarian',
    desc: 'Respectfully challenges assumptions with practical production experience.',
  },
  {
    id: 'question',
    label: '❓ Senior Question',
    desc: 'Poses an incisive, senior-level question that advances the discussion.',
  },
]

export function getAnglePill(angleKey) {
  switch (angleKey) {
    case 'insightful':
      return '💡 Nuanced Insight'
    case 'contrarian':
      return '⚖️ Respectful Contrarian'
    case 'question':
      return '❓ Senior Question'
    default:
      return angleKey
  }
}
