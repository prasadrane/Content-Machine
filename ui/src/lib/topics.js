export function formatTopicLabel(topic) {
  if (!topic || topic === 'All') return 'All'
  // Older saved topics can include decorative emoji. Keep the stored value for
  // queries and comparisons, but use a plain label wherever it is displayed.
  return topic.replace(/^(?:\p{Extended_Pictographic}[\uFE0F\u200D]*\s*)+/u, '') || 'Topic'
}
