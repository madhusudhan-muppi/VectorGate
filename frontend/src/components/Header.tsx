import { Activity, CircleHelp, RefreshCw, Wifi, WifiOff } from 'lucide-react'

type HeaderProps = {
  online: boolean
  isDemoTelemetry: boolean
  lastRefresh: Date | null
  onRefresh: () => void
}

export function Header({ online, isDemoTelemetry, lastRefresh, onRefresh }: HeaderProps) {
  return (
    <header className="topbar">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true"><Activity size={20} strokeWidth={2.5} /></div>
        <div>
          <div className="brand-name">VECTORGATE</div>
          <div className="brand-subtitle">Optical Vector Surveillance Network</div>
        </div>
      </div>
      <div className="header-actions">
        <div className={`system-state ${online ? 'online' : 'offline'}`}>
          {online ? <Wifi size={15} /> : <WifiOff size={15} />}
          <span>{online ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}</span>
        </div>
        {isDemoTelemetry && <div className="demo-state"><span>DEMO TELEMETRY</span><strong>SYNTHETIC DATA</strong></div>}
        <div className="refresh-meta">
          <span>LAST SYNC</span>
          <strong>{lastRefresh ? lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'WAITING'}</strong>
        </div>
        <button className="icon-button" onClick={onRefresh} title="Refresh telemetry now" aria-label="Refresh telemetry now">
          <RefreshCw size={17} />
        </button>
        <button className="icon-button quiet" title="About VectorGate" aria-label="About VectorGate">
          <CircleHelp size={17} />
        </button>
      </div>
    </header>
  )
}
