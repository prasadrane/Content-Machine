// Accept pasted lines and legacy saved inputs that contain literal "\\n" separators.
export function parseSources(text = '') {
  return text.split(/\\n|\r?\n/).map(value => value.trim()).filter(Boolean)
}

export function toggleSource(text, value) {
  const current = parseSources(text)
  return (current.includes(value) ? current.filter(item => item !== value) : [...current, value]).join('\n')
}

function isWebUrl(value) {
  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) && Boolean(url.hostname) && !url.username && !url.password
  } catch {
    return false
  }
}

function isLinkedInTarget(value) {
  if (/^(?:in\/|company\/)?[\w-]+\/?$/.test(value)) return true
  if (!isWebUrl(value)) return false
  const url = new URL(value)
  return /(^|\.)linkedin\.com$/i.test(url.hostname) && /^\/(in|company)\/[^/]+(?:\/.*)?$/.test(url.pathname)
}

export function validateSources(feeds, repos, profiles) {
  const badFeed = feeds.findIndex(value => !isWebUrl(value))
  if (badFeed >= 0) return `RSS feed ${badFeed + 1}: enter a valid http or https URL.`
  const badRepo = repos.findIndex(value => !/^[\w.-]+\/[\w.-]+$/.test(value))
  if (badRepo >= 0) return `GitHub repository ${badRepo + 1}: use owner/repo, for example facebook/react.`
  const badProfile = profiles.findIndex(value => !isLinkedInTarget(value))
  return badProfile >= 0 ? `LinkedIn profile ${badProfile + 1}: use a handle, in/slug, company/slug, or LinkedIn profile URL.` : ''
}
