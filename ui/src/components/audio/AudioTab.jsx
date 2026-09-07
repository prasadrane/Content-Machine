import React, { useState } from 'react'

export default function AudioTab() {
  const [audioPath, setAudioPath] = useState('')
  const [model, setModel] = useState('small')

  return (
    <div className="space-y-8 animate-fadeIn max-w-2xl">
      <div className="border-b border-[#e3dacc] pb-5">
        <h2 className="font-serif text-2xl font-medium tracking-tight text-[#141413]">Audio & Voice</h2>
        <p className="text-sm text-[#87867f] mt-1 font-sans">
          Speech transcription and dictation monitor.
        </p>
      </div>

      <div className="bg-[#f0eee6]/60 p-6 rounded-2xl border border-[#e3dacc] space-y-6 shadow-anthropic">
        <div className="space-y-4">
          <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Batch Transcription</h3>
          
          <div>
            <label className="block text-xs font-medium text-[#141413] mb-1.5">Audio File Path</label>
            <input
              type="text"
              value={audioPath}
              onChange={(e) => setAudioPath(e.target.value)}
              placeholder="C:/Users/.../recordings/interview.wav"
              className="w-full text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2.5 text-[#141413] focus:outline-none focus:border-[#141413] placeholder-[#b0aea5]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#141413] mb-1.5">Model Size (CPU int8)</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="text-xs font-mono bg-[#faf9f5] border border-[#e3dacc] rounded-xl p-2.5 text-[#141413] focus:outline-none focus:border-[#141413] w-52"
            >
              <option value="tiny">tiny (fastest)</option>
              <option value="base">base</option>
              <option value="small">small (recommended)</option>
              <option value="medium">medium</option>
              <option value="large-v3">large-v3 (highest accuracy)</option>
            </select>
          </div>

          <p className="text-xs text-[#87867f] font-mono">
            CLI quick-run: <code className="text-[#141413] bg-[#e3dacc]/50 px-1.5 py-0.5 rounded">python -m content_machine transcribe &lt;path&gt; --model {model}</code>
          </p>
        </div>

        <div className="pt-6 border-t border-[#e3dacc] space-y-3">
          <h3 className="text-xs uppercase font-mono tracking-wider text-[#87867f]">Live Streaming Monitor</h3>
          <div className="bg-[#faf9f5] p-4 rounded-xl border border-[#e3dacc] space-y-2 text-xs text-[#87867f] shadow-anthropic">
            <p className="text-[#141413]">
              Real-time whisper.cpp dictation monitoring streams directly to the terminal or browser WebSocket during the 09:00 Interview panel phase.
            </p>
            <p className="text-[11px] font-mono text-[#87867f]">
              Hardware profile: i7-1255U CPU-only &bull; Target word count: 800-2,000 words before drafting gate opens.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
