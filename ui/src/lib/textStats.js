// Sentence-counting helper shared by commenting UI cards.
export function countSentences(text) {
  if (!text || !text.trim()) return 0
  const matches = text.trim().match(/[^.!?]+[.!?]+(\s|$)/g)
  if (matches) return matches.length
  return text.trim().length > 0 ? 1 : 0
}
