import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Crosshair, MapPinOff } from 'lucide-react'
import type { MapNode } from '../types'

type MapPanelProps = { nodes: MapNode[]; selectedNodeId: string | null; onSelectNode: (nodeId: string) => void }

function activityLevel(count: number) {
  if (count >= 10) return 'high'
  if (count >= 5) return 'elevated'
  if (count > 0) return 'normal'
  return 'quiet'
}

function markerIcon(node: MapNode) {
  const level = activityLevel(node.recent_detection_count)
  return L.divIcon({ className: 'vg-marker-wrap', html: `<span class="vg-marker ${level} ${node.active ? '' : 'muted'}"><i></i></span>`, iconSize: [28, 28], iconAnchor: [14, 14] })
}

export function MapPanel({ nodes, selectedNodeId, onSelectNode }: MapPanelProps) {
  const mapElement = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerRef = useRef<L.LayerGroup | null>(null)
  const validNodes = nodes.filter((node) => Math.abs(node.latitude) > 0.001 || Math.abs(node.longitude) > 0.001)
  const syntheticNodes = nodes.length - validNodes.length

  useEffect(() => {
    if (!mapElement.current || mapRef.current) return
    const map = L.map(mapElement.current, { zoomControl: false, attributionControl: true, scrollWheelZoom: false }).setView([13.02, 80.23], 11)
    L.control.zoom({ position: 'bottomright' }).addTo(map)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 }).addTo(map)
    layerRef.current = L.layerGroup().addTo(map)
    mapRef.current = map
    window.setTimeout(() => map.invalidateSize(), 100)
    return () => { map.remove(); mapRef.current = null }
  }, [])

  useEffect(() => {
    if (!mapRef.current || !layerRef.current) return
    layerRef.current.clearLayers()
    validNodes.forEach((node) => {
      const marker = L.marker([node.latitude, node.longitude], { icon: markerIcon(node), title: node.name })
      marker.bindTooltip(`<strong>${node.name}</strong><br>${node.recent_detection_count} recent detections`, { direction: 'top', offset: [0, -10] })
      marker.on('click', () => onSelectNode(node.node_id))
      marker.addTo(layerRef.current!)
    })
    if (selectedNodeId) {
      const node = validNodes.find((item) => item.node_id === selectedNodeId)
      if (node) mapRef.current.flyTo([node.latitude, node.longitude], 13, { duration: 0.7 })
    }
  }, [nodes, selectedNodeId, onSelectNode, validNodes])

  return <section className="panel map-panel">
    <div className="panel-heading map-heading"><div><span className="eyebrow"><Crosshair size={13} /> GEOGRAPHIC VIEW</span><h2>Where the nodes are</h2></div><div className="map-legend"><span><i className="legend-dot quiet" />Quiet</span><span><i className="legend-dot elevated" />Elevated</span><span><i className="legend-dot high" />High</span></div></div>
    <div className="map-stage"><div className="leaflet-host" ref={mapElement} />
      {nodes.length === 0 && <div className="map-empty"><MapPinOff size={22} /><strong>No nodes configured</strong><span>Waiting for VectorGate telemetry...</span></div>}
      {syntheticNodes > 0 && <div className="map-note"><MapPinOff size={14} /> {syntheticNodes} synthetic coordinate{syntheticNodes > 1 ? 's' : ''} withheld from map</div>}
    </div>
    <div className="map-footer"><span><i className="live-dot" /> Activity window: last 24 hours</span><span>{validNodes.length} mapped / {nodes.length} nodes</span></div>
  </section>
}
