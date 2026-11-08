import React from 'react'
import { Brain, Cloud, Code, Layers, Shield, Tag, Users, Wrench } from 'lucide-react'
import { formatTopicLabel } from '../../lib/topics'

const topicIcons = [
  { matches: /systems|architecture/i, icon: Layers },
  { matches: /leadership/i, icon: Users },
  { matches: /\bai\b|machine learning/i, icon: Brain },
  { matches: /cloud|infrastructure/i, icon: Cloud },
  { matches: /security|reliability/i, icon: Shield },
  { matches: /productivity|tools/i, icon: Wrench },
  { matches: /engineering/i, icon: Code },
]

export default function TopicIcon({ topic }) {
  const label = formatTopicLabel(topic)
  const Icon = topicIcons.find(entry => entry.matches.test(label))?.icon || Tag
  return <Icon aria-hidden="true" className="w-3.5 h-3.5 shrink-0" />
}
