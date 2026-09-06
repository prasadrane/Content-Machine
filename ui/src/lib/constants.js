export const DIMENSION_LABELS = {
  lived_experience: 'Experience',
  novelty: 'Novelty',
  counter_intuitive: 'Novelty',
  specificity: 'Specificity',
  pov: 'POV',
  relevance: 'Relevance',
  rigor: 'Rigor',
}

export const HUMANIZE_TONES = [
  { id: 'punchy_direct', label: '⚡ Punchy & Direct', desc: 'Short sentences, raw cadence, aggressive brevity' },
  { id: 'pragmatic_architect', label: '🏛️ Pragmatic Architect', desc: 'Senior eng rigor, operational trade-offs, zero fluff' },
  { id: 'conversational_peer', label: '☕ Conversational Peer', desc: 'Natural peer dialogue, warm clarity, lived experience' },
]

export const DISTRIBUTION_FORMATS = [
  {
    id: 'linkedin',
    label: 'LinkedIn Post',
    shortLabel: 'LinkedIn',
    tag: 'Primary Platform',
    desc: 'High-performing, whitespace-optimized narrative with punchy hook, key operational lessons & relevant hashtags.',
    defaultOn: true,
    tagColor: 'text-[#141413] bg-[#e3dacc]/60 border-[#b0aea5]',
  },
  {
    id: 'x_thread',
    label: 'X (Twitter) Thread',
    shortLabel: 'X Thread',
    tag: '6-8 Cards',
    desc: 'Numbered insight cards (1/, 2/) with viral single-line hook and closing operational takeaway.',
    defaultOn: true,
    tagColor: 'text-[#141413] bg-[#e3dacc]/60 border-[#b0aea5]',
  },
  {
    id: 'video_script_short',
    label: 'Video Script - Short Form',
    shortLabel: 'Short Video',
    tag: 'Reels / Shorts (60-90s)',
    desc: 'Rapid-fire spoken script with [Visual Cue], [Camera Zoom], and pattern interrupts.',
    defaultOn: true,
    tagColor: 'text-[#c6613f] bg-[#c6613f]/10 border-[#c6613f]/30',
  },
  {
    id: 'video_script_long',
    label: 'Video Script - Long Form',
    shortLabel: 'YouTube Deep Dive',
    tag: 'YouTube (5-10 min)',
    desc: 'Comprehensive technical breakdown script with chapters, B-roll, and code overlays.',
    defaultOn: false,
    tagColor: 'text-[#d97757] bg-[#d97757]/10 border-[#d97757]/30',
  },
  {
    id: 'newsletter',
    label: 'Newsletter Briefing',
    shortLabel: 'Newsletter',
    tag: 'Executive Digest',
    desc: '300-400 word executive briefing with markdown headers and core strategic takeaways.',
    defaultOn: true,
    tagColor: 'text-emerald-800 bg-emerald-50 border-emerald-200',
  },
]

export const CORE_VOICE_INVARIANTS = [
  {
    title: 'Zero Company Attribution',
    summary: 'No previous company names',
    description: 'NEVER cite previous employers (e.g., Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech). Frame all insights as pure architectural observations and personal experience.',
  },
  {
    title: 'No False Corporate Employment',
    summary: 'Never claim current corporate employment',
    description: 'NEVER generate statements implying current employment at an organization (NEVER write "My company today...", "My team at work...", "At my current job...").',
  },
  {
    title: 'Job-Status Agnostic Senior Tone',
    summary: 'Focus on engineering architecture and trade-offs',
    description: 'Do not bring up layoffs or job searches in technical posts or comments unless explicitly prompted. Speak with senior authority, craftsmanship, and pragmatic conviction.',
  },
  {
    title: 'Zero Generic Praise',
    summary: 'Banned corporate clichés and empty praise',
    description: 'Banned phrases: "Spot on!", "Thanks for sharing", "Great post!", "In today\'s fast-paced world", "Crucial to remember". Jump straight into the technical crux.',
  },
  {
    title: 'No Emoji Overload',
    summary: '0-1 functional emoji max',
    description: 'Maximum 0-1 functional emoji per piece; zero bullet-point emoji spam or decoration.',
  },
]
