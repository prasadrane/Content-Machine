import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import PlatformIcon from '../components/ui/PlatformIcon'
import { FORMATS, PLATFORMS, getFormat, getPlatform, resolveLegacyFormat } from './platforms'

describe('workflow platform identities', () => {
  it('covers every canonical destination and format once', () => {
    expect(FORMATS.map(({ destination, format }) => `${destination}/${format}`)).toEqual([
      'linkedin/linkedin_post',
      'x/x_thread',
      'youtube/youtube_short_script',
      'youtube/youtube_long_script',
      'instagram/instagram_caption',
      'instagram/instagram_reel_script',
      'newsletter/newsletter_draft',
      'generic_video/generic_short_video_script',
    ])
    expect(new Set(FORMATS.map(({ destination, format }) => `${destination}/${format}`)).size)
      .toBe(FORMATS.length)
    expect(new Set(PLATFORMS.map(({ id }) => id)).size).toBe(PLATFORMS.length)
    for (const entry of FORMATS) {
      expect(getPlatform(entry.destination)?.label).toBeTruthy()
      expect(getFormat(entry.destination, entry.format)).toEqual(entry)
      expect(entry.label).toBeTruthy()
      expect(entry).not.toHaveProperty('canGenerate')
      expect(entry).not.toHaveProperty('can_generate')
    }
    expect(getFormat('instagram', 'youtube_short_script')).toBeUndefined()
    expect(getPlatform('unknown')).toBeUndefined()
  })

  it.each([
    ['linkedin', ['linkedin', 'linkedin_post']],
    ['x_thread', ['x', 'x_thread']],
    ['video_script_long', ['youtube', 'youtube_long_script']],
    ['video_script_short', ['generic_video', 'generic_short_video_script']],
    ['video_script', ['generic_video', 'generic_short_video_script']],
    ['newsletter', ['newsletter', 'newsletter_draft']],
  ])('maps retained legacy format %s without guessing', (legacy, pair) => {
    expect(resolveLegacyFormat(legacy)).toEqual(pair)
    expect(resolveLegacyFormat(legacy, pair[0])).toEqual(pair)
    expect(resolveLegacyFormat(legacy, 'unknown')).toBeUndefined()
  })

  it('returns no identity for unknown legacy formats', () => {
    expect(resolveLegacyFormat('unrecognized')).toBeUndefined()
    expect(resolveLegacyFormat('__proto__')).toBeUndefined()
    expect(resolveLegacyFormat('constructor')).toBeUndefined()
  })

  it.each(PLATFORMS.map(({ id }) => [id]))('renders %s as a decorative icon alongside a readable label', platform => {
    const label = getPlatform(platform).label
    const { container } = render(React.createElement('button', {},
      React.createElement(PlatformIcon, { platform, size: 18 }), label))
    expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    const icon = container.querySelector('svg')
    expect(icon).toHaveAttribute('aria-hidden', 'true')
    expect(icon).toHaveAttribute('width', '18')
    expect(icon).toHaveAttribute('height', '18')
    expect(icon.querySelector('path')).not.toBeNull()
  })

  it('renders a generic icon for unknown platform identifiers', () => {
    const { container } = render(React.createElement(PlatformIcon, { platform: 'constructor' }))
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })
})
