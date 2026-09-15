import { Activity, Radio, ScanLine, Tags } from 'lucide-react'
import type { Summary } from '../types'

type KpiStripProps = { summary: Summary | null }

export function KpiStrip({ summary }: KpiStripProps) {
  const cards = [
    { label: 'Active nodes', value: summary?.active_nodes ?? '--', note: summary ? `of ${summary.total_nodes} configured` : 'Awaiting telemetry', icon: Radio, tone: 'teal' },
    { label: 'Total detections', value: summary?.total_detections ?? '--', note: 'All recorded events', icon: Activity, tone: 'blue' },
    { label: 'Last 24 hours', value: summary?.detections_last_24h ?? '--', note: `${summary?.detections_last_hour ?? '--'} in the last hour`, icon: ScanLine, tone: 'amber' },
    { label: 'Unclassified', value: summary?.unknown_detections ?? '--', note: 'Classification pending', icon: Tags, tone: 'slate' },
  ]
  return <section className="kpi-strip" aria-label="Network key performance indicators">
    {cards.map(({ label, value, note, icon: Icon, tone }) => <article className="kpi" key={label}>
      <div className={`kpi-icon ${tone}`}><Icon size={18} /></div>
      <div className="kpi-copy"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>
    </article>)}
  </section>
}
