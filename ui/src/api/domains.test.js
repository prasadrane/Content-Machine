import { describe, it, expect, vi, afterEach } from 'vitest'
import { runCouncil, getCouncilHistory, getCouncilSpikes } from './council'
import { getLessons, addCustomLesson, diffLessons, approveLesson, rejectLesson } from './lessons'
import { runDistribute } from './distribute'
import { getBrief, synthesizeDraft, transcribeAudio } from './interview'
import { generateComments, getCommentsHistory } from './comments'
import { getProfile, saveProfile } from './profile'
import { runHumanize } from './humanize'

afterEach(() => vi.unstubAllGlobals())

function stub(okJson = {}) {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => okJson })))
}

describe('domain api modules hit exact endpoints', () => {
  it('council', async () => {
    stub()
    await runCouncil({ draft: 'x' }); expect(fetch.mock.calls[0][0]).toBe('/api/council/run')
    await getCouncilHistory('s1');      expect(fetch.mock.calls[1][0]).toBe('/api/council/history/s1')
    await getCouncilSpikes();          expect(fetch.mock.calls[2][0]).toBe('/api/council/spikes')
  })
  it('lessons', async () => {
    stub()
    await getLessons();          expect(fetch.mock.calls[0][0]).toBe('/api/lessons')
    await approveLesson('r-2');  expect(fetch.mock.calls[1][0]).toBe('/api/lessons/r-2/approve')
    expect(fetch.mock.calls[1][1].method).toBe('POST')
  })
  it('lessons custom/diff/reject', async () => {
    stub()
    await addCustomLesson({ rule_text: 'r' }); expect(fetch.mock.calls[0][0]).toBe('/api/lessons/custom')
    await diffLessons({ draft: 'd' });         expect(fetch.mock.calls[1][0]).toBe('/api/lessons/diff')
    await rejectLesson(7);                     expect(fetch.mock.calls[2][0]).toBe('/api/lessons/7/reject')
  })
  it('distribute + humanize', async () => {
    stub()
    await runDistribute({ text: 't' }); expect(fetch.mock.calls[0][0]).toBe('/api/distribute/run')
    await runHumanize({ text: 't' });   expect(fetch.mock.calls[1][0]).toBe('/api/humanize')
  })
  it('interview json endpoints', async () => {
    stub()
    await getBrief({ title: 't' });        expect(fetch.mock.calls[0][0]).toBe('/api/interview/brief')
    await synthesizeDraft({ responses: [] }); expect(fetch.mock.calls[1][0]).toBe('/api/interview/synthesize')
  })
  it('comments', async () => {
    stub()
    await generateComments({ post_content: 'p' }); expect(fetch.mock.calls[0][0]).toBe('/api/comments/generate')
    await getCommentsHistory(50)
    expect(fetch.mock.calls[1][0]).toBe('/api/comments/history?limit=50')
    await getCommentsHistory()
    expect(fetch.mock.calls[2][0]).toBe('/api/comments/history?limit=50')
  })
  it('profile get/save', async () => {
    stub()
    await getProfile();                 expect(fetch.mock.calls[0][0]).toBe('/api/profile')
    await saveProfile({ focus: 'x' });  expect(fetch.mock.calls[1][1].method).toBe('POST')
    expect(fetch.mock.calls[1][0]).toBe('/api/profile')
  })
  it('transcribeAudio sends FormData, no content-type header', async () => {
    stub({ text: 'hello' })
    const blob = new Blob(['a'])
    await transcribeAudio(blob, 'recording.webm')
    const [url, opts] = fetch.mock.calls[0]
    expect(url).toBe('/api/interview/transcribe')
    expect(opts.method).toBe('POST')
    expect(opts.body).toBeInstanceOf(FormData)
    expect(opts.headers).toBeUndefined()
    // source uses field name 'audio' (InterviewModal + CommentingTab)
    expect(opts.body.get('audio')).toBeInstanceOf(File)
    const file = opts.body.get('audio')
    expect(file.name).toBe('recording.webm')
  })
  it('transcribeAudio error string matches source', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 502, json: async () => ({}) })))
    await expect(transcribeAudio(new Blob(['a']), 'recording.webm'))
      .rejects.toThrow('Transcription failed (502)')
  })
})
