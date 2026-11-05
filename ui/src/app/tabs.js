import OracleTab from '../components/oracle/OracleTab'
import CouncilTab from '../components/council/CouncilTab'
import DistributeTab from '../components/distribute/DistributeTab'
import LessonsTab from '../components/lessons/LessonsTab'
import AudioTab from '../components/audio/AudioTab'
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
      councilIdentity: s.councilIdentity,
      setDraft: s.setCouncilDraft,
      spikeId: s.councilSpikeId,
      setSpikeId: s.setCouncilSpikeId,
      onApprove: s.handleApprove,
    }),
  },
  {
    id: 'distribute',
    label: 'Distribute',
    Component: DistributeTab,
    getProps: (s) => ({
      initialText: s.distributeText,
      initialSlug: s.distributeSlug,
      approvedText: s.approvedText,
      approval: s.approval,
      anchorIdentity: s.distributeAnchor,
      onApprove: s.approveAnchor,
      onInvalidateApproval: s.invalidateApproval,
    }),
  },
  { id: 'lessons', label: 'Lessons', Component: LessonsTab },
  { id: 'audio', label: 'Audio', Component: AudioTab },
  { id: 'profile', label: 'Profile', Component: ProfileTab },
]
