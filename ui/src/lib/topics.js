export function getTopicBadgeClass(topic) {
  if (!topic) return 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc]'
  if (topic.includes('Systems')) return 'bg-[#e3dacc]/80 text-[#87867f] border-[#b0aea5]'
  if (topic.includes('Leadership')) return 'bg-[#f0eee6] text-[#141413] border-[#e3dacc]'
  if (topic.includes('AI') || topic.includes('Machine Learning')) return 'bg-[#c6613f]/10 text-[#c6613f] border-[#c6613f]/30'
  if (topic.includes('Cloud') || topic.includes('Infra')) return 'bg-[#d97757]/10 text-[#d97757] border-[#d97757]/30'
  if (topic.includes('Security')) return 'bg-rose-500/10 text-rose-800 border-rose-200'
  if (topic.includes('Productivity') || topic.includes('Tools')) return 'bg-emerald-500/10 text-emerald-800 border-emerald-200'
  return 'bg-[#f0eee6] text-[#87867f] border-[#e3dacc]'
}

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
