import React, { useState } from 'react'

export default function AudioTab() {
  const [audioPath, setAudioPath] = useState('')
  const [model, setModel] = useState('small')

  return (
    <div className="cm-page animate-fadeIn">
      <div className="cm-page-header">
        <div>
          <h2 className="cm-page-title">Audio & Voice</h2>
          <p className="cm-page-description">
            Speech transcription and dictation monitor.
          </p>
        </div>
      </div>

      <div className="cm-panel space-y-6">
        <div className="space-y-4">
          <h3 className="cm-panel-title">Batch Transcription</h3>
          
          <div>
            <label htmlFor="audio-file-path" className="cm-label">Audio File Path</label>
            <input
              id="audio-file-path"
              type="text"
              value={audioPath}
              onChange={(e) => setAudioPath(e.target.value)}
              placeholder="C:/Users/.../recordings/interview.wav"
              className="cm-input font-mono"
            />
          </div>

          <div>
            <label htmlFor="audio-model-size" className="cm-label">Model Size (CPU int8)</label>
            <select
              id="audio-model-size"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="cm-select max-w-xs"
            >
              <option value="tiny">tiny (fastest)</option>
              <option value="base">base</option>
              <option value="small">small (recommended)</option>
              <option value="medium">medium</option>
              <option value="large-v3">large-v3 (highest accuracy)</option>
            </select>
          </div>

          <p className="cm-muted break-words">
            CLI quick-run: <code className="cm-subpanel block mt-2 font-mono text-base break-all">python -m content_machine transcribe &lt;path&gt; --model {model}</code>
          </p>
        </div>

        <div className="cm-divider pt-6 space-y-3">
          <h3 className="cm-panel-title">Live Streaming Monitor</h3>
          <div className="cm-subpanel space-y-3">
            <p className="cm-prose">
              Real-time whisper.cpp dictation monitoring streams directly to the terminal or browser WebSocket during the 09:00 Interview panel phase.
            </p>
            <p className="cm-muted">
              Hardware profile: i7-1255U CPU-only &bull; Target word count: 800-2,000 words before drafting gate opens.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
