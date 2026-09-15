import { Activity, CircleDashed, Radio } from 'lucide-react'
import type { Detection } from '../types'

type DetectionFeedProps = { detections: Detection[]; newDetectionIds: Set<number> }

function relativeTime(iso: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

export function DetectionFeed({ detections, newDetectionIds }: DetectionFeedProps) {
  return <section className="panel feed-panel"><div className="panel-heading"><div><span className="eyebrow"><Radio size={13} /> LIVE TELEMETRY</span><h2>Recent flight detections</h2></div><span className="feed-count">{detections.length} visible</span></div>
    {detections.length === 0 ? <div className="feed-empty"><CircleDashed size={24} /><strong>No detections recorded yet.</strong><span>Waiting for optical telemetry...</span></div> : <div className="feed-list">{detections.map((detection) => <article className={`feed-row ${newDetectionIds.has(detection.id) ? 'new' : ''}`} key={detection.id}><div className="feed-signal"><Activity size={15} /></div><div className="feed-main"><div><strong>{detection.node_id}</strong><span className="feed-time" title={new Date(detection.recorded_at).toLocaleString()}>{relativeTime(detection.recorded_at)}</span></div><div className="feed-measure"><span>{detection.dominant_frequency_hz.toFixed(1)} <small>Hz</small></span><span>{detection.event_duration_seconds.toFixed(2)} <small>sec</small></span></div></div><div className="classification"><span className="unclassified">UNCLASSIFIED</span><small>{detection.confidence == null ? 'Awaiting labelled model' : `${(detection.confidence * 100).toFixed(0)}% confidence`}</small></div></article>)}</div>}
  </section>
}
