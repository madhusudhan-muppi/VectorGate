import { useState } from 'react'
import { ArrowUpRight, Database, ShieldCheck } from 'lucide-react'
import { Header } from './components/Header'
import { KpiStrip } from './components/KpiStrip'
import { MapPanel } from './components/MapPanel'
import { DetectionFeed } from './components/DetectionFeed'
import { ActivityChart } from './components/ActivityChart'
import { NodeDetail } from './components/NodeDetail'
import { ClassifierStatus } from './components/ClassifierStatus'
import { useDashboardData } from './hooks/useDashboardData'

function App() {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const dashboard = useDashboardData(selectedNodeId)
  const selectedNode = dashboard.nodes.find((node) => node.node_id === selectedNodeId) ?? null
  const online = dashboard.health?.status === 'ok' && !dashboard.error

  return <div className="app-shell"><Header online={online} lastRefresh={dashboard.lastRefresh} onRefresh={() => void dashboard.refresh()} />
    {dashboard.error && <div className="offline-banner"><ShieldCheck size={16} /><span>{dashboard.error}. The dashboard will retry automatically.</span></div>}
    <main className="dashboard"><section className="intro-row"><div><span className="eyebrow">NETWORK OPERATIONS / LIVE VIEW</span><h1>Flight activity across the network.</h1><p>Optical gate telemetry, event timing, and node health in one operational view.</p></div><div className="intro-actions"><ClassifierStatus status={dashboard.classifier} /><div className="data-honesty"><Database size={15} /><span>Observed activity only<br /><b>No species inference</b></span><ArrowUpRight size={15} /></div></div></section>
      <KpiStrip summary={dashboard.summary} />
      <div className="primary-grid"><MapPanel nodes={dashboard.nodes} selectedNodeId={selectedNodeId} onSelectNode={setSelectedNodeId} /><aside className="side-stack"><NodeDetail node={selectedNode} detections={dashboard.detections} /><ActivityChart nodeId={selectedNodeId} activity={dashboard.activity} /></aside></div>
      <DetectionFeed detections={dashboard.detections} newDetectionIds={dashboard.newDetectionIds} />
    </main>
    <footer className="app-footer"><span>VECTORGATE / STAGE 4 COMMAND VIEW</span><span>Source: live Stage 3 API · UTC stored, local display</span></footer>
  </div>
}

export default App
