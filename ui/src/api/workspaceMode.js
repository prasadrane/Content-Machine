const warnedModes = new Set()

export function resolveWorkspaceMode(env = import.meta.env) {
  const raw = env.VITE_WORKSPACE_MODE
  const value = typeof raw === 'string' ? raw.trim().toLowerCase() : ''
  if (value === 'local') return 'local'
  if (value && value !== 'hosted' && !warnedModes.has(value)) {
    warnedModes.add(value)
    console.error(`Unrecognized VITE_WORKSPACE_MODE "${raw}"; treating as hosted (sign-in required).`)
  }
  return value ? 'hosted' : 'local'
}

export const isHostedWorkspace = (env = import.meta.env) => resolveWorkspaceMode(env) === 'hosted'
