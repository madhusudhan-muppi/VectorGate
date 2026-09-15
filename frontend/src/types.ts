export type Health = {
  status: string
  database: string
}

export type ClassifierStatus = {
  enabled: boolean
  loaded: boolean
  model_version: string | null
  model_type: string | null
  training_data_type: string | null
  unknown_threshold: number | null
  classes: string[]
  synthetic_validation_metrics?: { label: string; accuracy: number; macro_f1: number; rejected_as_unknown_at_threshold: number }
  load_error?: string | null
}

export type Summary = {
  total_nodes: number
  active_nodes: number
  total_detections: number
  detections_last_hour: number
  detections_last_24h: number
  unknown_detections: number
  latest_detection_at: string | null
}

export type MapNode = {
  node_id: string
  name: string
  latitude: number
  longitude: number
  location_label: string
  active: boolean
  recent_detection_count: number
  latest_detection_at: string | null
}

export type Detection = {
  id: number
  node_id: string
  recorded_at: string
  received_at: string
  dominant_frequency_hz: number
  event_duration_seconds: number
  dominant_magnitude: number
  second_harmonic_ratio: number
  third_harmonic_ratio: number
  rms: number
  peak_to_peak: number
  spectral_energy: number
  estimated_snr_db: number
  temperature_c: number | null
  humidity_percent: number | null
  predicted_class: string | null
  confidence: number | null
  model_version: string | null
}

export type ActivityBucket = {
  bucket_start: string
  count: number
}

export type ApiState = {
  health: Health | null
  classifier: ClassifierStatus | null
  summary: Summary | null
  nodes: MapNode[]
  detections: Detection[]
  activity: ActivityBucket[]
  loading: boolean
  error: string | null
  lastRefresh: Date | null
}
