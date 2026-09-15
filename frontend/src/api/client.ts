import type { ActivityBucket, Detection, Health, MapNode, Summary } from '../types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new Error('Unable to reach the VectorGate backend')
  }

  if (!response.ok) {
    let detail = `Backend request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // Preserve the useful HTTP status when an error body is not JSON.
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  baseUrl: API_BASE_URL,
  health: (signal?: AbortSignal) => request<Health>('/api/v1/health', signal),
  summary: (signal?: AbortSignal) => request<Summary>('/api/v1/stats/summary', signal),
  nodes: (signal?: AbortSignal) => request<MapNode[]>('/api/v1/map/nodes', signal),
  detections: (signal?: AbortSignal) => request<Detection[]>('/api/v1/detections?limit=50', signal),
  activity: (nodeId: string, signal?: AbortSignal) => request<ActivityBucket[]>(
    `/api/v1/nodes/${encodeURIComponent(nodeId)}/activity?bucket_seconds=3600`,
    signal,
  ),
}
