import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import PlatformIcon from './PlatformIcon'
import { FORMATS, PLATFORMS, getPlatform } from '../../lib/platforms'

// Decorative pictographs only: labels are plain professional text.
const NO_EMOJI = /[\u{1F000}-\u{1FAFF}\u{2190}-\u{21FF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}]/u

describe('PlatformIcon', () => {
  it('renders a recognizable brand path for every brand platform', () => {
    for (const platform of ['linkedin', 'x', 'youtube', 'instagram']) {
      const { container, unmount } = render(<PlatformIcon platform={platform} />)
      const svg = container.querySelector('svg')
      expect(svg).not.toBeNull()
      expect(svg).toHaveAttribute('viewBox', '0 0 16 16')
      expect(svg).toHaveAttribute('fill', 'currentColor')
      expect(svg.querySelectorAll('path')).toHaveLength(1)
      expect(svg.querySelector('path').getAttribute('d')).toBeTruthy()
      unmount()
    }
  })

  it('renders neutral non-brand icons for newsletter and video', () => {
    for (const platform of ['newsletter', 'generic_video']) {
      const { container, unmount } = render(<PlatformIcon platform={platform} />)
      const svg = container.querySelector('svg')
      expect(svg).not.toBeNull()
      expect(svg).toHaveAttribute('aria-hidden', 'true')
      expect(svg).not.toHaveAttribute('viewBox', '0 0 16 16')
      unmount()
    }
  })

  it('falls back to a neutral icon for unknown identifiers', () => {
    for (const platform of [undefined, null, '', 'constructor', '__proto__', 'mastodon']) {
      const { container, unmount } = render(<PlatformIcon platform={platform} />)
      expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
      unmount()
    }
  })

  it('keeps one default size and honours explicit size and className', () => {
    const { container, rerender } = render(<PlatformIcon platform="linkedin" className="cm-icon" />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('width', '20')
    expect(svg).toHaveAttribute('height', '20')
    expect(svg).toHaveClass('cm-icon')

    rerender(<PlatformIcon platform="linkedin" size={16} className="size-4" />)
    const resized = container.querySelector('svg')
    expect(resized).toHaveAttribute('width', '16')
    expect(resized).toHaveAttribute('height', '16')
    expect(resized).toHaveClass('size-4')
  })

  it('is decorative and never announces status, account or readiness', () => {
    const { container } = render(<PlatformIcon platform="x" size={18} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-hidden', 'true')
    expect(svg).toHaveAttribute('focusable', 'false')
    expect(svg).not.toHaveAttribute('role')
    expect(svg.querySelector('title')).toBeNull()
    expect(container.textContent).toBe('')
  })

  it('pairs with a visible platform label as the accessible name', () => {
    for (const { id, label } of PLATFORMS) {
      const { container, unmount } = render(
        <button type="button">
          <PlatformIcon platform={id} size={18} />
          {label}
        </button>,
      )
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
      expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
      unmount()
    }
  })

  it('labels every retained platform and format without decorative emoji', () => {
    expect(PLATFORMS.length).toBeGreaterThan(0)
    expect(FORMATS.length).toBeGreaterThan(0)
    for (const { label } of [...PLATFORMS, ...FORMATS]) {
      expect(label).toBe(label.trim())
      expect(label).not.toMatch(NO_EMOJI)
    }
    for (const entry of FORMATS) {
      expect(getPlatform(entry.destination)?.label).toBeTruthy()
    }
  })

  it('exposes identity only, never inferred availability or publication', () => {
    for (const entry of PLATFORMS) {
      expect(Object.keys(entry).sort()).toEqual(['id', 'label'])
    }
    for (const entry of FORMATS) {
      expect(Object.keys(entry).sort()).toEqual(['destination', 'format', 'label'])
    }
  })
})
