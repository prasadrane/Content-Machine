# Hosted legacy API boundary

`LegacyBoundaryMiddleware` rejects legacy `/api` routes with HTTP 410 when `VERCEL` is present or `CONTENT_MACHINE_DEPLOYMENT_MODE=hosted`. It permits the authenticated `/api/workflow` namespace and GET or HEAD for `/api/health` and `/api/meta`. Local endpoints retain their existing behavior.

Legacy Oracle, Council, distribution, lessons, profile, LinkedIn, interview, transcription and humanization endpoints use shared local state or connector behavior. The hosted boundary stops those handlers before their dependencies run. Creator data remains in the new owner-scoped workflow routes. Before exposing a legacy capability in hosted mode, it needs an owner-scoped design and independent security verification.

The legacy Vercel entry currently seeds public demo records and enables replay fallbacks automatically. Those fallbacks can return a prior Council result or distribution bundle after a model failure. Interview briefing also constructs a generic summary after failure, synthesis falls back to a template, and humanization can return sanitized original text after a model error. The hosted API boundary blocks these endpoints. Separate changes are needed before those legacy endpoints can report provider failures and outcomes accurately in any deployment mode.

Interview synthesis validates its project identifier through `project_dir` and checks the resolved directory remains inside the projects tree before model execution or transcript writes. This does not turn the legacy interview API into a hosted, owner-scoped capability.
