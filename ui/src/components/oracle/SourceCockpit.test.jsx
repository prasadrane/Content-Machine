import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SourceCockpit from './SourceCockpit'

describe('SourceCockpit Presets selection state', () => {
  it('highlights selected RSS presets and toggles them off when clicked', () => {
    const setRssUrls = vi.fn()
    const selectedUrl = 'https://www.reddit.com/r/ExperiencedDevs/top/.rss?t=week'

    render(
      <SourceCockpit
        sourceSubTab="rss"
        onSubTabChange={vi.fn()}
        rssUrls={selectedUrl}
        setRssUrls={setRssUrls}
        githubRepos=""
        setGithubRepos={vi.fn()}
        linkedInProfiles=""
        setLinkedInProfiles={vi.fn()}
        linkedInLiAt=""
        setLinkedInLiAt={vi.fn()}
        maxAgeDays="10"
        setMaxAgeDays={vi.fn()}
        maxItemsPerFeed="25"
        setMaxItemsPerFeed={vi.fn()}
        rssCount={1}
        ghCount={0}
        liCount={0}
        totalSources={1}
        onRun={vi.fn()}
        loading={false}
        error=""
        linkedInStatus={{ session_valid: false }}
        syncingLinkedIn={false}
        syncMsg=""
        onSyncLinkedIn={vi.fn()}
      />
    )

    // The selected preset uses a decorative icon and exposes its state.
    const selectedBtn = screen.getByRole('button', { name: /r\/ExperiencedDevs/i })
    expect(selectedBtn.querySelector('svg.lucide-check')).toHaveAttribute('aria-hidden', 'true')
    expect(selectedBtn).toHaveAttribute('aria-pressed', 'true')

    // An unselected preset uses the matching add icon.
    const unselectedBtn = screen.getByRole('button', { name: /r\/LocalLLaMA/i })
    expect(unselectedBtn.querySelector('svg.lucide-plus')).toHaveAttribute('aria-hidden', 'true')

    // Clicking the selected preset should toggle it off
    fireEvent.click(selectedBtn)
    expect(setRssUrls).toHaveBeenCalledWith('')

    // Clicking an unselected preset should add it
    fireEvent.click(unselectedBtn)
    expect(setRssUrls).toHaveBeenCalled()
  })

  it('highlights selected GitHub presets and toggles them', () => {
    const setGithubRepos = vi.fn()
    render(
      <SourceCockpit
        sourceSubTab="github"
        onSubTabChange={vi.fn()}
        rssUrls=""
        setRssUrls={vi.fn()}
        githubRepos="facebook/react"
        setGithubRepos={setGithubRepos}
        linkedInProfiles=""
        setLinkedInProfiles={vi.fn()}
        linkedInLiAt=""
        setLinkedInLiAt={vi.fn()}
        maxAgeDays="10"
        setMaxAgeDays={vi.fn()}
        maxItemsPerFeed="25"
        setMaxItemsPerFeed={vi.fn()}
        rssCount={0}
        ghCount={1}
        liCount={0}
        totalSources={1}
        onRun={vi.fn()}
        loading={false}
        error=""
        linkedInStatus={{ session_valid: false }}
        syncingLinkedIn={false}
        syncMsg=""
        onSyncLinkedIn={vi.fn()}
      />
    )

    const ghBtn = screen.getByRole('button', { name: /facebook\/react/i })
    expect(ghBtn.querySelector('svg.lucide-check')).toHaveAttribute('aria-hidden', 'true')
    expect(ghBtn).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(ghBtn)
    expect(setGithubRepos).toHaveBeenCalledWith('')
  })
})
