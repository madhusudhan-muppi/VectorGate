import { Thermometer, Waves, MapPinned, Clock3 } from 'lucide-react'
import type { Detection, MapNode } from '../types'
import { StatusPill } from './StatusPill'

type NodeDetailProps = { node: MapNode | null; detections: Detection[] }

export function NodeDetail({ node, detections }: NodeDetailProps) {
  if (!node) return <section className="panel detail-panel empty-detail"><div className="eyebrow"><MapPinned size={13} /> NODE DETAIL</div><strong>Select a mapped node</strong><span>Choose a marker to inspect current telemetry.</span></section>
  const latest = detections.find((detection) => detection.node_id === node.node_id)
  return <section className="panel detail-panel"><div className="panel-heading"><div><span className="eyebrow"><MapPinned size={13} /> NODE DETAIL</span><h2>{node.name}</h2></div><StatusPill active={node.active} /></div>
    <div className="node-id">{node.node_id}</div><p className="location-label">{node.location_label}</p>
    <div className="detail-grid"><div><span>RECENT EVENTS</span><strong>{node.recent_detection_count}</strong></div><div><span>LAST OBSERVED</span><strong>{node.latest_detection_at ? new Date(node.latest_detection_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</strong></div></div>
    <div className="environment-row"><div><Thermometer size={15} /><span>Temperature</span><strong>{latest?.temperature_c != null ? `${latest.temperature_c.toFixed(1)}°C` : 'Not reported'}</strong></div><div><Waves size={15} /><span>Humidity</span><strong>{latest?.humidity_percent != null ? `${latest.humidity_percent.toFixed(0)}%` : 'Not reported'}</strong></div></div>
    <div className="detail-foot"><Clock3 size={14} /> Times shown in your local timezone</div>
  </section>
}
