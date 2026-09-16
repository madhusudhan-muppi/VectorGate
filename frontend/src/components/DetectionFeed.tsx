import { Activity, CircleDashed, Radio } from 'lucide-react'
import { useState } from 'react'
import type { Detection } from '../types'

type DetectionFeedProps = { detections: Detection[]; newDetectionIds: Set<number> }

function relativeTime(iso: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

function displayClass(label: string | null) {
  if (label === 'DEMO_CLASS_A') return 'Pattern A (Synthetic)'
  if (label === 'DEMO_CLASS_B') return 'Pattern B (Synthetic)'
  if (label === 'DEMO_CLASS_C') return 'Pattern C (Synthetic)'
  return label ?? 'UNCLASSIFIED'
}

export function DetectionFeed({ detections, newDetectionIds }: DetectionFeedProps) {
  const [filter, setFilter] = useState<'ALL' | 'CLASSIFIED' | 'UNKNOWN' | 'UNCLASSIFIED'>('ALL')
  const visible = detections.filter((detection) => filter === 'ALL' || filter === 'CLASSIFIED' && detection.predicted_class != null && detection.predicted_class !== 'UNKNOWN' || filter === 'UNKNOWN' && detection.predicted_class === 'UNKNOWN' || filter === 'UNCLASSIFIED' && detection.predicted_class == null)
  return <section className="panel feed-panel"><div className="panel-heading"><div><span className="eyebrow"><Radio size={13} /> LIVE DETECTIONS</span><h2>Recent wingbeat events</h2></div><div className="feed-tools"><div className="feed-filters">{(['ALL', 'CLASSIFIED', 'UNKNOWN', 'UNCLASSIFIED'] as const).map((item) => <button className={filter === item ? 'selected' : ''} onClick={() => setFilter(item)} key={item}>{item}</button>)}</div><span className="feed-count">{visible.length} visible</span></div></div>
    {visible.length === 0 ? <div className="feed-empty"><CircleDashed size={24} /><strong>No detections in this filter.</strong><span>Waiting for the next wingbeat event...</span></div> : <div className="feed-list">{visible.map((detection) => <article className={`feed-row ${newDetectionIds.has(detection.id) ? 'new' : ''}`} key={detection.id}><div className="feed-signal"><Activity size={15} /></div><div className="feed-main"><div><strong>{detection.node_id}</strong><span className="feed-time" title={new Date(detection.recorded_at).toLocaleString()}>{relativeTime(detection.recorded_at)}</span></div><div className="feed-measure"><span>{detection.dominant_frequency_hz.toFixed(1)} <small>Hz</small></span><span>{detection.event_duration_seconds.toFixed(2)} <small>sec</small></span></div></div><div className="classification"><span className={`classification-label ${detection.predicted_class === 'UNKNOWN' ? 'unknown' : detection.predicted_class ? 'demo-class' : 'unclassified'}`}>{displayClass(detection.predicted_class)}</span><small>{detection.predicted_class === 'UNKNOWN' ? detection.confidence == null ? 'Insufficient confidence' : `Best known-class probability ${(detection.confidence * 100).toFixed(0)}%` : detection.confidence == null ? detection.predicted_class == null ? 'Awaiting model' : 'Model output' : `${(detection.confidence * 100).toFixed(0)}% confidence`}</small></div></article>)}</div>}
  </section>
}
