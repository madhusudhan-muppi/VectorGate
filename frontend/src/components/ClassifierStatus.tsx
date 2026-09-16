import { BrainCircuit, ShieldAlert } from 'lucide-react'
import type { ClassifierStatus as ClassifierStatusType } from '../types'

type Props = { status: ClassifierStatusType | null }

export function ClassifierStatus({ status }: Props) {
  if (!status || !status.enabled || !status.loaded) return <div className="classifier-card muted"><ShieldAlert size={17} /><div><span>CLASSIFIER</span><strong>{status?.enabled ? 'Unavailable' : 'Not enabled'}</strong></div><small>Detections remain unclassified</small></div>
  if (status.training_data_type === 'wingbeats_optical') {
    const accuracy = status.session_grouped_accuracy == null ? null : `${(status.session_grouped_accuracy * 100).toFixed(0)}%`
    return <div className="classifier-card"><BrainCircuit size={17} /><div><span>SPECIES CLASSIFIER</span><strong>{status.model_version}</strong></div><small>PUBLIC OPTICAL DATASET{accuracy && ` · ${accuracy} session-grouped`} · threshold {status.unknown_threshold?.toFixed(2)}</small></div>
  }
  return <div className="classifier-card"><BrainCircuit size={17} /><div><span>DEMO CLASSIFIER</span><strong>{status.model_version}</strong></div><small>SYNTHETIC MODEL · threshold {status.unknown_threshold?.toFixed(2)}</small></div>
}
