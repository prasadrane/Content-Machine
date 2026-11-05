export function formatTopicLabel(topic) {
  if (!topic || topic === 'All') return 'All'
  if (topic.includes('⚡') || topic.includes('🤖') || topic.includes('📈') || topic.includes('☁️') || topic.includes('🔒') || topic.includes('🛠️') || topic.includes('💻')) {
    return topic
  }
  if (topic.includes('Systems')) return `⚡ ${topic}`
  if (topic.includes('AI') || topic.includes('Machine Learning')) return `🤖 ${topic}`
  if (topic.includes('Leadership')) return `📈 ${topic}`
  if (topic.includes('Cloud') || topic.includes('Infra')) return `☁️ ${topic}`
  if (topic.includes('Security')) return `🔒 ${topic}`
  if (topic.includes('Productivity') || topic.includes('Tools')) return `🛠️ ${topic}`
  return topic
}
