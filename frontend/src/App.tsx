import { useState } from 'react'
import { ArrowUpRight, Database, GitBranch, ShieldCheck } from 'lucide-react'
import { Header } from './components/Header'
import { KpiStrip } from './components/KpiStrip'
import { MapPanel } from './components/MapPanel'
import { DetectionFeed } from './components/DetectionFeed'
import { ActivityChart } from './components/ActivityChart'
import { NodeDetail } from './components/NodeDetail'
import { SpeciesPanel } from './components/SpeciesPanel'
import { ClassifierStatus } from './components/ClassifierStatus'
import { useDashboardData } from './hooks/useDashboardData'

function relativeTime(iso: string | null) {
  if (!iso) return 'WAITING'
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return `${seconds} sec ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
  return `${Math.floor(seconds / 3600)} hr ago`
}

function App() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const dashboard = useDashboardData(selectedNodeId)
  const selectedNode = dashboard.nodes.find((node) => node.node_id === selectedNodeId) ?? null
  const online = dashboard.health?.status === 'ok' && !dashboard.error
  const isDemoTelemetry = dashboard.nodes.some((node) => node.node_id.startsWith('DEMO-')) || dashboard.detections.some((detection) => detection.node_id.startsWith('DEMO-'))
  const lastEvent = dashboard.detections[0]?.recorded_at ?? dashboard.summary?.latest_detection_at ?? null
  // The "no species inference" claim stops being true once a species model serves
  // the feed, so the banner has to follow what the backend is actually running.
  const speciesModelServing = dashboard.classifier?.enabled === true && dashboard.classifier?.loaded === true && dashboard.classifier?.training_data_type === 'wingbeats_optical'

  return <div className="app-shell"><Header online={online} isDemoTelemetry={isDemoTelemetry} lastRefresh={dashboard.lastRefresh} onRefresh={() => void dashboard.refresh()} />
    {dashboard.error && <div className="offline-banner"><ShieldCheck size={16} /><span>{dashboard.error}. The dashboard will retry automatically.</span></div>}
    <main className="dashboard"><section className="intro-row"><div><span className="eyebrow">MOSQUITO SURVEILLANCE / LIVE VIEW</span><h1>Which mosquitoes are flying, and where.</h1><p>Optical wingbeat sensing across the node network, with the disease each species is known to carry.</p></div><div className="intro-actions"><div className="last-event"><span>LAST DETECTION</span><strong className={dashboard.newDetectionIds.size > 0 ? 'pulse' : ''}>{relativeTime(lastEvent)}</strong></div><ClassifierStatus status={dashboard.classifier} /><div className="data-honesty"><Database size={15} /><span>{speciesModelServing ? <>Trained on public optical data<br /><b>Not validated on this hardware</b></> : <>Wingbeat activity only<br /><b>No species inference</b></>}</span><ArrowUpRight size={15} /></div></div></section>
      <section className="pipeline-strip" aria-label="VectorGate processing pipeline"><span className="pipeline-label"><GitBranch size={14} /> SIGNAL PATH</span>{['OPTICAL SENSOR', 'WINGBEAT DSP', 'FEATURE EXTRACTION', 'SPECIES MODEL', 'VECTOR PROFILE'].map((step, index) => <span className="pipeline-step" key={step}><b>{String(index + 1).padStart(2, '0')}</b>{step}{index < 4 && <i>→</i>}</span>)}</section>
      <KpiStrip summary={dashboard.summary} />
      <SpeciesPanel detections={dashboard.detections} nodes={dashboard.nodes} catalog={dashboard.speciesCatalog} selectedNodeId={selectedNodeId} onSelectNode={setSelectedNodeId} />
      <div className="primary-grid"><MapPanel nodes={dashboard.nodes} selectedNodeId={selectedNodeId} onSelectNode={setSelectedNodeId} /><aside className="side-stack"><NodeDetail node={selectedNode} detections={dashboard.detections} /><ActivityChart nodeId={selectedNodeId} activity={dashboard.activity} /></aside></div>
      <DetectionFeed detections={dashboard.detections} newDetectionIds={dashboard.newDetectionIds} />
    </main>
    <footer className="app-footer"><span>VECTORGATE PROTOTYPE · {speciesModelServing ? 'SPECIES MODEL TRAINED ON A PUBLIC OPTICAL WINGBEAT DATASET' : 'CLASSIFIER NOT ENABLED'}</span><span>NOT VALIDATED ON VECTORGATE HARDWARE · NOT A DIAGNOSTIC DEVICE</span></footer>
  </div>
}

export default App
