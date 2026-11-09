import FlowStrip from '../workflow/FlowStrip'

/** Signed-out welcome screen. Handlers and pending/error state come from AuthGate. */
export default function WelcomeLanding({ error, pending, onGoogle, onGuest }) {
  return <main className="cm-page cm-welcome">
    <section className="cm-welcome-hero" aria-labelledby="welcome-title">
      <p className="cm-welcome-kicker">For engineers who write</p>
      <h1 id="welcome-title" className="cm-page-title cm-welcome-title">Welcome to Content Machine</h1>
      <p className="cm-page-description cm-welcome-lead">
        Turn an engineering idea into a reviewed, approved draft for LinkedIn, X, YouTube, Instagram,
        a newsletter or a video, in four steps.
      </p>
      {error && <p role="alert" className="cm-status cm-status-error">{error}</p>}
      <div className="cm-welcome-actions">
        <button type="button" className="cm-button cm-button-primary cm-welcome-primary" disabled={pending}
          onClick={onGuest}>Continue as guest</button>
        <button type="button" className="cm-button cm-button-secondary" disabled={pending}
          onClick={onGoogle}>Continue with Google</button>
      </div>
      <p className="cm-muted">
        Guest is the quickest way to start, with no sign-in. Sign in with Google to keep your work
        in a private workspace; you can later copy guest work into it as new drafts that still need approval.
      </p>
    </section>
    <section className="cm-welcome-flow" aria-labelledby="welcome-flow-title">
      <h2 id="welcome-flow-title" className="cm-panel-title">How it works</h2>
      <FlowStrip />
      <p className="cm-muted">AI assistance is optional. If it is unavailable, your drafts are still kept.</p>
    </section>
  </main>
}
