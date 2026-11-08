// Identity and labels only. Availability is supplied by the server capabilities.
export const PLATFORMS = [
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'x', label: 'X' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'newsletter', label: 'Newsletter' },
  { id: 'generic_video', label: 'Video' },
]

export const FORMATS = [
  { destination: 'linkedin', format: 'linkedin_post', label: 'LinkedIn post' },
  { destination: 'x', format: 'x_thread', label: 'X thread' },
  { destination: 'youtube', format: 'youtube_short_script', label: 'YouTube Shorts script' },
  { destination: 'youtube', format: 'youtube_long_script', label: 'YouTube video script' },
  { destination: 'instagram', format: 'instagram_caption', label: 'Instagram caption' },
  { destination: 'instagram', format: 'instagram_reel_script', label: 'Instagram Reel script' },
  { destination: 'newsletter', format: 'newsletter_draft', label: 'Newsletter draft' },
  { destination: 'generic_video', format: 'generic_short_video_script', label: 'Short video script' },
]

const LEGACY_FORMATS = {
  linkedin: ['linkedin', 'linkedin_post'],
  x_thread: ['x', 'x_thread'],
  video_script_long: ['youtube', 'youtube_long_script'],
  video_script_short: ['generic_video', 'generic_short_video_script'],
  video_script: ['generic_video', 'generic_short_video_script'],
  newsletter: ['newsletter', 'newsletter_draft'],
}

export function getPlatform(id) {
  return PLATFORMS.find(platform => platform.id === id)
}

export function getFormat(destination, format) {
  return FORMATS.find(entry => entry.destination === destination && entry.format === format)
}

export function resolveLegacyFormat(legacyFormat, destination) {
  if (!Object.hasOwn(LEGACY_FORMATS, legacyFormat)) return undefined
  const pair = LEGACY_FORMATS[legacyFormat]
  if (destination != null && destination !== pair[0]) return undefined
  return [...pair]
}
