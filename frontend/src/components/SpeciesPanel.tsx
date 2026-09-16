import { useMemo, useState } from 'react'
import { AlertTriangle, BookOpen, Bug, CircleHelp, MapPin, ShieldQuestion } from 'lucide-react'
import type { Detection, MapNode, SpeciesCatalog, SpeciesReference } from '../types'

type SpeciesPanelProps = {
  detections: Detection[]
  nodes: MapNode[]
  catalog: SpeciesCatalog | null
  selectedNodeId: string | null
  onSelectNode: (nodeId: string | null) => void
}

type Tally = {
  key: string
  label: string
  count: number
  share: number
  meanConfidence: number | null
  reference: SpeciesReference | null
}

const UNCLASSIFIED = '__unclassified__'

/** Strip the demo prefix so place names read naturally in headings and chips. */
function placeName(node: MapNode) {
  return node.name.replace(/^DEMO \/ /, '')
}

/** Identified species first, then Unknown, then rows the model never labelled. */
function rank(item: Tally) {
  if (item.reference && !item.reference.is_unknown) return 0
  return item.reference ? 1 : 2
}

/** Group detections by the class the model reported. */
function tally(detections: Detection[], catalog: SpeciesCatalog | null): Tally[] {
  const buckets = new Map<string, { count: number; confidence: number[] }>()
  for (const detection of detections) {
    const key = detection.predicted_class ?? UNCLASSIFIED
    const bucket = buckets.get(key) ?? { count: 0, confidence: [] }
    bucket.count += 1
    if (detection.confidence != null) bucket.confidence.push(detection.confidence)
    buckets.set(key, bucket)
  }
  const total = detections.length || 1
  return [...buckets.entries()]
    .map(([key, bucket]) => ({
      key,
      label: key === UNCLASSIFIED ? 'Not classified' : key,
      count: bucket.count,
      share: bucket.count / total,
      meanConfidence: bucket.confidence.length
        ? bucket.confidence.reduce((sum, value) => sum + value, 0) / bucket.confidence.length
        : null,
      reference: catalog?.species.find((record) => record.key === key) ?? null,
    }))
    .sort((a, b) => rank(a) - rank(b) || b.count - a.count)
}

function DiseaseDetail({ reference, disclaimer }: { reference: SpeciesReference; disclaimer: string }) {
  if (reference.is_unknown || reference.diseases.length === 0) {
    return <div className="species-detail">
      <div className="species-detail-head">
        <div>
          <span className="eyebrow"><ShieldQuestion size={13} /> UNRESOLVED SIGNATURE</span>
          <h3>{reference.scientific_name}</h3>
          <p className="species-common">{reference.common_name}</p>
        </div>
      </div>
      <p className="species-unknown-note">{reference.notes}</p>
    </div>
  }

  return <div className="species-detail">
    {reference.image && <figure className="species-photo">
      <img src={reference.image} alt={`${reference.scientific_name} mosquito`} />
      <figcaption><i>{reference.scientific_name}</i></figcaption>
    </figure>}
    <div className="species-detail-head">
      <div>
        <span className="eyebrow"><Bug size={13} /> SPECIES PROFILE</span>
        <h3><i>{reference.scientific_name}</i></h3>
        <p className="species-common">{reference.common_name}</p>
      </div>
      <span className={`vector-badge ${reference.genus.toLowerCase()}`}>{reference.vector_status}</span>
    </div>

    <div className="disease-headline">
      <span>PRIMARY DISEASE ASSOCIATION</span>
      <strong>{reference.headline_disease}</strong>
    </div>

    <div className="disease-grid">
      {reference.diseases.map((disease) => <article className={`disease-chip ${disease.group}`} key={disease.name}>
        <strong>{disease.name}</strong>
        <small>{disease.note || disease.group.replace(/^\w/, (c) => c.toUpperCase())}</small>
      </article>)}
    </div>

    <dl className="species-facts">
      {reference.india_relevance && <div><dt><MapPin size={12} /> India relevance</dt><dd>{reference.india_relevance}</dd></div>}
      {reference.notes && <div><dt><CircleHelp size={12} /> Field notes</dt><dd>{reference.notes}</dd></div>}
      {reference.sources.length > 0 && <div>
        <dt><BookOpen size={12} /> Evidence{reference.evidence_level && ` · ${reference.evidence_level}`}</dt>
        <dd>{reference.sources.join(' · ')}</dd>
      </div>}
    </dl>

    <p className="disease-disclaimer"><AlertTriangle size={14} /><span>{disclaimer}</span></p>
  </div>
}

export function SpeciesPanel({ detections, nodes, catalog, selectedNodeId, onSelectNode }: SpeciesPanelProps) {
  const [focusKey, setFocusKey] = useState<string | null>(null)

  const scoped = useMemo(
    () => (selectedNodeId ? detections.filter((detection) => detection.node_id === selectedNodeId) : detections),
    [detections, selectedNodeId],
  )
  const tallies = useMemo(() => tally(scoped, catalog), [scoped, catalog])
  const selectedNode = nodes.find((node) => node.node_id === selectedNodeId) ?? null

  // Focus follows the most-detected identified species unless the user picks
  // another. Unknown and unclassified rows are far more numerous in a seeded
  // database, and leading with them buries the thing the panel exists to show.
  const focused =
    tallies.find((item) => item.key === focusKey)
    ?? tallies.find((item) => item.reference && !item.reference.is_unknown)
    ?? tallies.find((item) => item.reference)
    ?? null
  const heading = selectedNode
    ? `Which mosquitoes are flying at ${placeName(selectedNode)}`
    : 'Which mosquitoes are flying across the network'

  return <section className="panel species-panel">
    <div className="panel-heading">
      <div>
        <span className="eyebrow"><Bug size={13} /> VECTOR IDENTIFICATION</span>
        <h2>{heading}</h2>
      </div>
      <span className="feed-count">{scoped.length} detections analysed</span>
    </div>

    <div className="place-picker" role="group" aria-label="Choose a location">
      <button className={selectedNodeId === null ? 'selected' : ''} onClick={() => onSelectNode(null)}>All locations</button>
      {nodes.map((node) => <button
        key={node.node_id}
        className={selectedNodeId === node.node_id ? 'selected' : ''}
        onClick={() => onSelectNode(node.node_id)}
      >{placeName(node)}</button>)}
    </div>

    {scoped.length === 0
      ? <div className="feed-empty"><Bug size={24} /><strong>No detections here yet.</strong><span>Choose another location, or publish telemetry to this node.</span></div>
      : <div className="species-layout">
        <div className="species-ranking">
          {tallies.map((item) => <button
            key={item.key}
            className={`species-row ${focused?.key === item.key ? 'selected' : ''} ${item.reference?.is_unknown || !item.reference ? 'muted' : ''}`}
            onClick={() => setFocusKey(item.key)}
            disabled={!item.reference}
          >
            <div className="species-row-head">
              {item.reference?.image
                ? <img className="species-thumb" src={item.reference.image} alt="" />
                : <span className="species-thumb placeholder" aria-hidden="true" />}
              <strong>{item.reference && !item.reference.is_unknown ? <i>{item.reference.scientific_name}</i> : item.label}</strong>
              <span>{item.count}</span>
            </div>
            <div className="species-bar"><span style={{ width: `${Math.max(3, item.share * 100)}%` }} className={item.reference?.genus.toLowerCase() ?? 'none'} /></div>
            <div className="species-row-foot">
              <span>{item.reference && !item.reference.is_unknown ? item.reference.headline_disease : 'No species assigned'}</span>
              <span>{item.meanConfidence != null ? `${(item.meanConfidence * 100).toFixed(0)}% mean confidence` : '—'}</span>
            </div>
          </button>)}
        </div>

        {focused?.reference
          ? <DiseaseDetail reference={focused.reference} disclaimer={catalog?.disclaimer ?? ''} />
          : <div className="species-detail empty"><ShieldQuestion size={22} /><strong>No species profile to show.</strong><span>These detections were not assigned a species by the classifier.</span></div>}
      </div>}
  </section>
}
