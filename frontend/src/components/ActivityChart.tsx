import { BarChart3, ChartNoAxesColumn } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ActivityBucket } from '../types'

type ActivityChartProps = { nodeId: string | null; activity: ActivityBucket[] }

export function ActivityChart({ nodeId, activity }: ActivityChartProps) {
  const data = activity.map((bucket) => ({ ...bucket, label: new Date(bucket.bucket_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }))
  return <section className="panel chart-panel"><div className="panel-heading"><div><span className="eyebrow"><BarChart3 size={13} /> TIME SERIES</span><h2>{nodeId ? `Observed activity — ${nodeId}` : 'Observed activity'}</h2></div><span className="chart-range">24H / HOURLY</span></div>
    {!nodeId ? <div className="chart-empty"><ChartNoAxesColumn size={24} /><strong>Select a node to view activity</strong><span>Hourly event counts will appear here.</span></div> : data.length === 0 ? <div className="chart-empty"><ChartNoAxesColumn size={24} /><strong>No activity in this window</strong><span>This node has not reported detections recently.</span></div> : <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}><CartesianGrid vertical={false} stroke="rgba(167, 189, 194, 0.12)" /><XAxis dataKey="label" tick={{ fill: '#8fa4a8', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fill: '#8fa4a8', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip cursor={{ fill: 'rgba(39, 202, 182, 0.08)' }} contentStyle={{ background: '#121d22', border: '1px solid #2d4349', borderRadius: 3, color: '#eef6f4' }} formatter={(value) => [value, 'detections']} /><Bar dataKey="count" fill="#32b8a5" radius={[2, 2, 0, 0]} /></BarChart></ResponsiveContainer></div>}
  </section>
}
