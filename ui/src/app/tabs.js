import OracleTab from '../components/oracle/OracleTab'
import CouncilTab from '../components/council/CouncilTab'
import DistributeTab from '../components/distribute/DistributeTab'
import LessonsTab from '../components/lessons/LessonsTab'
import AudioTab from '../components/audio/AudioTab'
import CommentingTab from '../components/commenting/CommentingTab'
import ProfileTab from '../components/profile/ProfileTab'

export const TABS = [
  {
    id: 'oracle',
    label: 'Oracle',
    Component: OracleTab,
    getProps: (s) => ({
      onSendToCouncil: s.handleSendToCouncil,
      onSendToCouncilWithDraft: s.handleSendToCouncilWithDraft,
    }),
  },
  {
    id: 'council',
    label: 'Council',
    Component: CouncilTab,
    getProps: (s) => ({
      draft: s.councilDraft,
      setDraft: s.setCouncilDraft,
      spikeId: s.councilSpikeId,
      setSpikeId: s.setCouncilSpikeId,
      onSendToDistribute: s.handleSendToDistribute,
    }),
  },
  {
    id: 'distribute',
    label: 'Distribute',
    Component: DistributeTab,
    getProps: (s) => ({
      initialText: s.distributeText,
      initialSlug: s.distributeSlug,
    }),
  },
  { id: 'lessons', label: 'Lessons', Component: LessonsTab },
  { id: 'audio', label: 'Audio', Component: AudioTab },
  { id: 'commenting', label: 'Comments', Component: CommentingTab },
  { id: 'profile', label: 'Profile', Component: ProfileTab },
]
