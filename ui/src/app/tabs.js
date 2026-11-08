import WorkflowTab from '../components/workflow/WorkflowTab'
import PreferencesPage from '../components/lessons/PreferencesPage'
import SettingsPage from '../components/profile/SettingsPage'

export const TABS = [
  { id: 'workflow', label: 'Workflow', Component: WorkflowTab },
  { id: 'lessons', label: 'Lessons', Component: PreferencesPage },
  { id: 'settings', label: 'Settings', Component: SettingsPage },
]
