import { webcrypto } from 'node:crypto'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { artifactDigest, formatLabel } from './workflowUtils'
import { FORMATS } from '../../lib/platforms'

const makeItem = (destination, format, segments, changes = {}) => ({
  item_id: 'item-1',
  owner_id: 'owner-1',
  title: 'Indexing',
  destination,
  format,
  stage: 'draft_review',
  working_revision: 2,
  context: { notes: 'not part of the digest' },
  artifact: { segments },
  ...changes,
})

beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto)
})

// Expected values come from the backend's artifact_digest over
// canonical_json (sort_keys, (",", ":"), ensure_ascii=False). The first three
// are the R00 reviewer vectors that independently compared both runtimes.
describe('artifactDigest', () => {
  it.each([
    [
      'Unicode, CRLF and trailing whitespace',
      'linkedin',
      'linkedin_post',
      [' leading\r\ncaf\u00e9 \u{1f600}  \n'],
      'sha256:e205134440552aadaa4d9bb1b62b9f9765edfe3e1087a39be0f5089c8e0dcc94',
    ],
    [
      'ordered thread segments',
      'x',
      'x_thread',
      ['one\n', 'two\r\n '],
      'sha256:c9dd1c42fda290e9a5fda4b854fb412c4d5ecbd2311921d3810de1a903a5ce62',
    ],
    [
      'quotes and a U+2028 separator',
      'instagram',
      'instagram_caption',
      ['quoted " / \u2028'],
      'sha256:cea53bfd83032ae031f7dd05f402beb271f6be25b9fa08c8eb065757e72ea596',
    ],
  ])('matches the backend for %s', async (_name, destination, format, segments, expected) => {
    await expect(artifactDigest(makeItem(destination, format, segments))).resolves.toBe(expected)
  })

  it('depends on segment order for a thread', async () => {
    const ordered = [' first \r\n', 'second  ', '"third"']
    const reversed = [...ordered].reverse()
    await expect(artifactDigest(makeItem('x', 'x_thread', ordered)))
      .resolves.toBe('sha256:390238f2d860e2bf508e188f6e85549980fc0b27d7c6412081ad4ffe3526cc4c')
    await expect(artifactDigest(makeItem('x', 'x_thread', reversed)))
      .resolves.toBe('sha256:21f4c2e40c6e750cf032b02f0120b8990fa3afe483b5e9b66eff459a703e14eb')
  })

  it('depends on segment boundaries even when the joined text is identical', async () => {
    await expect(artifactDigest(makeItem('linkedin', 'linkedin_post', ['abcd'])))
      .resolves.toBe('sha256:9a600932185f55e44ea50e3e5c815e668c3f8279ad16b2c37b452725a25adc0e')
    await expect(artifactDigest(makeItem('linkedin', 'linkedin_post', ['ab', 'cd'])))
      .resolves.toBe('sha256:fa300f2bf2a81c832234fa1449e95786403b0a5e84f13f99000730317e143c9b')
  })

  it('covers only the contract fields', async () => {
    const segments = ['  exact text\n']
    const first = makeItem('linkedin', 'linkedin_post', segments)
    const second = makeItem('linkedin', 'linkedin_post', segments, {
      title: 'A different title',
      stage: 'export',
      working_revision: 9,
      context: { notes: 'different notes' },
      active_approval_id: 'approval-1',
    })
    await expect(artifactDigest(first)).resolves.toBe(await artifactDigest(second))
  })

  it('refuses to guess a digest without Web Crypto', async () => {
    vi.stubGlobal('crypto', undefined)
    await expect(artifactDigest(makeItem('linkedin', 'linkedin_post', ['text'])))
      .rejects.toThrow('This browser cannot calculate the approval digest.')
  })
})

describe('formatLabel', () => {
  it('uses the same labels as platform selection for every supported format', () => {
    for (const pair of FORMATS) expect(formatLabel(pair)).toBe(pair.label)
  })
  it('uses the retained label for a known format', () => {
    expect(formatLabel({ destination: 'linkedin', format: 'linkedin_post' })).toBe('LinkedIn post')
  })

  it('falls back to the pair for an unknown format', () => {
    expect(formatLabel({ destination: 'threads', format: 'threads_post' })).toBe('threads \u00b7 threads_post')
  })
})
