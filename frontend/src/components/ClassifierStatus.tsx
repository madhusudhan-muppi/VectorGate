import { BrainCircuit, ShieldAlert } from 'lucide-react'
import type { ClassifierStatus as ClassifierStatusType } from '../types'

type Props = { status: ClassifierStatusType | null }

export function ClassifierStatus({ status }: Props) {
  if (!status || !status.enabled || !status.loaded) return <div className="classifier-card muted"><ShieldAlert size={17} /><div><span>CLASSIFIER</span><strong>{status?.enabled ? 'Unavailable' : 'Not enabled'}</strong></div><small>Detections remain unclassified</small></div>
  return <div className="classifier-card"><BrainCircuit size={17} /><div><span>DEMO CLASSIFIER</span><strong>{status.model_version}</strong></div><small>SYNTHETIC MODEL · threshold {status.unknown_threshold?.toFixed(2)}</small></div>
}
